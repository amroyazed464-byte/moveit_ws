#!/usr/bin/env python3
"""Opt-in public API screen transition stress check; leaves the demo in FAULT."""
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

URL = 'http://127.0.0.1:8765'


def state():
    return json.load(urllib.request.urlopen(URL + '/api/state', timeout=5))


def post(event):
    request = urllib.request.Request(URL + '/api/command', json.dumps(event).encode(),
                                     {'Content-Type': 'application/json'})
    assert json.load(urllib.request.urlopen(request, timeout=5))['ok']


def main():
    deadline = time.monotonic() + 75
    while True:
        try:
            current = state()
            if current.get('ready') and current['scene_linkage']['ok']:
                break
        except urllib.error.URLError:
            pass
        assert time.monotonic() < deadline, 'Scene startup failed'
        time.sleep(.3)
    for index in range(8):
        post({'type': 'scenario', 'name': 'unclear'})
        time.sleep(.4)
        current = state()
        assert current['state'] == 'FAULT' and current['ready']
        assert current['scene_linkage']['ok'], current['scene_linkage']
        if index < 7:
            post({'type': 'scenario', 'name': 'clear'})
            post({'type': 'recover'})
            post({'type': 'resume'})
            time.sleep(.4)
            assert state()['ready']
    Path('/tmp/heritage-screen-linkage.json').write_text(json.dumps(
        {'passed': True, 'fault_transitions': 8, 'restores': 7,
         'scan_fresh': current['safety']['scan_fresh'], 'scene_linkage': current['scene_linkage']}, indent=2))
    print('PASS: fresh startup and 15 public API screen transitions; capture FAULT visuals now', flush=True)


if __name__ == '__main__':
    main()
