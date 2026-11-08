#!/usr/bin/env python3
"""Check fresh GUI startup, short actual motion, pause and return; leave visitors ready."""
import json
import math
import time
from pathlib import Path
from run_safety_scenarios import post, state, stopped, wait


def main():
    started = time.monotonic()
    wait(lambda d: d['ready'] and d['scene_linkage']['ok'], timeout=100)
    assert state()['state'] in ('IDLE', 'WELCOMING', 'COMPLETE')
    post({'type': 'visitors', 'count': 3})
    wait(lambda d: not d['pending_visitors'] and d['visitor_count'] == 3)
    origin = state()['world_pose']
    post({'type': 'start', 'mode': 'general', 'language': 'zh', 'auto_advance': False})
    current = wait(lambda d: math.hypot(d['world_pose']['x'] - origin['x'],
                                     d['world_pose']['y'] - origin['y']) > .30, timeout=45)
    moved = math.hypot(current['world_pose']['x'] - origin['x'], current['world_pose']['y'] - origin['y'])
    post({'type': 'pause'})
    drift = stopped()
    post({'type': 'end'})
    current = wait(lambda d: d['state'] == 'COMPLETE', timeout=120)
    assert current['ready'] and current['scene_linkage']['ok']
    home_distance = math.hypot(current['world_pose']['x'] + 13.27, current['world_pose']['y'] + 7.73)
    assert home_distance < .55
    Path('/tmp/heritage-final-smoke.json').write_text(json.dumps(
        {'passed': True, 'elapsed_seconds': time.monotonic() - started, 'forward_distance_m': moved, 'pause_drift_m': drift,
         'home_distance_m': home_distance, 'scene_linkage': current['scene_linkage']}, indent=2))
    post({'type': 'visitors', 'count': 3})
    wait(lambda d: not d['pending_visitors'] and d['visitor_count'] == 3)
    print('PASS: final GUI startup, actual motion, stop, return and three visitors ready', flush=True)


if __name__ == '__main__':
    main()
