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
    path: '/socket.io/',
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

    const timeEl = document.createElement('div');
    timeEl.className = 'chat-time';
    timeEl.textContent = getCurrentTime();
    bodyEl.appendChild(timeEl);

    const bubble = document.createElement('div');
    bubble.className = data && data.username ? 'chat-bubble other' : 'chat-bubble bot';
    bubble.textContent = `${data.username || '익명'}: ${data.message || ''}`;
    bodyEl.appendChild(bubble);

    bodyEl.scrollTop = bodyEl.scrollHeight;
  });

  function getCurrentTime() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    const hour12 = hours % 12 === 0 ? 12 : hours % 12;
    return `오늘 ${period} ${hour12}:${minutes}`;
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

    function doSend() {
      const text = (input.value || '').trim();
      if (!text) return;

      const t = document.createElement('div');
      t.className = 'chat-time';
      t.textContent = getCurrentTime();
      body.appendChild(t);

      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble user';
      bubble.textContent = text;
      body.appendChild(bubble);

      body.scrollTop = body.scrollHeight;
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