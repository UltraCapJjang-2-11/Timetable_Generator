"""
자연어 기반 시간표 생성 뷰 (HTTP 기반)
timetable 페이지의 chatbot에서 사용
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from home.services.nl_timetable_service import NaturalLanguageTimetableService
from home.services.timetable_generation_service import TimetableGenerationService


@csrf_exempt
@require_http_methods(["POST"])
def nl_timetable_chat(request):
    """
    자연어 기반 시간표 생성 채팅 API

    Request Body:
        {
            "message": "월화는 공강이고 전공 12학점 원해",
            "session_id": "user_1234567890"
        }

    Response:
        {
            "message": "AI 응답 메시지",
            "stage": "gathering" | "confirming" | "generating",
            "constraints": {...},  // stage가 generating일 때만
            "timetables": [...],   // stage가 generating일 때만 (생성 완료)
            "summary": "추출된 조건 요약"  // 옵션
        }
    """
    try:
        # 요청 파싱
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')

        if not user_message:
            return JsonResponse({
                'error': '메시지를 입력해주세요.'
            }, status=400)

        # 사용자 정보
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({
                'error': '로그인이 필요합니다.'
            }, status=401)

        # 자연어 처리 서비스 호출
        nl_service = NaturalLanguageTimetableService()
        constraints, ai_response, stage = nl_service.parse_natural_language(
            user.id, session_id, user_message
        )

        response_data = {
            'message': ai_response,
            'stage': stage
        }

        # 제약조건이 추출된 경우
        if constraints:
            response_data['constraints'] = constraints
            response_data['summary'] = nl_service.generate_summary(constraints)

        # 시간표 생성 단계인 경우
        if stage == 'generating' and constraints:
            try:
                # TimetableRequest로 변환
                timetable_request = nl_service.constraints_to_timetable_request(
                    constraints, user
                )

                # 시간표 생성
                generation_service = TimetableGenerationService()
                result = generation_service.generate(user, timetable_request)

                # 생성 결과 추가
                if result.get('error'):
                    response_data['error'] = result['error']
                    response_data['message'] = f"😔 {result['error']}"
                else:
                    response_data['timetables'] = result.get('timetables', [])
                    timetable_count = len(response_data['timetables'])

                    if timetable_count > 0:
                        response_data['message'] = f"✅ {timetable_count}개의 시간표를 생성했습니다!"
                    else:
                        response_data['message'] = "😔 조건을 만족하는 시간표를 생성하지 못했습니다."

                # 세션 초기화
                nl_service.clear_session(user.id, session_id)

            except Exception as e:
                print(f"Timetable generation error: {str(e)}")
                import traceback
                traceback.print_exc()

                response_data['error'] = str(e)
                response_data['message'] = f"시간표 생성 중 오류가 발생했습니다: {str(e)}"

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': '잘못된 JSON 형식입니다.'
        }, status=400)
    except Exception as e:
        print(f"NL Timetable Chat Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'error': f'서버 오류가 발생했습니다: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def nl_reset_session(request):
    """세션 초기화 API"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id', 'default')

        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)

        nl_service = NaturalLanguageTimetableService()
        nl_service.clear_session(user.id, session_id)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({
            'error': f'세션 초기화 실패: {str(e)}'
        }, status=500)
