#!/usr/bin/env python3
"""Opt-in creation/removal regression; run while the tour is at standby."""
import json
from pathlib import Path
import time
from heritage_tour.scene import SceneBridge


def main():
    scene = SceneBridge()
    result = {'passed': False, 'creations': 0, 'removals': 0}
    start = time.monotonic()
    try:
        for index in range(12):
            name = 'tour_transport_probe_' + str(index)
            try:
                scene._create(scene.person(name, 16, 8))
                result['creations'] += 1
            finally:
                assert scene._service('remove', 'gz.msgs.Entity',
                                      'name: ' + json.dumps(name) + ' type: MODEL')
                result['removals'] += 1
        result['passed'] = True
        print('PASS: 12 actual Gazebo creations and removals', flush=True)
    finally:
        result['elapsed_seconds'] = time.monotonic() - start
        scene.close()
        Path('/tmp/heritage-transport-check.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
