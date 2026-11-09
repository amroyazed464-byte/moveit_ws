"""Content-addressed, prerecorded Cantonese clips; no network during playback."""
import hashlib


def audio_name(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest() + '.mp3'


def cantonese_audio_url(share, speech):
    if not speech or speech.get('language') != 'yue':
        return None
    name = audio_name(speech['text'])
    return '/audio/yue/' + name if (share / 'voices/yue' / name).is_file() else None
