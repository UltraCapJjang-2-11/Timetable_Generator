from django.db import models
from django.utils import timezone


class ChatMessage(models.Model):
    """강의별 채팅 메시지 저장 테이블.

    - room: 소켓 룸 키(예: 'course_39429' 또는 사용자 지정 name_*)
    - course_id: 과목 ID가 있을 경우 저장(없으면 NULL)
    - user_id: 보낸 사용자 ID(익명일 수 있음)
    - username: 보낸 사용자 이름(익명 허용)
    - message: 본문
    - created_at: 생성 시각(서버 기준)
    """
    room = models.CharField(max_length=100, db_index=True)
    course_id = models.IntegerField(null=True, blank=True, db_index=True)
    user_id = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, default='익명')
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.room} - {self.username}: {self.message[:30]}" 