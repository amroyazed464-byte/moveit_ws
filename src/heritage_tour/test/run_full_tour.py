#!/usr/bin/env python3
"""Drive the public demo API; arrivals must come from real Nav2 results.

Narration acknowledgements and quiz answers are explicitly simulated visitors.
This is an opt-in integration run, not part of the unit-test command.
"""
import argparse
import json
import math
from pathlib import Path
import time
import urllib.request
import urllib.error


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8765')
    parser.add_argument('--report',default='/tmp/heritage-full-tour.json')
    args=parser.parse_args()
    def state():return json.load(urllib.request.urlopen(args.url+'/api/state',timeout=5))
    def post(event):
        req=urllib.request.Request(args.url+'/api/command',json.dumps(event).encode(),{'Content-Type':'application/json'})
        return json.load(urllib.request.urlopen(req,timeout=5))
    deadline=time.monotonic()+75
    while True:
        try:ready=state().get('ready')
        except urllib.error.URLError:ready=False
        if ready:break
        assert time.monotonic()<deadline,'Navigation did not become ready'
        time.sleep(.5)
    post({'type':'visitors','count':1})
    while state().get('visitor_count')!=1:
        assert time.monotonic()<deadline,'Visitor model did not appear'
        time.sleep(.3)
    post({'type':'start','mode':'general','language':'zh','auto_advance':True})
    start=time.monotonic();arrivals={};last_print=0;seen_speech=set();answers=set()
    result={'scenario':'actual five-zone navigation; simulated subtitle acknowledgements and quiz answers','arrivals':arrivals}
    try:
        while time.monotonic()-start<1000:
            d=state();phase=d['state']
            if time.monotonic()-last_print>20:
                print(json.dumps({'state':phase,'zone':d.get('zone_id'),'pose':d.get('world_pose'),'distance':d['navigation'].get('distance_remaining'),'safety':d['safety']['reason']},ensure_ascii=False),flush=True)
                last_print=time.monotonic()
            assert phase not in ('FAULT','MANUAL'),json.dumps(d.get('fault') or d.get('human_help'))
            if phase=='PRESENTING' and d.get('speech',{}).get('kind')=='narration':
                zone=next(z for z in d['route'] if z['id']==d['zone_id'])
                actual=d['world_pose'];distance=math.hypot(actual['x']-zone['pose'][0],actual['y']-zone['pose'][1])
                assert distance<.55,(zone['id'],actual,distance)
                arrivals[zone['id']]={'world_pose':actual,'distance_to_stop':distance,'localization_error':d['safety']['localization_error']}
                speech=d['speech']['id']
                if speech not in seen_speech:
                    seen_speech.add(speech);post({'type':'speech_done','speech_id':speech})
            elif phase=='QUIZ' and d['zone_id'] not in answers:
                zone=next(z for z in d['route'] if z['id']==d['zone_id'])
                answers.add(zone['id']);post({'type':'quiz_answer','answer':zone['quiz']['answer']})
            elif phase=='COMPLETE':
                assert len(arrivals)==5,arrivals
                home=(-13.27,-7.73);p=d['world_pose'];distance=math.hypot(p['x']-home[0],p['y']-home[1])
                assert distance<.55,distance
                result.update(passed=True,elapsed_seconds=time.monotonic()-start,home_distance=distance,stats=d['stats'])
                print('PASS: all five real stops and return home completed',flush=True)
                break
            time.sleep(.5)
        else:raise AssertionError('Full tour timed out')
    except Exception as exc:
        result.update(passed=False,error=str(exc),last_state=state())
        post({'type':'pause'})
        raise
    finally:
        Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
