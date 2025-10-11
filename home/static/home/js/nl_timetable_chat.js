/**
 * 자연어 기반 시간표 생성 채팅 모듈
 * Socket.IO를 통한 실시간 AI 대화 및 시간표 생성
 */

(function() {
  'use strict';

  // 전역 변수
  let nlSocket = null;
  let currentSessionId = null;
  let isProcessing = false;

  /**
   * 초기화
   */
  function initNLTimetableChat(socket) {
    nlSocket = socket;
    currentSessionId = generateSessionId();

    console.log('NL Timetable Chat initialized with session:', currentSessionId);

    // Socket.IO 이벤트 리스너 등록
    setupSocketListeners();
  }

  /**
   * 세션 ID 생성
   */
  function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Socket.IO 이벤트 리스너 설정
   */
  function setupSocketListeners() {
    // AI 응답 수신
    nlSocket.on('nl_timetable_response', handleAIResponse);

    // 시간표 생성 시작 알림
    nlSocket.on('nl_timetable_generating', handleGeneratingStatus);

    // 시간표 생성 결과 수신
    nlSocket.on('nl_timetable_result', handleTimetableResult);
  }

  /**
   * 자연어 시간표 요청 전송
   */
  function sendNLTimetableRequest(message, chatEntry) {
    if (!message || !message.trim()) return;
    if (isProcessing) {
      appendAIMessage(chatEntry, '현재 요청을 처리 중입니다. 잠시만 기다려주세요.', 'warning');
      return;
    }

    isProcessing = true;

    // 사용자 메시지 표시
    appendUserMessage(chatEntry, message);

    // Socket.IO로 요청 전송
    nlSocket.emit('nl_timetable_request', {
      message: message.trim(),
      session_id: currentSessionId
    });

    // 로딩 표시
    appendAIMessage(chatEntry, '생각 중...', 'loading');
  }

  /**
   * AI 응답 처리
   */
  function handleAIResponse(data) {
    isProcessing = false;

    // 로딩 메시지 제거
    removeLoadingMessages();

    const chatEntry = getAIChatEntry();
    if (!chatEntry) return;

    if (data.error) {
      appendAIMessage(chatEntry, `❌ ${data.error}`, 'error');
      return;
    }

    const message = data.message || '';
    const stage = data.stage || 'gathering';
    const constraints = data.constraints;

    // AI 메시지 표시
    appendAIMessage(chatEntry, message, 'normal');

    // 제약조건이 있으면 요약 표시
    if (constraints && Object.keys(constraints).length > 0) {
      const summary = generateConstraintsSummary(constraints);
      if (summary) {
        appendConstraintsSummary(chatEntry, summary);
      }
    }

    // 스크롤 하단으로
    scrollToBottom(chatEntry);
  }

  /**
   * 시간표 생성 상태 처리
   */
  function handleGeneratingStatus(data) {
    const chatEntry = getAIChatEntry();
    if (!chatEntry) return;

    const message = data.message || '시간표를 생성하고 있습니다...';
    const summary = data.summary || '';

    // 생성 중 메시지 표시
    appendAIMessage(chatEntry, `🔄 ${message}`, 'generating');

    if (summary) {
      appendAIMessage(chatEntry, `📋 ${summary}`, 'info');
    }

    scrollToBottom(chatEntry);
  }

  /**
   * 시간표 생성 결과 처리
   */
  function handleTimetableResult(data) {
    isProcessing = false;
    removeLoadingMessages();

    const chatEntry = getAIChatEntry();
    if (!chatEntry) return;

    if (data.error) {
      appendAIMessage(chatEntry, `❌ ${data.error}`, 'error');
      return;
    }

    // 성공 메시지
    const timetableCount = data.timetables ? data.timetables.length : 0;
    if (timetableCount === 0) {
      appendAIMessage(chatEntry, '😔 조건을 만족하는 시간표를 생성하지 못했습니다. 조건을 조정해보시겠어요?', 'warning');
    } else {
      appendAIMessage(chatEntry, `✅ ${timetableCount}개의 시간표를 생성했습니다!`, 'success');

      // 시간표 카드 표시
      displayTimetableCards(chatEntry, data.timetables);
    }

    scrollToBottom(chatEntry);
  }

  /**
   * 사용자 메시지 추가
   */
  function appendUserMessage(entry, text) {
    if (!entry || !entry.panelEl) return;

    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const row = document.createElement('div');
    row.className = 'chat-row self nl-chat-row';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble user';
    bubble.textContent = text;

    const timeEl = document.createElement('span');
    timeEl.className = 'msg-time';
    timeEl.textContent = formatTime(new Date());

    row.appendChild(bubble);
    row.appendChild(timeEl);
    bodyEl.appendChild(row);

    scrollToBottom(entry);
  }

  /**
   * AI 메시지 추가
   */
  function appendAIMessage(entry, text, type = 'normal') {
    if (!entry || !entry.panelEl) return;

    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const row = document.createElement('div');
    row.className = 'chat-row other nl-chat-row';
    row.dataset.messageType = type;

    // AI 아바타
    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar ai-avatar';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble other ai-bubble ai-bubble-${type}`;
    bubble.textContent = text;

    const timeEl = document.createElement('span');
    timeEl.className = 'msg-time';
    timeEl.textContent = formatTime(new Date());

    row.appendChild(avatar);
    row.appendChild(bubble);
    row.appendChild(timeEl);
    bodyEl.appendChild(row);

    scrollToBottom(entry);
  }

  /**
   * 제약조건 요약 표시
   */
  function appendConstraintsSummary(entry, summary) {
    if (!entry || !entry.panelEl) return;

    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const summaryEl = document.createElement('div');
    summaryEl.className = 'constraints-summary';
    summaryEl.innerHTML = `
      <div class="summary-title">📌 추출된 조건</div>
      <div class="summary-content">${summary}</div>
    `;

    bodyEl.appendChild(summaryEl);
    scrollToBottom(entry);
  }

  /**
   * 시간표 카드 표시
   */
  function displayTimetableCards(entry, timetables) {
    if (!entry || !entry.panelEl || !timetables) return;

    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const container = document.createElement('div');
    container.className = 'timetable-cards-container';

    timetables.forEach((timetable, index) => {
      const card = createTimetableCard(timetable, index);
      container.appendChild(card);
    });

    bodyEl.appendChild(container);
    scrollToBottom(entry);
  }

  /**
   * 시간표 카드 생성
   */
  function createTimetableCard(timetable, index) {
    const card = document.createElement('div');
    card.className = 'timetable-card nl-timetable-card';

    const header = document.createElement('div');
    header.className = 'timetable-card-header';
    header.innerHTML = `
      <span class="timetable-number">시간표 ${index + 1}</span>
      <span class="timetable-stars">${timetable.recommendation_level || '★★★'}</span>
    `;

    const body = document.createElement('div');
    body.className = 'timetable-card-body';

    // 과목 목록
    const coursesList = document.createElement('div');
    coursesList.className = 'courses-list';

    if (timetable.courses && timetable.courses.length > 0) {
      timetable.courses.forEach(course => {
        const courseItem = document.createElement('div');
        courseItem.className = 'course-item';
        courseItem.textContent = `${course.course_name} (${course.credit}학점)`;
        coursesList.appendChild(courseItem);
      });
    }

    // 총 학점
    const totalCredits = timetable.courses ?
      timetable.courses.reduce((sum, c) => sum + (c.credit || 0), 0) : 0;

    const creditsInfo = document.createElement('div');
    creditsInfo.className = 'credits-info';
    creditsInfo.textContent = `총 ${totalCredits}학점`;

    body.appendChild(coursesList);
    body.appendChild(creditsInfo);

    // 액션 버튼
    const actions = document.createElement('div');
    actions.className = 'timetable-card-actions';

    const viewBtn = document.createElement('button');
    viewBtn.className = 'btn btn-sm btn-primary';
    viewBtn.textContent = '상세보기';
    viewBtn.onclick = () => viewTimetableDetail(timetable);

    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-sm btn-success';
    saveBtn.textContent = '저장하기';
    saveBtn.onclick = () => saveTimetable(timetable);

    actions.appendChild(viewBtn);
    actions.appendChild(saveBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);

    return card;
  }

  /**
   * 시간표 상세보기
   */
  function viewTimetableDetail(timetable) {
    // 기존 시간표 표시 로직 재사용
    if (window.showTimetableInModal) {
      window.showTimetableInModal(timetable);
    } else {
      console.log('Timetable detail:', timetable);
      alert('시간표를 표시할 수 없습니다.');
    }
  }

  /**
   * 시간표 저장
   */
  async function saveTimetable(timetable) {
    try {
      const response = await fetch('/save_timetable/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          title: `AI 생성 시간표 ${new Date().toLocaleDateString()}`,
          courses: timetable.courses
        })
      });

      const result = await response.json();

      if (result.success) {
        alert('✅ 시간표가 저장되었습니다!');
        // 페이지 새로고침 또는 목록 업데이트
        if (window.location.pathname === '/manage/') {
          location.reload();
        }
      } else {
        alert('❌ 저장 실패: ' + (result.error || '알 수 없는 오류'));
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('❌ 저장 중 오류가 발생했습니다.');
    }
  }

  /**
   * 제약조건 요약 생성
   */
  function generateConstraintsSummary(constraints) {
    const parts = [];

    if (constraints.target_total) {
      parts.push(`총 ${constraints.target_total}학점`);
    }
    if (constraints.target_major) {
      parts.push(`전공 ${constraints.target_major}학점`);
    }
    if (constraints.target_elective) {
      parts.push(`교양 ${constraints.target_elective}학점`);
    }
    if (constraints.free_days && constraints.free_days.length > 0) {
      parts.push(`${constraints.free_days.join(', ')} 공강`);
    }
    if (constraints.prefer_morning) {
      parts.push('오전 선호');
    }
    if (constraints.prefer_afternoon) {
      parts.push('오후 선호');
    }
    if (constraints.prefer_compact) {
      parts.push('밀집 시간표');
    }

    return parts.join(' • ');
  }

  /**
   * 유틸리티 함수들
   */
  function getAIChatEntry() {
    // AI 채팅방의 entry를 가져오는 로직
    // manage_chat.js의 openRooms에서 'ai_timetable' 룸을 찾음
    if (window.nlChatEntry) {
      return window.nlChatEntry;
    }
    return null;
  }

  function removeLoadingMessages() {
    const chatBody = document.querySelector('.lecture-chat-body');
    if (!chatBody) return;

    const loadingMsgs = chatBody.querySelectorAll('[data-message-type="loading"]');
    loadingMsgs.forEach(msg => msg.remove());
  }

  function scrollToBottom(entry) {
    if (!entry || !entry.panelEl) return;
    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (bodyEl) {
      bodyEl.scrollTop = bodyEl.scrollHeight;
    }
  }

  function formatTime(date) {
    const hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    const hour12 = hours % 12 === 0 ? 12 : hours % 12;
    return `${period} ${hour12}:${minutes}`;
  }

  function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  // 전역으로 노출
  window.NLTimetableChat = {
    init: initNLTimetableChat,
    sendRequest: sendNLTimetableRequest,
    resetSession: function() {
      currentSessionId = generateSessionId();
      isProcessing = false;
    }
  };

})();
