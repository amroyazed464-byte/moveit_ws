"""Portable locations for generated runtime files."""
import os
from pathlib import Path


def event_log_path():
    directory = os.environ.get('HERITAGE_TOUR_LOG_DIR')
    if not directory:
        state = os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state'
        directory = Path(state) / 'heritage_tour'
    return Path(directory) / 'events.jsonl'
