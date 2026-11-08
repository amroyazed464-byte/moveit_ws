#!/usr/bin/env python3
"""Opt-in real simulator checks after run_full_tour.py has returned home."""
import json
import math
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request


URL = 'http://127.0.0.1:8765'
REPORT = Path('/tmp/heritage-safety-scenarios.json')


def state():
    return json.load(urllib.request.urlopen(URL + '/api/state', timeout=5))


def post(event, accepted=True):
    request = urllib.request.Request(URL + '/api/command', json.dumps(event).encode(),
                                     {'Content-Type': 'application/json'})
    try:
        result = json.load(urllib.request.urlopen(request, timeout=5))
    except urllib.error.HTTPError as exc:
        result = json.load(exc)
    assert result['ok'] is accepted, (event, result)
    return result


def wait(predicate, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = state()
        if predicate(current):
            return current
        time.sleep(.25)
    raise AssertionError(('Timed out', current['state'], current.get('fault')))


def stopped():
    time.sleep(.5)
    first = state()['world_pose']
    time.sleep(2)
    current = state()
    drift = math.hypot(current['world_pose']['x'] - first['x'], current['world_pose']['y'] - first['y'])
    assert abs(current['safety']['speed']) < .001 and drift < .08, (current, drift)
    return drift


def restore():
    post({'type': 'scenario', 'name': 'clear'})
    wait(lambda d: d['ready'])
    post({'type': 'recover'})
    assert state()['state'] == 'PAUSED'
    post({'type': 'resume'})


def main():
    results = {}
    try:
        assert state()['state'] == 'COMPLETE', 'Run the full tour first'
        post({'type': 'scenario', 'name': 'battery_low'})
        wait(lambda d: d['state'] == 'FAULT')
        post({'type': 'start'}, accepted=False)
        results['low_battery_blocks_restart'] = {'drift': stopped()}
        restore()
        wait(lambda d: d['state'] == 'COMPLETE')
        post({'type': 'visitors', 'count': 3})
        wait(lambda d: not d['pending_visitors'] and d['visitor_count'] == 3)
        post({'type': 'start', 'mode': 'child', 'language': 'en', 'auto_advance': False})
        moving = wait(lambda d: d['safety']['speed'] > .03)
        assert moving['safety']['speed'] <= .18001
        results['group_speed'] = moving['safety']['speed']
        post({'type': 'pause'})
        wait(lambda d: d['state'] == 'PAUSED')
        results['pause_stop_drift'] = stopped()
        post({'type': 'resume'})
        wait(lambda d: d['safety']['speed'] > .03)
        for name, seconds in [('crossing', 17), ('static_obstacle', 16)]:
            origin = state()['world_pose']
            post({'type': 'scenario', 'name': name})
            samples = []
            minimum_clearance = float('inf')
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                current = state()
                if name == 'static_obstacle':
                    obstacle_x = origin['x'] + 1.7 * math.cos(origin['yaw'])
                    obstacle_y = origin['y'] + 1.7 * math.sin(origin['yaw'])
                    dx = max(0, abs(current['world_pose']['x'] - obstacle_x) - .35)
                    dy = max(0, abs(current['world_pose']['y'] - obstacle_y) - .35)
                    minimum_clearance = min(minimum_clearance, math.hypot(dx, dy))
                    assert minimum_clearance >= .30, minimum_clearance
                samples.append({key: current['safety'][key] for key in ('front_distance', 'speed', 'reason')})
                front, speed = samples[-1]['front_distance'], samples[-1]['speed']
                assert speed <= .18001
                if front is not None and front < .62:
                    assert speed <= .001
                elif front is not None and front < 1.0:
                    assert speed <= .12001
                time.sleep(.25)
            results[name] = {'origin': origin, 'samples': samples}
            if name == 'static_obstacle':
                results[name]['minimum_robot_center_to_box'] = minimum_clearance
            post({'type': 'scenario', 'name': 'clear'})
            if state()['state'] == 'FAULT':
                restore()
        for name in ('visitor_lost', 'localization_lost', 'unclear'):
            post({'type': 'scenario', 'name': name})
            wait(lambda d: d['state'] == 'FAULT')
            post({'type': 'resume'}, accepted=False)
            results[name] = {'drift': stopped(), 'fault': state()['fault']}
            restore()
        current = wait(lambda d: d['state'] == 'PRESENTING')
        speech_id = current['speech']['id']
        post({'type': 'speech_started', 'speech_id': speech_id})
        wait(lambda d: d['media']['client_active'])
        wait(lambda d: d['state'] == 'PAUSED', timeout=12)
        results['lost_narration_client_pauses'] = True
        post({'type': 'resume'})
        current = wait(lambda d: d['state'] == 'PRESENTING')
        question = current['route'][0]['qa'][0]['question']
        post({'type': 'question', 'text': question})
        current = wait(lambda d: (d.get('qa') or {}).get('answered') is True)
        assert current['qa']['source_ids']
        results['bounded_qa_sources'] = current['qa']['source_ids']
        post({'type': 'question', 'text': '请给这件藏品估价一百万元是否合适'})
        current = wait(lambda d: (d.get('qa') or {}).get('answered') is False)
        assert current['human_help'] == 'unknown_question'
        results['unknown_question_handoff'] = True
        post({'type': 'repeat'})
        current = wait(lambda d: d['state'] == 'PRESENTING' and d['speech']['kind'] == 'narration')
        post({'type': 'speech_done', 'speech_id': current['speech']['id']})
        current = wait(lambda d: d['state'] == 'QUIZ')
        post({'type': 'quiz_answer', 'answer': current['quiz']['answer']})
        post({'type': 'repeat'})
        current = wait(lambda d: d['state'] == 'PRESENTING')
        post({'type': 'speech_done', 'speech_id': current['speech']['id']})
        wait(lambda d: d['state'] == 'READY_NEXT')
        results['repeat_after_quiz_recovers'] = True
        post({'type': 'next'})
        wait(lambda d: d['state'] == 'NAVIGATING')
        post({'type': 'skip'})
        wait(lambda d: d['zone_id'] == 'masterpieces')
        post({'type': 'manual'})
        wait(lambda d: d['state'] == 'MANUAL')
        results['manual_stop_drift'] = stopped()
        post({'type': 'recover'})
        post({'type': 'end'})
        wait(lambda d: d['state'] == 'COMPLETE', timeout=180)
        # Wall-clock safety/HTTP processing must continue while simulation time is paused.
        def pause_sim(paused):
            subprocess.run(['gz', 'service', '-s', '/world/heritage_hall/control', '--reqtype',
                            'gz.msgs.WorldControl', '--reptype', 'gz.msgs.Boolean', '--timeout',
                            '1500', '--req', 'pause: ' + str(paused).lower()], check=True, capture_output=True)
        try:
            pause_sim(True)
            post({'type': 'scenario', 'name': 'battery_low'})
            wait(lambda d: d['state'] == 'FAULT', timeout=4)
            results['paused_simulator_http_responsive'] = True
        finally:
            pause_sim(False)
        restore()
        wait(lambda d: d['state'] == 'COMPLETE')
        results['passed'] = True
        print('PASS: live safety and offline interaction scenarios', flush=True)
    except Exception as exc:
        results.update(passed=False, error=str(exc))
        post({'type': 'pause'})
        raise
    finally:
        REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
