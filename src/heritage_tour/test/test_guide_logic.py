"""Pure business acceptance checks; no ROS, browser or robot doubles."""
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('guide_logic', ROOT / 'heritage_tour/guide_logic.py')
if SPEC and SPEC.loader and Path(SPEC.origin).exists():
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)
    GuideSession = MODULE.GuideSession
else:
    GuideSession = None


def fixture():
    return {
        'home': [0, 0, 0],
        'sources': [{'id': 'official', 'title': 'Official', 'url': 'https://ich.unesco.org/en/'}],
        'zones': [{
            'id': name, 'name': name, 'pose': [i, 1, 0],
            'narrations': {'child': '儿童讲解', 'general': '大众讲解', 'deep': '深度讲解'},
            'english': {'child': 'For children', 'general': 'General story', 'deep': 'Deep story'},
            'quiz': {'id': name + '_quiz', 'question': '保护什么？',
                     'question_en': 'What should we safeguard?',
                     'options': [{'id': 'A', 'text': '技艺', 'en': 'Skills'},
                                 {'id': 'B', 'text': '只有物品', 'en': 'Only objects'}],
                     'answer': 'A', 'reason': '技艺需要传承。', 'reason_en': 'Skills are transmitted.',
                     'source_ids': ['official']},
            'qa': [{'question': '什么是非遗', 'question_en': 'What is living heritage',
                    'aliases': ['非遗是什么'], 'answer': '代代传承的技艺和实践。',
                    'answer_en': 'Transmitted skills and practices.', 'source_ids': ['official']}],
        } for i, name in enumerate(['overview', 'craft', 'masterpieces', 'history', 'interactive'])],
    }


class GuideSessionTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(GuideSession, 'GuideSession implementation is required')
        self.session = GuideSession(fixture())

    def send(self, event_type, **fields):
        return self.session.apply({'type': event_type, **fields})

    def start(self, **fields):
        return self.send('start', **fields)

    def present(self):
        self.start()
        return self.send('arrived', zone_id='overview')

    def finish_speech(self):
        speech = self.session.snapshot()['speech']
        return self.send('speech_done', speech_id=speech['id'])

    def test_single_and_group_welcome_do_not_move(self):
        for count in (1, 4):
            effects = self.send('visitor', count=count)
            snap = self.session.snapshot()
            self.assertEqual(snap['state'], 'WELCOMING')
            self.assertEqual(snap['visitor_count'], count)
            self.assertTrue(any(e['type'] == 'speak' for e in effects))
            self.assertFalse(any(e['type'] == 'navigate' for e in effects))
        self.finish_speech()
        self.assertEqual(self.session.snapshot()['state'], 'IDLE')

    def test_complete_five_zone_route_quiz_and_return(self):
        self.start(mode='deep', language='en', auto_advance=True)
        for zone_id in ('overview', 'craft', 'masterpieces', 'history', 'interactive'):
            self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')
            effects = self.send('arrived', zone_id=zone_id)
            self.assertEqual(self.session.snapshot()['state'], 'PRESENTING')
            speech = next(e for e in effects if e['type'] == 'speak')
            self.assertEqual(speech['text'], 'Deep story')
            self.finish_speech()
            self.assertEqual(self.session.snapshot()['state'], 'QUIZ')
            self.send('quiz_answer', answer='A')
        self.assertEqual(self.session.snapshot()['state'], 'RETURNING')
        self.assertEqual(self.session.snapshot()['stats']['quiz_correct'], 5)
        self.send('home_arrived')
        self.assertEqual(self.session.snapshot()['state'], 'COMPLETE')
        self.assertEqual(self.session.snapshot()['stats']['zones_completed'], 5)

    def test_stale_arrivals_and_speech_cannot_advance(self):
        self.start()
        self.send('arrived', zone_id='craft')
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')
        self.send('arrived', zone_id='overview')
        old = self.session.snapshot()['speech']['id']
        self.send('repeat')
        self.send('speech_done', speech_id=old)
        self.assertEqual(self.session.snapshot()['state'], 'PRESENTING')
        self.send('skip')
        self.send('arrived', zone_id='overview')
        self.send('speech_done', speech_id=old)
        self.assertEqual(self.session.snapshot()['zone_id'], 'craft')
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')

    def test_pause_blocks_callbacks_and_resume_restarts_speech(self):
        self.present()
        old = self.session.snapshot()['speech']['id']
        effects = self.send('pause')
        self.assertIn('cancel_navigation', [e['type'] for e in effects])
        self.send('speech_done', speech_id=old)
        self.send('next')
        self.assertEqual(self.session.snapshot()['state'], 'PAUSED')
        self.send('resume')
        self.assertEqual(self.session.snapshot()['state'], 'PRESENTING')
        self.assertNotEqual(self.session.snapshot()['speech']['id'], old)

    def test_paused_navigation_reissues_same_destination(self):
        self.start()
        self.send('pause')
        self.send('arrived', zone_id='overview')
        effects = self.send('resume')
        goal = next(e for e in effects if e['type'] == 'navigate')
        self.assertEqual(goal['zone_id'], 'overview')
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')

    def test_navigation_identity_rejects_cancelled_goal_at_same_zone(self):
        first = self.start()
        old = next(e for e in first if e['type'] == 'navigate')['navigation_id']
        self.send('pause')
        resumed = self.send('resume')
        current = next(e for e in resumed if e['type'] == 'navigate')['navigation_id']
        self.send('arrived', zone_id='overview', navigation_id=old)
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')
        self.send('arrived', zone_id='overview', navigation_id=current)
        self.assertEqual(self.session.snapshot()['state'], 'PRESENTING')

    def test_fault_origin_distinguishes_live_detection_from_simulation(self):
        self.start()
        self.send('fault', kind='localization_lost')
        self.assertFalse(self.session.snapshot()['fault']['simulated'])
        self.send('fault', kind='battery_low', simulated=True)
        self.assertTrue(self.session.snapshot()['fault']['simulated'])

    def test_all_faults_require_explicit_recovery_and_resume(self):
        for kind in ('unclear', 'visitor_lost', 'blocked', 'localization_lost', 'battery_low'):
            with self.subTest(kind=kind):
                self.session = GuideSession(fixture())
                self.start()
                effects = self.send('fault', kind=kind)
                self.assertEqual(self.session.snapshot()['state'], 'FAULT')
                self.assertIn('cancel_navigation', [e['type'] for e in effects])
                self.send('arrived', zone_id='overview')
                self.send('resume')
                self.send('next')
                self.assertEqual(self.session.snapshot()['state'], 'FAULT')
                effects = self.send('recover')
                self.assertEqual(self.session.snapshot()['state'], 'PAUSED')
                self.assertFalse(any(e['type'] == 'navigate' for e in effects))
                self.send('resume')
                self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')

    def test_nested_fault_during_pause_keeps_original_resume_target(self):
        self.present()
        self.send('pause')
        self.send('fault', kind='blocked')
        self.send('fault', kind='localization_lost')
        self.send('recover')
        self.send('resume')
        self.assertEqual(self.session.snapshot()['state'], 'PRESENTING')

    def test_manual_requires_recover_then_resume(self):
        self.start()
        effects = self.send('manual')
        self.assertIn('human_help', [e['type'] for e in effects])
        self.send('arrived', zone_id='overview')
        self.send('resume')
        self.assertEqual(self.session.snapshot()['state'], 'MANUAL')
        self.send('recover')
        self.assertEqual(self.session.snapshot()['state'], 'PAUSED')
        self.send('resume')
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')

    def test_known_question_is_sourced_and_unknown_is_referred(self):
        self.present()
        self.send('question', text='非遗是什么？')
        qa = self.session.snapshot()['qa']
        self.assertTrue(qa['answered'])
        self.assertEqual(qa['source_ids'], ['official'])
        self.finish_speech()
        self.assertEqual(self.session.snapshot()['speech']['kind'], 'narration')
        effects = self.send('question', text='这件馆藏真品值多少钱？')
        self.assertFalse(self.session.snapshot()['qa']['answered'])
        self.assertIn('human_help', [e['type'] for e in effects])
        # A keyword alone must not turn an unsupported question into a known one.
        self.send('question', text='非遗是什么价格可以购买股票吗')
        self.assertFalse(self.session.snapshot()['qa']['answered'])

    def test_wrong_quiz_answer_reveals_reason_once_without_auto_move(self):
        self.present()
        self.finish_speech()
        self.send('quiz_answer', answer='B')
        snap = self.session.snapshot()
        self.assertEqual(snap['state'], 'READY_NEXT')
        self.assertFalse(snap['quiz']['result']['correct'])
        self.assertEqual(snap['quiz']['result']['reason'], '技艺需要传承。')
        self.send('quiz_answer', answer='A')
        self.assertEqual(self.session.snapshot()['stats']['quiz_attempts'], 1)
        self.send('next')
        self.assertEqual(self.session.snapshot()['zone_id'], 'craft')

    def test_repeat_after_answer_does_not_reopen_answered_quiz(self):
        self.present()
        self.finish_speech()
        self.send('quiz_answer', answer='A')
        self.send('repeat')
        self.finish_speech()
        self.assertEqual(self.session.snapshot()['state'], 'READY_NEXT')
        self.assertEqual(self.session.snapshot()['stats']['quiz_attempts'], 1)

    def test_new_tour_task_card_does_not_reuse_last_tour_score(self):
        self.present()
        self.finish_speech()
        self.send('quiz_answer', answer='A')
        self.send('end')
        self.send('home_arrived')
        self.start()
        card = self.session.snapshot()['task_card']
        self.assertEqual(card['score'], 0)
        self.assertEqual(card['answered'], 0)
        self.assertEqual(card['visited'], [])
        self.assertEqual(self.session.snapshot()['stats']['sessions'], 2)

    def test_end_cancels_navigation_and_home_only_completes_return(self):
        self.send('home_arrived')
        self.assertEqual(self.session.snapshot()['state'], 'IDLE')
        self.start()
        effects = self.send('end')
        self.assertEqual(self.session.snapshot()['state'], 'RETURNING')
        self.assertIn('cancel_navigation', [e['type'] for e in effects])
        self.assertEqual(next(e for e in effects if e['type'] == 'navigate')['pose'], [0, 0, 0])
        self.send('arrived', zone_id='overview')
        self.assertEqual(self.session.snapshot()['state'], 'RETURNING')
        self.send('home_arrived')
        self.assertEqual(self.session.snapshot()['state'], 'COMPLETE')

    def test_fault_or_manual_cannot_be_bypassed_by_start_skip_or_end(self):
        self.start()
        self.send('fault', kind='battery_low')
        for command in ('start', 'skip', 'next', 'end', 'repeat'):
            effects = self.send(command)
            self.assertEqual(self.session.snapshot()['state'], 'FAULT')
            self.assertFalse(any(e['type'] == 'navigate' for e in effects))

    def test_fault_after_completion_blocks_new_tour_until_recover_and_resume(self):
        self.start()
        self.send('end')
        self.send('home_arrived')
        self.assertEqual(self.session.snapshot()['state'], 'COMPLETE')
        self.send('fault', kind='battery_low', simulated=True)
        self.assertEqual(self.session.snapshot()['state'], 'FAULT')
        for command in ('start', 'skip', 'end'):
            effects = self.send(command)
            self.assertEqual(self.session.snapshot()['state'], 'FAULT')
            self.assertFalse(any(e['type'] == 'navigate' for e in effects))
        self.send('recover')
        self.assertEqual(self.session.snapshot()['state'], 'PAUSED')
        effects = self.start()
        self.assertFalse(any(e['type'] == 'navigate' for e in effects))
        effects = self.send('resume')
        self.assertEqual(self.session.snapshot()['state'], 'COMPLETE')
        self.assertFalse(any(e['type'] == 'navigate' for e in effects))
        effects = self.start()
        self.assertEqual(self.session.snapshot()['state'], 'NAVIGATING')
        self.assertEqual(next(e for e in effects if e['type'] == 'navigate')['zone_id'], 'overview')

    def test_invalid_commands_do_not_change_state_or_preferences(self):
        for event in ({'type': 'start', 'mode': 'invalid'},
                      {'type': 'start', 'language': 'fr'},
                      {'type': 'start', 'auto_advance': 'false'},
                      {'type': 'visitor', 'count': -1}, {'type': 'visitor', 'count': True},
                      {'type': 'does_not_exist'}):
            with self.assertRaises(ValueError):
                self.session.apply(event)
            self.assertEqual(self.session.snapshot()['state'], 'IDLE')
        self.start()
        effects = self.start()
        self.assertFalse(any(e['type'] == 'navigate' for e in effects))

    def test_snapshots_and_input_content_are_detached(self):
        content = fixture()
        session = GuideSession(content)
        content['zones'][0]['pose'][0] = 999
        effects = session.apply({'type': 'start'})
        self.assertEqual(next(e for e in effects if e['type'] == 'navigate')['pose'], [0, 1, 0])
        snap = session.snapshot()
        snap['stats']['faults'] = 999
        self.assertEqual(session.snapshot()['stats']['faults'], 0)

    def test_missing_or_ambiguous_content_rejected(self):
        content = fixture()
        content['zones'][1]['id'] = 'overview'
        with self.assertRaises(ValueError):
            GuideSession(content)


class DeliveredContentTest(unittest.TestCase):
    def test_five_zones_have_three_bilingual_levels_quiz_and_sourced_answers(self):
        content = json.loads((ROOT / 'config/content.json').read_text(encoding='utf-8'))
        self.assertEqual([z['id'] for z in content['zones']],
                         ['overview', 'craft', 'masterpieces', 'history', 'interactive'])
        source_ids = {s['id'] for s in content['sources']}
        for zone in content['zones']:
            for language in ('narrations', 'english'):
                self.assertEqual(set(zone[language]), {'child', 'general', 'deep'})
                self.assertTrue(all(zone[language].values()))
            self.assertTrue(zone['quiz']['reason'])
            self.assertGreaterEqual(len(zone['qa']), 2)
            for answer in zone['qa']:
                self.assertTrue(answer['source_ids'])
                self.assertLessEqual(set(answer['source_ids']), source_ids)
        self.assertTrue(content['exhibition_notice'])


if __name__ == '__main__':
    unittest.main()
