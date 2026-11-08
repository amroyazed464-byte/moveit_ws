"""Visitor markers must follow acknowledged simulator changes, not planned poses."""
from collections import deque
import importlib.util
from pathlib import Path
import queue
import unittest

SPEC = importlib.util.spec_from_file_location('scene_ack', Path(__file__).resolve().parents[1] / 'heritage_tour/scene.py')
SCENE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCENE)


class SceneAcknowledgementTest(unittest.TestCase):
    def setUp(self):
        self.scene = SCENE.SceneBridge.__new__(SCENE.SceneBridge)
        self.scene.robot = {'x': 3., 'y': 0., 'yaw': 0.}
        self.scene.history = deque([(0., 0., 0.), (1., 0., 0.), (2., 0., 0.), (3., 0., 0.)])
        self.scene.visitors = [{'id': 'tour_visitor_0', 'x': 0., 'y': 0., 'yaw': 0.}]
        self.scene.freeze_visitors = False
        self.scene.crossing_until = 0.
        self.scene.latest_poses = None
        self.scene.closed = False
        self.scene.motion_ok = True
        self.scene.linkage_ok = True
        self.scene.last_error = ''
        self.scene.commands = queue.Queue()
        self.scene.notifications = queue.Queue()

    def test_failed_pose_service_keeps_last_acknowledged_visitor_position(self):
        self.scene.animate(1.)
        self.assertEqual(self.scene.visitors[0]['x'], 0.)
        def fail(*args):
            self.scene.closed = True
            raise RuntimeError('pose service unavailable')
        self.scene._service = fail
        self.scene._work()
        self.assertEqual(self.scene.visitors[0]['x'], 0.)
        self.assertFalse(self.scene.motion_ok)
        self.assertEqual(self.scene.notifications.get_nowait()['operation'], 'visitor_pose')

    def test_successful_pose_service_commits_position_and_restores_health(self):
        self.scene.animate(1.)
        self.scene.motion_ok = False
        def succeed(*args):
            self.scene.closed = True
            return True
        self.scene._service = succeed
        self.scene._work()
        self.assertGreater(self.scene.visitors[0]['x'], 0.)
        self.assertTrue(self.scene.motion_ok)


if __name__ == '__main__':
    unittest.main()
