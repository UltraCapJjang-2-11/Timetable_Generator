// Wrap everything in DOMContentLoaded to ensure DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  console.log('manage_chat.js: DOM loaded, initializing chat system...');
  
  // Ensure dependencies
  if (typeof io === 'undefined') {
    console.error('Socket.IO client not loaded');
    return;
  }

  const timetableSelect = document.getElementById('saved-timetable-select');
  const lectureListEl = document.getElementById('lecture-list');
  const chatroomView = document.querySelector('.chatroom-view');
  const chatPlaceholder = document.getElementById('chat-placeholder');

  if (!timetableSelect) {
    console.error('Timetable select element not found in DOM');
    return;
  }
  if (!lectureListEl) {
    console.error('Lecture list element not found in DOM');
    return;
  }

  console.log('All required DOM elements found');

  // Maintain open rooms and UI panels
  const openRooms = new Map(); // roomKey -> { panelEl, headerCountEl, course }
  let currentRoomKey = null;   // 현재 표시 중인 단일 채팅방

  // Connect socket - 수정된 연결 설정
  console.log('Attempting to connect to Socket.IO server...');
  const socket = io('/', {
    path: '/socket.io',
    transports: ['polling', 'websocket'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    auth: {
      user_id: (window.currentUser && Number(window.currentUser.user_id)) || 0,
      username: (window.currentUser && window.currentUser.username) || '익명'
    }
  });

  socket.on('connect', () => {
    console.log('Socket.IO connected successfully!');
    socket.emit('identify', {
      user_id: (window.currentUser && Number(window.currentUser.user_id)) || 0,
      username: (window.currentUser && window.currentUser.username) || '익명'
    });
  });

  socket.on('connect_error', (error) => {
    console.error('Socket.IO connection error:', error.message);
    console.error('Error type:', error.type);
  });

  socket.on('disconnect', (reason) => {
    console.log('Socket.IO disconnected:', reason);
  });

  socket.on('user_count', (data) => {
    const room = data && data.room;
    const count = (data && data.count) || 0;
    if (!room) return;
    const entry = openRooms.get(room);
    if (entry && entry.headerCountEl) {
      entry.headerCountEl.textContent = `${count}명 참여 중`;
    }
  });

  socket.on('chat_message', (data) => {
    const room = data && (data.room || (data.course_id != null ? `course_${data.course_id}` : null));
    if (!room) return;
    const entry = openRooms.get(room);
    if (!entry) return;
    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const isSelf = data && (data.user_id === (window.currentUser && Number(window.currentUser.user_id)));
    appendMessage(openRooms.get(room), !!isSelf, data && data.user_id, data && data.username, data && data.message, new Date(), data && data.first_name, data && data.last_name);
  });

  function getCurrentTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    const hour12 = hours % 12 === 0 ? 12 : hours % 12;
    return `오늘 ${period} ${hour12}:${minutes}`;
  }

  // Kakao-style formatters and render helpers
  function formatKakaoTime(dt) {
    const hours = dt.getHours();
    const minutes = String(dt.getMinutes()).padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    const hour12 = hours % 12 === 0 ? 12 : hours % 12;
    return `${period} ${hour12}:${minutes}`;
  }

  function formatKakaoDate(dt) {
    const y = dt.getFullYear();
    const m = dt.getMonth() + 1;
    const d = dt.getDate();
    return `${y}. ${m}. ${d}.`;
  }

  function dateKey(dt) {
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
  }

  function ensureDateSeparator(entry, dt) {
    if (!entry || !entry.panelEl) return;
    const key = dateKey(dt);
    if (entry.lastDateKey !== key) {
      const sep = document.createElement('div');
      sep.className = 'chat-date-sep';
      sep.textContent = formatKakaoDate(dt);
      const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
      if (bodyEl) bodyEl.appendChild(sep);
      entry.lastDateKey = key;
      entry.lastSenderKey = null; // 날짜가 바뀌면 이름 라벨을 다시 표시
    }
  }

  function appendMessage(entry, isSelf, userId, username, text, dt, firstName, lastName) {
    if (!entry || !entry.panelEl) return;
    const bodyEl = entry.panelEl.querySelector('.lecture-chat-body');
    if (!bodyEl) return;

    const when = dt instanceof Date ? dt : new Date();
    ensureDateSeparator(entry, when);

    // 타인 메시지에서 발신자 라벨 표시(연속 동일 발신자면 생략)
    const senderKey = isSelf ? `self:${(window.currentUser && Number(window.currentUser.user_id)) || 0}` : `user:${userId || username || '익명'}`;
    
    // 사용자 전체 이름 구성 (first_name + last_name 우선, 없으면 username)
    let displayName;
    if (!isSelf) {
      if (firstName || lastName) {
        displayName = `${lastName || ''}${firstName || ''}`.trim() || username || '익명';
      } else {
        displayName = username || '익명';
      }
      
      if (entry.lastSenderKey !== senderKey) {
        const nameEl = document.createElement('div');
        nameEl.className = 'chat-sender';
        nameEl.textContent = displayName;
        bodyEl.appendChild(nameEl);
      }
    }
    entry.lastSenderKey = senderKey;

    const row = document.createElement('div');
    row.className = `chat-row ${isSelf ? 'self' : 'other'}`;

    // 상대방 메시지일 경우 프로필 아바타 추가
    if (!isSelf) {
      const avatar = document.createElement('div');
      avatar.className = 'chat-avatar';
      // 이름의 첫 글자를 아바타로 표시
      const initial = displayName ? displayName.charAt(0).toUpperCase() : '?';
      avatar.textContent = initial;
      row.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = isSelf ? 'chat-bubble user' : 'chat-bubble other';
    bubble.textContent = text || '';

    const timeEl = document.createElement('span');
    timeEl.className = 'msg-time';
    timeEl.textContent = formatKakaoTime(when);

    row.appendChild(bubble);
    row.appendChild(timeEl);

    bodyEl.appendChild(row);
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  function hashStr(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = (h << 5) - h + str.charCodeAt(i);
      h |= 0;
    }
    return Math.abs(h).toString(36);
  }

  function roomKeyForCourse(course) {
    const hasId = course && course.course_id != null && String(course.course_id) !== '';
    if (hasId) return `course_${course.course_id}`;
    return `name_${hashStr(String(course.course_name || 'unknown'))}`;
  }

  function buildLectureList(timetable) {
    console.log('Building lecture list for timetable:', timetable);
    lectureListEl.innerHTML = '';
    if (!timetable || !Array.isArray(timetable.courses)) {
      console.warn('No timetable or courses found');
      return;
    }

    console.log(`Found ${timetable.courses.length} courses`);
    timetable.courses
      .filter(c => !!c)
      .forEach(course => {
        const li = document.createElement('li');
        li.textContent = course.course_name || '(이름 없음)';
        li.dataset.courseId = String(course.course_id || '');
        li.addEventListener('click', () => {
          console.log('Course clicked:', course.course_name);
          const key = roomKeyForCourse(course);
          if (currentRoomKey && currentRoomKey !== key) {
            closeRoom(currentRoomKey);
          }
          let entry = openRooms.get(key);
          if (!entry) entry = ensureChatPanel(course);
          currentRoomKey = key;
          if (entry) {
            entry.panelEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        });
        lectureListEl.appendChild(li);
      });
  }

  function ensureChatPanel(course) {
    console.log('Ensuring chat panel for course:', course.course_name);
    const roomKey = roomKeyForCourse(course);
    if (openRooms.has(roomKey)) {
      console.log('Chat panel already exists for room:', roomKey);
      return openRooms.get(roomKey);
    }

    console.log('Creating new chat panel for room:', roomKey);
    if (chatPlaceholder) chatPlaceholder.style.display = 'none';

    const panel = document.createElement('div');
    panel.className = 'lecture-chat-widget';
    panel.id = `chat-panel-${roomKey}`;

    const header = document.createElement('div');
    header.className = 'chatroom-header';

    const title = document.createElement('h3');
    title.className = 'chatroom-title';
    title.textContent = `${course.course_name} 채팅방`;

    const countEl = document.createElement('div');
    countEl.className = 'chatroom-user-count';
    countEl.textContent = '0명 참여 중';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-sm btn-outline-secondary';
    closeBtn.textContent = '닫기';
    closeBtn.addEventListener('click', () => closeRoom(roomKey));

    header.appendChild(title);
    header.appendChild(countEl);
    header.appendChild(closeBtn);

    const body = document.createElement('div');
    body.className = 'lecture-chat-body';

    const inputWrap = document.createElement('div');
    inputWrap.className = 'lecture-chat-input';

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = '메시지를 입력하세요';

    const sendBtn = document.createElement('button');
    sendBtn.textContent = '전송';

    inputWrap.appendChild(input);
    inputWrap.appendChild(sendBtn);

    panel.appendChild(header);
    panel.appendChild(body);
    panel.appendChild(inputWrap);

    // 다른 모든 패널 숨기고(제거) 하나만 보이도록 유지
    for (const key of Array.from(openRooms.keys())) {
      closeRoom(key);
    }

    chatroomView.appendChild(panel);

    const entry = { panelEl: panel, headerCountEl: countEl, course };
    openRooms.set(roomKey, entry);

    // 과거 메시지 로딩
    (async () => {
      try {
        const params = new URLSearchParams();
        if (course && course.course_id != null && String(course.course_id) !== '') {
          params.set('course_id', String(course.course_id));
        } else {
          params.set('room', roomKey);
        }
        params.set('limit', '50');
        const res = await fetch(`/api/chat/history/?${params.toString()}`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
        });
        if (!res.ok) throw new Error(`History API HTTP ${res.status}`);
        const data = await res.json();
        const msgs = Array.isArray(data.messages) ? data.messages : [];
        for (const m of msgs) {
          const dt = m.created_at ? new Date(m.created_at) : new Date();
          const isSelf = (m.user_id === (window.currentUser && Number(window.currentUser.user_id)));
          appendMessage(entry, !!isSelf, m.user_id, m.username, m.message, dt, m.first_name, m.last_name);
        }
      } catch (e) {
        console.error('Failed to load chat history:', e);
      }
    })();

    function doSend() {
      const text = (input.value || '').trim();
      if (!text) return;

      appendMessage(entry, true, (window.currentUser && Number(window.currentUser.user_id)) || 0, (window.currentUser && window.currentUser.username) || '익명', text, new Date(), window.currentUser && window.currentUser.first_name, window.currentUser && window.currentUser.last_name);
      input.value = '';

      if (course && course.course_id != null && String(course.course_id) !== '') {
        socket.emit('chat_message', {
          course_id: course.course_id,
          message: text
        });
      } else {
        socket.emit('chat_message', {
          room: roomKey,
          message: text
        });
      }
    }

    sendBtn.addEventListener('click', doSend);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') doSend();
    });

    // Join room
    if (course && course.course_id != null && String(course.course_id) !== '') {
      socket.emit('join_room', { course_id: course.course_id });
    } else {
      socket.emit('join_room', { room: roomKey });
    }

    currentRoomKey = roomKey;
    return entry;
  }

  function closeRoom(roomKey) {
    const entry = openRooms.get(roomKey);
    if (!entry) return;
    
    // leave room
    socket.emit('leave_room', { room: roomKey });
    
    entry.panelEl.remove();
    openRooms.delete(roomKey);

    if (currentRoomKey === roomKey) {
      currentRoomKey = null;
    }

    if (openRooms.size === 0 && chatPlaceholder) {
      chatPlaceholder.style.display = '';
    }
  }

  function openAllCourseChats(timetable) {
    console.log('Opening all course chats for timetable:', timetable);
    // Close existing rooms first
    for (const key of Array.from(openRooms.keys())) {
      closeRoom(key);
    }
    // Build list only; 하나씩 클릭할 때 열리도록 변경
    buildLectureList(timetable);
    // 자동으로 모두 열지 않음
  }

  function findTimetableById(id) {
    id = Number(id);
    const list = Array.isArray(window.timetablesData) ? window.timetablesData : [];
    const found = list.find(t => Number(t.id) === id) || null;
    console.log(`Finding timetable by ID ${id}:`, found ? 'Found' : 'Not found');
    return found;
  }

  if (timetableSelect) {
    console.log('Timetable select element found, adding change listener');
    timetableSelect.addEventListener('change', (e) => {
      const id = e.target.value;
      console.log('Timetable selected, ID:', id);
      const tt = id ? findTimetableById(id) : null;
      if (tt) {
        console.log('Timetable data found:', tt.title);
        window.currentTimetable = tt;
        window.currentTimetableId = tt.id;
        openAllCourseChats(tt);
        // 좌측 카드 active 및 제목 반영: .timetable-item 기준으로 개선
        const side = document.querySelector('.timetable-side');
        const titleEl = document.getElementById('selected-timetable-name');
        if (side) {
          side.querySelectorAll('.timetable-card').forEach(el => el.classList.remove('active'));
          const item = side.querySelector(`.timetable-item[data-timetable-id="${id}"]`);
          const card = item ? item.querySelector('.timetable-card') : null;
          if (card) card.classList.add('active');
        }
        if (titleEl) titleEl.textContent = tt.title;
      } else {
        console.log('No timetable selected or found, clearing chats');
        for (const key of Array.from(openRooms.keys())) {
          closeRoom(key);
        }
        lectureListEl.innerHTML = '';
        if (chatPlaceholder) chatPlaceholder.style.display = '';
      }
    });
  } else {
    console.error('Timetable select element not found!');
  }

  // If only one timetable exists, preselect it
  if (timetableSelect && timetableSelect.options.length === 2) {
    timetableSelect.selectedIndex = 1;
    const event = new Event('change');
    timetableSelect.dispatchEvent(event);
  }
}); 