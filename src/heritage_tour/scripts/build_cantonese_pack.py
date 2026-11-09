#!/usr/bin/env python3
"""Build once online; deployed playback uses only bundled MP3 files.

Build dependencies: edge-tts==7.3.1 and imageio-ffmpeg. No build dependencies
are imported by the ROS runtime. Existing clips are retained unless --rebuild.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from heritage_tour.guide_logic import GuideSession, FAULTS
from heritage_tour.voice_pack import audio_name

VOICE = 'zh-HK-HiuGaaiNeural'
PREVIEW = '歡迎嚟到非遺展館，我係你嘅導覽機械人。我可以用粵語帶你參觀五個展區。'


def utterances(content):
    """Enumerate the actual policy's fixed Cantonese speech, including greetings."""
    texts = set()

    def collect(session, event):
        session.apply(event)
        if session.speech:
            texts.add(session.speech['text'])

    for mode in ('child', 'general', 'deep'):
        session = GuideSession(content)
        session.apply({'type': 'start', 'language': 'yue', 'mode': mode, 'auto_advance': True})
        for zone in content['zones']:
            collect(session, {'type': 'arrived', 'zone_id': zone['id']})
            for qa in zone['qa']:
                collect(session, {'type': 'question', 'text': qa['question']})
            collect(session, {'type': 'repeat'})
            session.apply({'type': 'speech_done', 'speech_id': session.speech['id']})
            session.apply({'type': 'quiz_answer', 'answer': zone['quiz']['answer']})
        collect(session, {'type': 'home_arrived'})
    for count in (1, 3):
        session = GuideSession(content)
        session.apply({'type': 'language', 'language': 'yue'})
        collect(session, {'type': 'visitor', 'count': count})
    for fault in list(FAULTS) + ['sensor_stale']:
        session = GuideSession(content)
        session.apply({'type': 'language', 'language': 'yue'})
        collect(session, {'type': 'fault', 'kind': fault})
    return sorted(texts)


def duration(ffmpeg, path):
    result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path)], capture_output=True)
    match = re.search(rb'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
    if not match:
        raise RuntimeError('No playable audio: ' + str(path))
    hours, minutes, seconds = map(float, match.groups())
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
    return hours * 3600 + minutes * 60 + seconds


async def main():
    import edge_tts
    import imageio_ffmpeg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'voices/yue'
    output.mkdir(parents=True, exist_ok=True)
    content = json.loads((ROOT / 'config/content.json').read_text(encoding='utf-8'))
    clips = {audio_name(text): text for text in utterances(content)}
    clips['preview.mp3'] = PREVIEW
    semaphore = asyncio.Semaphore(2)

    async def generate(name, text):
        async with semaphore:
            path = output / name
            if not path.is_file() or args.rebuild:
                temporary = path.with_suffix('.mp3.part')
                await asyncio.wait_for(edge_tts.Communicate(text, voice=VOICE, rate='-5%').save(str(temporary)), 60)
                if temporary.stat().st_size < 1000:
                    raise RuntimeError('Empty speech response for ' + name)
                temporary.replace(path)
            print('Ready: ' + name, flush=True)

    await asyncio.gather(*(generate(name, text) for name, text in clips.items()))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    entries = {name: {'text': text, 'duration_seconds': duration(ffmpeg, output / name),
                      'sha256': hashlib.sha256((output / name).read_bytes()).hexdigest()}
               for name, text in clips.items()}
    manifest = {'language': 'yue', 'locale': 'zh-HK', 'voice': VOICE, 'rate': '-5%',
                'text_policy': 'Original Chinese scripts read aloud in Cantonese; not a colloquial rewrite.',
                'generation': 'Microsoft Edge online TTS via edge-tts 7.3.1; playback is offline.',
                'voice_reference': 'https://learn.microsoft.com/azure/cognitive-services/speech-service/language-support?tabs=tts',
                'entries': entries}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Validated {len(entries)} Cantonese clips', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
