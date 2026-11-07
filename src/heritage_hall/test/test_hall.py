"""Check the delivered geometry, including clearance for a 0.6 m robot."""
from collections import deque
from pathlib import Path
import math
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class HallTest(unittest.TestCase):
    def test_floor_mesh_has_normals_for_ogre2(self):
        ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
        mesh = ET.parse(ROOT / 'meshes/floor.dae').getroot()
        normals = mesh.findall('.//c:triangles/c:input[@semantic="NORMAL"]', ns)
        self.assertTrue(normals, 'Ogre2 textured meshes require explicit normals')

    def test_world_and_walkable_zones(self):
        path = ROOT / 'worlds' / 'heritage_hall.sdf'
        self.assertTrue(path.is_file(), 'The Gazebo hall must exist')
        world = ET.parse(path).getroot().find('world')
        obstacles = []
        names = set()
        for model in world.findall('model'):
            self.assertNotIn(model.get('name'), names)
            names.add(model.get('name'))
            for collision in model.findall('link/collision'):
                pose = [float(v) for v in collision.findtext('pose', '0 0 0 0 0 0').split()]
                box = collision.find('geometry/box')
                cylinder = collision.find('geometry/cylinder')
                if box is not None:
                    sx, sy, sz = map(float, box.findtext('size').split())
                    if pose[2] + sz / 2 > 0.12 and pose[2] - sz / 2 < 0.65:
                        obstacles.append(('box', pose, (sx, sy)))
                elif cylinder is not None:
                    obstacles.append(('circle', pose, float(cylinder.findtext('radius'))))
        self.assertIn('central_column', names)
        self.assertGreater(len(obstacles), 30)
        radius, step = 0.30, 0.1

        def free(x, y):
            # Do not let a path bypass a blocked aisle via unsupported space.
            for px in (x - radius, x + radius):
                for py in (y - radius, y + radius):
                    on_floor = -17.7 <= px <= 17.7 and -11 <= py <= 11
                    on_apron = -12.6 <= py <= -11 and any(abs(px - door) <= 1.4 for door in (-12.5, 9.4))
                    if not (on_floor or on_apron):
                        return False
            for shape, pose, size in obstacles:
                dx, dy = x - pose[0], y - pose[1]
                if shape == 'circle':
                    if math.hypot(dx, dy) < size + radius:
                        return False
                else:
                    c, s = math.cos(pose[5]), math.sin(pose[5])
                    u, v = c * dx + s * dy, -s * dx + c * dy
                    if abs(u) < size[0] / 2 + radius and abs(v) < size[1] / 2 + radius:
                        return False
            return True

        def cell(x, y):
            return round((x + 19) / step), round((y + 13) / step)

        start = cell(-12.5, -11.4)
        reached, queue = {start}, deque([start])
        while queue:
            i, j = queue.popleft()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if (a, b) in reached or not (0 <= a <= 380 and 0 <= b <= 260):
                    continue
                if free(a * step - 19, b * step - 13):
                    reached.add((a, b))
                    queue.append((a, b))
        targets = {
            'entrance_inside': (-12.5, -9), 'overview': (-13.6, 0),
            'craft': (-2, 4.8), 'masterpieces': (-2, -7.3),
            'history': (7, -1), 'interactive': (10, 5.8),
            'exit_inside': (9.4, -9), 'exit_outside': (9.4, -11.4),
        }
        for name, point in targets.items():
            self.assertTrue(free(*point), f'{name} is obstructed')
            self.assertIn(cell(*point), reached, f'{name} is disconnected')


if __name__ == '__main__':
    unittest.main()
