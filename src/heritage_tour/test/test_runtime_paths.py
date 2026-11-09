"""Deployment must not depend on the original developer's workspace name."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('runtime_paths', ROOT / 'heritage_tour/runtime_paths.py')
PATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATHS)


class RuntimePathsTest(unittest.TestCase):
    def test_workspace_launcher_can_choose_its_own_log_directory(self):
        with patch.dict(os.environ, {'HERITAGE_TOUR_LOG_DIR': '/tmp/relocated demo/log/heritage_tour'}):
            self.assertEqual(PATHS.event_log_path(), Path('/tmp/relocated demo/log/heritage_tour/events.jsonl'))

    def test_direct_ros_launch_uses_xdg_state_directory(self):
        with patch.dict(os.environ, {'HERITAGE_TOUR_LOG_DIR': '', 'XDG_STATE_HOME': '/tmp/user-state'}):
            self.assertEqual(PATHS.event_log_path(), Path('/tmp/user-state/heritage_tour/events.jsonl'))

    def test_fallback_does_not_create_the_original_workspace_name(self):
        with patch.dict(os.environ, {'HERITAGE_TOUR_LOG_DIR': '', 'XDG_STATE_HOME': ''}), \
                patch.object(PATHS.Path, 'home', return_value=Path('/tmp/other-user')):
            self.assertEqual(PATHS.event_log_path(), Path('/tmp/other-user/.local/state/heritage_tour/events.jsonl'))
