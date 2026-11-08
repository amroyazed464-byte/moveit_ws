"""Exercise the real runtime boundary methods without importing ROS or Gazebo."""
import ast
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import time
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('guide_logic_boundaries', ROOT / 'heritage_tour/guide_logic.py')
LOGIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOGIC)


class PoseStamped:
    def __init__(self):
        self.header = SimpleNamespace(frame_id='', stamp=None)
        self.pose = SimpleNamespace(position=SimpleNamespace(x=0., y=0.),
                                    orientation=SimpleNamespace(z=0., w=1.))


class DeferredFuture:
    def __init__(self):
        self.callbacks = []

    def result(self):
        return self.value

    def add_done_callback(self, callback):
        self.callbacks.append(callback)

    def resolve(self, value):
        self.value = value
        for callback in self.callbacks:
            callback(self)

    def cancel(self):
        self.cancelled = True


def runtime_class():
    """Compile original methods, replacing only ROS message/base dependencies."""
    source = ROOT / 'scripts/tour_runtime.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    constants = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id in ('PUBLIC', 'SCENARIOS')
                         for target in node.targets)]
    runtime = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'TourRuntime')
    runtime.bases = []
    runtime.body = [node for node in runtime.body if isinstance(node, ast.FunctionDef)
                    and node.name in ('command', '_navigate', 'tick')]
    tick = next(node for node in runtime.body if node.name == 'tick')
    end = next(index for index, node in enumerate(tick.body)
               if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'scan_fresh' for t in node.targets))
    tick.body = tick.body[:end]
    namespace = {'PoseStamped': PoseStamped, 'math': math, 'time': time,
                 'deepcopy': deepcopy, 'NavigateToPose': SimpleNamespace(Goal=SimpleNamespace),
                 'GetState': SimpleNamespace(Request=SimpleNamespace)}
    module = ast.fix_missing_locations(ast.Module(body=constants + [runtime], type_ignores=[]))
    exec(compile(module, str(source), 'exec'), namespace)
    return namespace['TourRuntime']


Runtime = runtime_class()


class RuntimeBoundariesTest(unittest.TestCase):
    def setUp(self):
        content = json.loads((ROOT / 'config/content.json').read_text(encoding='utf-8'))
        self.runtime = Runtime()
        self.runtime.session = LOGIC.GuideSession(content)
        self.runtime.ready = True
        self.runtime.pending_visitors = False
        self.runtime.injections = set()
        self.runtime.battery = 85
        self.runtime.human_help = None
        self.runtime.tour_started = False
        self.runtime.speech_deadline = 123.
        self.runtime.speech_client_until = None
        self.runtime.speech_client_id = None
        self.scene_commands = []
        self.runtime.scene = SimpleNamespace(
            visitors=[{'id': 'existing_visitor'}], robot=None,
            submit=lambda operation, **fields: self.scene_commands.append((operation, fields)))
        self.effects = []

        def apply(event):
            effects = self.runtime.session.apply(event)
            self.effects.extend(effects)
            return effects

        self.runtime.apply = apply

    def assert_no_navigation(self):
        self.assertFalse(any(effect['type'] == 'navigate' for effect in self.effects))

    def start_pending_goal(self):
        effect = next(effect for effect in self.runtime.session.apply({'type': 'start'})
                      if effect['type'] == 'navigate')
        accepted = DeferredFuture()
        finished = DeferredFuture()
        self.runtime.goal_epoch = 0
        self.runtime.navigation = {}
        self.runtime.active_goal = None
        self.runtime.get_clock = lambda: SimpleNamespace(
            now=lambda: SimpleNamespace(to_msg=lambda: None))
        self.runtime.nav = SimpleNamespace(send_goal_async=lambda *args, **kwargs: accepted)
        self.runtime._navigate(effect)
        accepted.resolve(SimpleNamespace(accepted=True, get_result_async=lambda: finished))
        return finished

    def test_start_rejected_while_visitor_replacement_is_pending(self):
        self.runtime.command({'type': 'visitors', 'count': 0})
        self.assertEqual(self.scene_commands, [('visitors', {'count': 0})])
        with self.assertRaises(ValueError):
            self.runtime.command({'type': 'start'})
        self.assert_no_navigation()

    def test_completed_tour_cannot_restart_with_low_battery_injection(self):
        self.runtime.session.state = 'COMPLETE'
        self.runtime.command({'type': 'scenario', 'name': 'battery_low'})
        self.assertIn('battery_low', self.runtime.injections)
        with self.assertRaises(ValueError):
            self.runtime.command({'type': 'start'})
        self.assert_no_navigation()

    def test_current_goal_cancellation_enters_fault(self):
        finished = self.start_pending_goal()
        finished.resolve(SimpleNamespace(status=5))
        self.assertEqual(self.runtime.session.state, 'FAULT')
        self.assertTrue(any(effect['type'] == 'cancel_navigation' for effect in self.effects))

    def test_old_goal_cancellation_cannot_change_paused_session(self):
        finished = self.start_pending_goal()
        self.runtime.apply({'type': 'pause'})
        self.runtime.goal_epoch += 1
        self.runtime.active_goal = None
        self.effects.clear()
        finished.resolve(SimpleNamespace(status=5))
        self.assertEqual(self.runtime.session.state, 'PAUSED')
        self.assertEqual(self.effects, [])

    def test_browser_narration_lease_only_accepts_current_speech(self):
        self.runtime.apply({'type': 'visitor', 'count': 1})
        speech_id = self.runtime.session.speech['id']
        self.runtime.command({'type': 'speech_started', 'speech_id': 'stale'})
        self.assertEqual(self.runtime.speech_deadline, 123.)
        self.assertIsNone(self.runtime.speech_client_until)
        self.runtime.command({'type': 'speech_started', 'speech_id': speech_id})
        self.assertIsNone(self.runtime.speech_deadline)
        self.assertGreater(self.runtime.speech_client_until, time.monotonic())
        self.runtime.command({'type': 'speech_aborted', 'speech_id': speech_id})
        self.assertIsNone(self.runtime.speech_client_until)
        self.assertGreater(self.runtime.speech_deadline, time.monotonic())

    def test_public_commands_cannot_forge_physical_arrival(self):
        for event in ({'type': 'arrived', 'zone_id': 'overview'}, {'type': 'home_arrived'}):
            with self.subTest(event=event), self.assertRaises(ValueError):
                self.runtime.command(event)
        self.assertEqual(self.runtime.session.state, 'IDLE')

    def test_unanswered_lifecycle_request_is_retried_after_restart(self):
        old = DeferredFuture()
        fresh = DeferredFuture()
        self.runtime._locate = lambda: None
        self.runtime.lifecycle_future = old
        self.runtime.nav_active = True
        self.runtime.last_lifecycle_check = time.monotonic() - 20
        self.runtime.lifecycle = SimpleNamespace(service_is_ready=lambda: True,
                                                call_async=lambda request: fresh)
        self.runtime.tick()
        self.assertTrue(old.cancelled)
        self.assertIs(self.runtime.lifecycle_future, fresh)
        self.assertFalse(self.runtime.nav_active)


if __name__ == '__main__':
    unittest.main()
