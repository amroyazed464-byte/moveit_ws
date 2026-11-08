"""Offline, deterministic tour policy. All sensing and movement live in the adapter.

Effects are requests, not proof of physical arrival or successful speech. An adapter
must deliver navigation results only for its current goal; navigation_id is supplied
for that purpose. Recovery requires a separate explicit resume command.
"""
from copy import deepcopy
from datetime import datetime, timezone
import math
import unicodedata


MODES = ('child', 'general', 'deep')
LANGUAGES = ('zh', 'en')
FAULTS = {
    'unclear': ('未听清指令，请使用文字或按钮重试，也可联系工作人员。',
                'The command was unclear. Please use text or buttons, or ask staff.'),
    'visitor_lost': ('有游客掉队，已停止。请在工作人员协助下集合后确认恢复。',
                     'A visitor has fallen behind. Stopped; regroup with staff before recovery.'),
    'route_blocked': ('路线受阻，已停止。请工作人员确认通道安全后恢复。',
                      'The route is blocked. Stopped; staff must confirm a clear path.'),
    'localization_lost': ('定位异常，已停止。请工作人员恢复定位并检查位置。',
                         'Localization is unavailable. Stopped; staff must restore and check it.'),
    'battery_low': ('低电量告警，已停止。请工作人员检查电源，确认后结束返航。',
                    'Low battery. Stopped; ask staff to check power before returning.'),
    'unknown_question': ('该问题超出已核验知识范围，请工作人员解答。',
                         'This question is outside the verified knowledge base. Please ask staff.'),
}


def _normal(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold()
                   if c.isalnum())


class GuideSession:
    """One tour with bounded audit history and explicit safe state transitions."""

    def __init__(self, content):
        self.content = deepcopy(content)
        zones = self.content.get('zones', [])
        ids = [zone.get('id') for zone in zones]
        if len(zones) != 5 or any(not name or name == 'home' for name in ids) or len(set(ids)) != 5:
            raise ValueError('Content requires five uniquely named zones')
        sources = {source['id'] for source in self.content.get('sources', [])}
        for pose in [self.content.get('home')] + [z.get('pose') for z in zones]:
            if (not isinstance(pose, list) or len(pose) != 3
                    or any(isinstance(v, bool) or not isinstance(v, (int, float))
                           or not math.isfinite(v) for v in pose)):
                raise ValueError('Every navigation pose must be three finite numbers')
        for zone in zones:
            if any(not zone.get(field, {}).get(mode) for field in ('narrations', 'english') for mode in MODES):
                raise ValueError('Every zone requires three bilingual narration levels')
            quiz = zone.get('quiz', {})
            if quiz.get('answer') not in [o.get('id') for o in quiz.get('options', [])]:
                raise ValueError('Quiz answer must identify an option')
            for item in zone.get('qa', []) + [quiz]:
                if not item.get('source_ids') or not set(item['source_ids']) <= sources:
                    raise ValueError('Every answer requires configured sources')
        self.state = 'IDLE'
        self.mode, self.language, self.auto_advance = 'general', 'zh', False
        self.zone_index = -1
        self.message = '待命：游客到访与异常按钮为仿真输入。'
        self.speech = self.quiz = self.qa = None
        self.theme = {'expression': 'idle', 'color': '#38bdf8', 'zone_id': None}
        self.visitor_count = 0
        self.fault = None
        self.events = []
        self.stats = {key: 0 for key in (
            'sessions', 'visitors', 'zones_completed', 'questions', 'answered_questions',
            'unknown_questions', 'quiz_attempts', 'quiz_correct', 'faults',
            'manual_takeovers', 'pauses', 'repeats', 'skipped_zones', 'completed')}
        self._speech_serial = self._navigation_serial = 0
        self._navigation_id = None
        self._resume_state = None
        self._qa_interrupted_narration = False
        self._visited = set()
        self._quiz_results = {}
        self._effects = []

    @property
    def zone(self):
        return self.content['zones'][self.zone_index] if self.zone_index >= 0 else None

    def snapshot(self):
        return deepcopy({
            'state': self.state, 'mode': self.mode, 'language': self.language,
            'auto_advance': self.auto_advance,
            'zone_id': self.zone['id'] if self.zone else None,
            'zone_index': self.zone_index, 'message': self.message,
            'speech': self.speech, 'quiz': self.quiz, 'qa': self.qa,
            'theme': self.theme, 'fault': self.fault, 'visitor_count': self.visitor_count,
            'navigation_id': self._navigation_id, 'events': self.events, 'stats': self.stats,
            'task_card': {'visited': [z['id'] for z in self.content['zones'] if z['id'] in self._visited],
                          'total': 5, 'score': sum(self._quiz_results.values()),
                          'answered': len(self._quiz_results)},
        })

    def _effect(self, effect_type, **fields):
        self._effects.append({'type': effect_type, **deepcopy(fields)})

    def _say(self, zh, en=None, kind='notice'):
        text = en if self.language == 'en' and en else zh
        self._speech_serial += 1
        self.speech = {'id': 'speech-' + str(self._speech_serial), 'text': text,
                       'language': self.language, 'kind': kind}
        self.message = text
        self._effect('speak', **self.speech)

    def _theme(self, expression, color):
        self.theme = {'expression': expression, 'color': color,
                      'zone_id': self.zone['id'] if self.zone else None}
        self._effect('theme', **self.theme)

    def _navigate(self, home=False):
        self.state = 'RETURNING' if home else 'NAVIGATING'
        self.speech = None
        self._navigation_serial += 1
        self._navigation_id = 'navigation-' + str(self._navigation_serial)
        self.message = '正在返回待命点。' if home else '请保持安全距离，前往' + self.zone['name'] + '。'
        self._effect('navigate', zone_id='home' if home else self.zone['id'],
                     pose=self.content['home'] if home else self.zone['pose'],
                     navigation_id=self._navigation_id)
        self._theme('guiding', '#38bdf8')

    def _present(self):
        self.state = 'PRESENTING'
        self._qa_interrupted_narration = False
        self._say(self.zone['narrations'][self.mode], self.zone['english'][self.mode], 'narration')
        self._theme('explaining', self.zone.get('color', '#f59e0b'))

    def _advance(self):
        self.speech = None
        self._qa_interrupted_narration = False
        if self.zone_index == 4:
            self._navigate(home=True)
        else:
            self.zone_index += 1
            self.quiz = self.qa = None
            self._navigate()

    def _suspend(self, target):
        if self.state not in ('PAUSED', 'FAULT', 'MANUAL'):
            self._resume_state = self.state
        self.state = target
        self.speech = None
        self._navigation_id = None
        self._effect('cancel_navigation')

    def _resume(self):
        target = self._resume_state or 'IDLE'
        self._resume_state = None
        self.state = target
        if target in ('NAVIGATING', 'RETURNING'):
            self._navigate(home=target == 'RETURNING')
        elif target == 'PRESENTING':
            self._present()
        elif target == 'WELCOMING':
            self.state = 'IDLE'
            self.message = '已恢复，请确认开始导览。'
        else:
            self.message = '已恢复，等待下一条指令。'

    def _question(self, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Question text must not be empty')
        self.stats['questions'] += 1
        match = None
        for zone in self.content['zones']:
            for qa in zone['qa']:
                names = [qa['question'], qa.get('question_en', '')] + qa.get('aliases', [])
                if _normal(text) in {_normal(name) for name in names if name}:
                    match = qa
                    break
            if match:
                break
        if self.state == 'PRESENTING' and self.speech and self.speech['kind'] == 'narration':
            self._qa_interrupted_narration = True
        if match:
            self.qa = dict(deepcopy(match), asked=text, answered=True)
            self.stats['answered_questions'] += 1
            self._say(match['answer'], match['answer_en'], 'qa')
        else:
            self.stats['unknown_questions'] += 1
            zh, en = FAULTS['unknown_question']
            self.qa = {'asked': text, 'answered': False, 'answer': zh, 'answer_en': en,
                       'source_ids': [], 'reason': 'outside_verified_sources'}
            self._say(zh, en, 'qa')
            self._effect('human_help', reason='unknown_question')

    def apply(self, event):
        if not isinstance(event, dict) or not isinstance(event.get('type'), str):
            raise ValueError('Event must contain a string type')
        kind = event['type']
        allowed = ('visitor', 'start', 'arrived', 'speech_done', 'pause', 'resume', 'repeat',
                   'skip', 'next', 'end', 'question', 'quiz_answer', 'fault', 'recover',
                   'manual', 'home_arrived')
        if kind not in allowed:
            raise ValueError('Unknown command: ' + kind)
        if kind == 'start':
            mode, language, auto = event.get('mode', 'general'), event.get('language', 'zh'), event.get('auto_advance', False)
            if mode not in MODES or language not in LANGUAGES or not isinstance(auto, bool):
                raise ValueError('Choose child/general/deep, zh/en and a boolean auto_advance')
        if kind == 'visitor':
            count = event.get('count')
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError('Visitor count must be a non-negative integer')
        before = self.state
        self._effects = []
        if kind == 'visitor':
            self.visitor_count = count
            if count and self.state in ('IDLE', 'WELCOMING', 'COMPLETE'):
                self.state = 'WELCOMING'
                self.stats['visitors'] += count
                self._say(('欢迎您！' if count == 1 else f'欢迎各位，当前为{count}人同行导览。')
                          + '这里是示范非遗展馆。请选择儿童、大众或深度讲解，确认后开始五区导览。',
                          f'Welcome, {count} visitor(s). This is a demonstration heritage hall. '
                          'Choose a narration level and confirm to start the five-zone tour.', 'welcome')
                self._theme('welcome', '#34d399')
        elif kind == 'start' and self.state in ('IDLE', 'WELCOMING', 'COMPLETE'):
            self.mode, self.language, self.auto_advance = mode, language, auto
            self.stats['sessions'] += 1
            self.zone_index = 0
            self.quiz = self.qa = self.fault = None
            self._visited.clear()
            self._quiz_results.clear()
            self._resume_state = None
            self._navigate()
        elif kind == 'arrived' and self.state == 'NAVIGATING':
            if (event.get('zone_id') == self.zone['id']
                    and event.get('navigation_id', self._navigation_id) == self._navigation_id):
                self._navigation_id = None
                self._present()
        elif kind == 'home_arrived' and self.state == 'RETURNING':
            if event.get('navigation_id', self._navigation_id) == self._navigation_id:
                self._navigation_id = None
                self.state = 'COMPLETE'
                self.stats['completed'] += 1
                self._say('导览已结束，已返回待命点。感谢参观！',
                          'The tour is complete. Back at the standby point. Thank you!', 'farewell')
                self._theme('goodbye', '#34d399')
        elif kind == 'speech_done' and self.speech and event.get('speech_id') == self.speech['id']:
            speech_kind = self.speech['kind']
            self.speech = None
            if self.state == 'WELCOMING':
                self.state = 'IDLE'
            elif self.state == 'PRESENTING' and speech_kind == 'narration':
                if self.zone['id'] not in self._visited:
                    self._visited.add(self.zone['id'])
                    self.stats['zones_completed'] += 1
                if self.quiz is None:
                    self.quiz = dict(deepcopy(self.zone['quiz']), answered=False, result=None)
                self.state = 'READY_NEXT' if self.quiz['answered'] else 'QUIZ'
                self.message = ('本区任务已完成，请继续。' if self.quiz['answered'] else
                                self.quiz['question_en'] if self.language == 'en' else self.quiz['question'])
                self._theme('question', '#a78bfa')
            elif self.state == 'PRESENTING' and speech_kind == 'qa' and self._qa_interrupted_narration:
                self._present()
        elif kind == 'pause' and self.state not in ('IDLE', 'COMPLETE', 'PAUSED', 'FAULT', 'MANUAL'):
            self.stats['pauses'] += 1
            self._suspend('PAUSED')
            self.message = '已暂停，请确认继续或结束返航。'
            self._theme('paused', '#fbbf24')
        elif kind == 'resume' and self.state == 'PAUSED':
            self._resume()
        elif kind == 'repeat' and self.zone and self.state in ('PRESENTING', 'READY_NEXT', 'QUIZ'):
            self.stats['repeats'] += 1
            self._present()
        elif kind == 'next' and self.state in ('READY_NEXT', 'QUIZ'):
            self._advance()
        elif kind == 'skip' and self.state in ('NAVIGATING', 'PRESENTING', 'READY_NEXT', 'QUIZ'):
            self.stats['skipped_zones'] += 1
            self._effect('cancel_navigation')
            self._advance()
        elif kind == 'end' and self.state not in ('FAULT', 'MANUAL', 'RETURNING', 'COMPLETE', 'IDLE'):
            self._effect('cancel_navigation')
            self._resume_state = None
            self._navigate(home=True)
        elif kind == 'question' and self.state in ('PRESENTING', 'READY_NEXT', 'QUIZ'):
            self._question(event.get('text'))
        elif kind == 'quiz_answer' and self.state == 'QUIZ' and not self.quiz['answered']:
            answer = str(event.get('answer', '')).strip().upper()
            if answer not in [option['id'] for option in self.quiz['options']]:
                raise ValueError('Answer must identify a displayed quiz option')
            correct = answer == self.quiz['answer']
            self.quiz['answered'] = True
            self.quiz['result'] = {'correct': correct, 'answer': answer,
                                   'correct_answer': self.quiz['answer'], 'reason': self.quiz['reason'],
                                   'reason_en': self.quiz['reason_en']}
            self.stats['quiz_attempts'] += 1
            self.stats['quiz_correct'] += int(correct)
            self._quiz_results[self.zone['id']] = correct
            self.speech = None
            self.state = 'READY_NEXT'
            self.message = ('回答正确。' if correct else '已记录回答，请查看解析。') + self.quiz['reason']
            self._theme('happy' if correct else 'encouraging', '#34d399' if correct else '#fbbf24')
            if self.auto_advance:
                self._advance()
        elif kind == 'fault':
            fault_kind = event.get('kind', 'unknown')
            if not isinstance(fault_kind, str):
                raise ValueError('Fault kind must be text')
            fault_kind = {'blocked': 'route_blocked'}.get(fault_kind, fault_kind)
            self.stats['faults'] += 1
            self._suspend('FAULT')
            self.fault = {'kind': fault_kind, 'simulated': bool(event.get('simulated', False))}
            zh, en = FAULTS.get(fault_kind, ('系统异常，已停止，请联系工作人员。',
                                            'System fault. Stopped; please ask staff.'))
            self._say(zh, en, 'fault')
            self._theme('alert', '#f87171')
            self._effect('human_help', reason=fault_kind)
        elif kind == 'manual' and self.state != 'COMPLETE':
            self.stats['manual_takeovers'] += 1
            self._suspend('MANUAL')
            self.message = '已请求人工接管，自动导览停止。工作人员确认恢复后方可继续。'
            self._theme('manual', '#f87171')
            self._effect('human_help', reason='manual_takeover')
        elif kind == 'recover' and self.state in ('FAULT', 'MANUAL'):
            self.fault = None
            self.speech = None
            self.state = 'PAUSED'
            self.message = '已确认恢复，仍保持停止；请按继续或结束返航。'
            self._theme('paused', '#fbbf24')
        record = {'sequence': len(self.events) + 1 if not self.events else self.events[-1]['sequence'] + 1,
                  'time': datetime.now(timezone.utc).isoformat(), 'event': kind,
                  'from_state': before, 'state': self.state, 'zone_id': self.zone['id'] if self.zone else None,
                  'message': self.message}
        self.events.append(record)
        self.events = self.events[-200:]
        self._effect('log', record=record)
        return deepcopy(self._effects)
