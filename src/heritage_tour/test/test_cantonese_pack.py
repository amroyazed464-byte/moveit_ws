"""Verify shipped clips cover real guide utterances and stay local to the pack."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from heritage_tour.voice_pack import audio_name, cantonese_audio_url

SPEC = importlib.util.spec_from_file_location('build_cantonese_pack', ROOT / 'scripts/build_cantonese_pack.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class CantonesePackTest(unittest.TestCase):
    def test_language_match_missing_file_and_content_address(self):
        speech = {'language': 'yue', 'text': '../欢迎参观'}
        with tempfile.TemporaryDirectory() as directory:
            share = Path(directory)
            self.assertIsNone(cantonese_audio_url(share, speech))
            clip = share / 'voices/yue' / audio_name(speech['text'])
            clip.parent.mkdir(parents=True)
            clip.write_bytes(b'clip')
            self.assertRegex(cantonese_audio_url(share, speech), r'^/audio/yue/[a-f0-9]{64}\.mp3$')
            self.assertIsNone(cantonese_audio_url(share, dict(speech, language='zh')))

    def test_every_real_cantonese_utterance_has_a_verified_shipped_clip(self):
        content = json.loads((ROOT / 'config/content.json').read_text(encoding='utf-8'))
        pack = ROOT / 'voices/yue'
        manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['voice'], 'zh-HK-HiuGaaiNeural')
        texts = BUILD.utterances(content)
        self.assertGreaterEqual(len(texts), 35)
        self.assertEqual(set(manifest['entries']), {audio_name(t) for t in texts} | {'preview.mp3'})
        for name, entry in manifest['entries'].items():
            with self.subTest(name=name):
                data = (pack / name).read_bytes()
                self.assertGreater(len(data), 1000)
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
                self.assertGreater(entry['duration_seconds'], .25)
                self.assertLess(entry['duration_seconds'], 180)
                if name != 'preview.mp3':
                    self.assertEqual(name, audio_name(entry['text']))


if __name__ == '__main__':
    unittest.main()
