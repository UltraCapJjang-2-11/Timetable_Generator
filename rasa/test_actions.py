# test_actions.py
import json
from unittest.mock import patch
from rasa_sdk.executor import CollectingDispatcher
from actions.actions import ActionExtractConstraints, ActionUtterGenerateTimetable

class DummyTracker:
    def __init__(self, text):
        # Rasa Tracker.latest_message.get('text') 모방
        self.latest_message = {'text': text}
        self._slots = {}

    def get_slot(self, name):
        return self._slots.get(name)

    def set_slot(self, name, value):
        self._slots[name] = value

def test_extract_constraints():
    print(">>> 제약조건 추출 액션 테스트")
    tracker = DummyTracker("전공 9학점, 교양 9학점 공강은 월요일로 해줘")
    dispatcher = CollectingDispatcher()
    # parse_constraints 엔드포인트 호출을 Mock
    with patch('actions.actions.requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            "major_credits": 9,
            "elective_credits": 9,
            "free_days": ["월"],
            "required_courses": ["알고리즘"]
        }
        action = ActionExtractConstraints()
        events = action.run(dispatcher, tracker, {})
        print("Events:", events)
        print("Dispatcher.messages:", dispatcher.messages)

def test_generate_timetable():
    print("\n>>> 시간표 생성 액션 테스트")
    tracker = DummyTracker("")
    # 슬롯을 미리 세팅
    tracker.set_slot("major_credits", 9)
    tracker.set_slot("elective_credits", 9)
    tracker.set_slot("free_days", ["월"])
    tracker.set_slot("required_courses", ["알고리즘"])
    dispatcher = CollectingDispatcher()
    # generate_timetable_stream SSE 호출을 Mock
    with patch('actions.actions.requests.get') as mock_get:
        class FakeResponse:
            def iter_lines(self):
                # SSE 데이터 바이트로 반환
                yield 'data: {"progress":"완료","message":"테스트 완료 메시지"}'.encode('utf-8')
        mock_get.return_value = FakeResponse()
        action = ActionUtterGenerateTimetable()
        events = action.run(dispatcher, tracker, {})
        print("Dispatcher.messages:", dispatcher.messages)

if __name__ == "__main__":
    test_extract_constraints()
    test_generate_timetable()
