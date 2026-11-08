"""Structural checks complement the real Gazebo drive verification."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class GuideRobotTest(unittest.TestCase):
    def test_dynamic_drivetrain_and_local_resources(self):
        path = ROOT / 'models/heritage_guide/model.sdf'
        self.assertTrue(path.is_file(), 'The guide robot model must exist')
        model = ET.parse(path).getroot().find('model')
        self.assertNotEqual(model.findtext('static'), 'true')
        links = {link.get('name'): link for link in model.findall('link')}
        self.assertIn('base_link', links)
        joints = {joint.get('name'): joint for joint in model.findall('joint')}
        drive = model.find('plugin[@name="gz::sim::systems::DiffDrive"]')
        self.assertIsNotNone(drive)
        for tag in ('left_joint', 'right_joint'):
            joint = joints[drive.findtext(tag)]
            self.assertEqual(joint.get('type'), 'revolute')
            wheel = links[joint.findtext('child')]
            radius = float(wheel.findtext('collision/geometry/cylinder/radius'))
            self.assertAlmostEqual(radius, float(drive.findtext('wheel_radius')))
        self.assertEqual(drive.findtext('topic'), '/heritage_robot/cmd_vel')
        self.assertLessEqual(float(drive.findtext('max_linear_velocity')), 0.4)
        for link in links.values():
            names = [node.get('name') for node in link if node.get('name')]
            self.assertEqual(len(names), len(set(names)), 'SDF link child names must be unique')
            self.assertGreater(float(link.findtext('inertial/mass')), 0)
            inertia = link.find('inertial/inertia')
            moments = [float(inertia.findtext(tag)) for tag in ('ixx', 'iyy', 'izz')]
            self.assertTrue(all(v > 0 for v in moments))
            self.assertLessEqual(max(moments), sum(moments) - max(moments))
        for uri in model.findall('.//uri') + model.findall('.//albedo_map'):
            self.assertTrue(uri.text.startswith('model://heritage_guide/'))
            local = ROOT / 'models' / uri.text.removeprefix('model://')
            self.assertTrue(local.is_file(), str(local))


if __name__ == '__main__':
    unittest.main()
