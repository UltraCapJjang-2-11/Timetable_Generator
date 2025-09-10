from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET
from django.db.models import Q
from django.contrib.auth.models import User

from ..models import ChatMessage


@require_GET
def get_chat_history(request):
    """과거 채팅 기록 조회 API

    Query params:
    - room: string (예: 'course_39429')
    - course_id: int (room 대신 제공 가능)
    - limit: int (기본 50, 최대 200)
    - before: ISO8601 datetime (해당 시각 이전 메시지 조회)
    - order: 'asc' | 'desc' (기본 'asc')
    """
    room = request.GET.get('room')
    course_id = request.GET.get('course_id')
    before = request.GET.get('before')
    order = request.GET.get('order', 'asc').lower()

    try:
        limit = int(request.GET.get('limit', 50))
    except Exception:
        limit = 50
    limit = max(1, min(limit, 200))

    if not room and course_id:
        try:
            cid = int(course_id)
            room = f"course_{cid}"
        except Exception:
            return JsonResponse({'error': 'invalid course_id'}, status=400)

    if not room:
        return JsonResponse({'error': 'room or course_id is required'}, status=400)

    qs = ChatMessage.objects.filter(room=room)

    if before:
        dt = parse_datetime(before)
        if dt is None:
            return JsonResponse({'error': 'invalid before datetime'}, status=400)
        qs = qs.filter(created_at__lt=dt)

    qs = qs.order_by('-created_at')[:limit]
    messages = list(qs.values('id', 'room', 'course_id', 'user_id', 'username', 'message', 'created_at'))
    messages.reverse()  # 최신순 슬라이스 후 시간 오름차순으로

    if order == 'desc':
        messages.reverse()

    # 직렬화: datetime ISO 포맷 변환 및 사용자 정보 추가
    for m in messages:
        m['created_at'] = m['created_at'].isoformat()
        # 사용자의 first_name, last_name 가져오기
        try:
            user = User.objects.get(id=m['user_id'])
            m['first_name'] = user.first_name
            m['last_name'] = user.last_name
        except User.DoesNotExist:
            m['first_name'] = ''
            m['last_name'] = ''

    return JsonResponse({'room': room, 'messages': messages}) 