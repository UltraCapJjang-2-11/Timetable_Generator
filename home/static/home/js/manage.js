// 시간표 데이터를 저장할 전역 변수
let timetablesData = {};
let currentTimetableId = null;
const visitedLectures = {};
const connectedUsers = {};

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", () => {
    // JSON 데이터 파싱
    const timetablesJson = document.getElementById('timetables-json');
    if (timetablesJson) {
        try {
            const data = JSON.parse(timetablesJson.textContent || '[]');
            data.forEach(timetable => {
                timetablesData[timetable.id] = timetable;
            });
        } catch (e) {
            console.error('시간표 데이터 파싱 오류:', e);
        }
    }

    // 시간표 선택 드롭다운 이벤트
    const selectElement = document.getElementById('saved-timetable-select');
    if (selectElement) {
        selectElement.addEventListener('change', function(e) {
            const timetableId = e.target.value;
            if (timetableId) {
                showTimetableById(parseInt(timetableId));
            } else {
                clearLectureList();
            }
        });
    }

    // 초기 채팅방 상태
    initEmptyChat();
});

// 시간표 선택 시 처리
function showTimetableById(timetableId) {
    console.log("Selected timetable:", timetableId);
    currentTimetableId = timetableId;
    
    // 시간표 데이터 가져오기
    const timetable = timetablesData[timetableId];
    if (!timetable) {
        console.error('시간표를 찾을 수 없습니다:', timetableId);
        return;
    }
    
    // 드롭다운 업데이트
    const selectElement = document.getElementById('saved-timetable-select');
    if (selectElement) {
        selectElement.value = timetableId;
    }
    
    // 강의 목록 업데이트
    updateLectureList(timetable.courses || []);
    
    // 채팅 초기화
    initEmptyChat();
}

// 강의 목록 업데이트
function updateLectureList(courses) {
    const lectureList = document.getElementById('lecture-list');
    if (!lectureList) return;
    
    lectureList.innerHTML = '';
    
    if (courses.length === 0) {
        lectureList.innerHTML = '<li style="color: #999; text-align: center;">강의가 없습니다</li>';
        return;
    }
    
    courses.forEach(course => {
        const li = document.createElement('li');
        li.textContent = course.course_name;
        li.onclick = () => selectChat(course.course_name, course.course_id);
        lectureList.appendChild(li);
        
        // 연결된 사용자 수 임시 설정
        connectedUsers[course.course_name] = Math.floor(Math.random() * 10) + 1;
    });
}

// 강의 목록 초기화
function clearLectureList() {
    const lectureList = document.getElementById('lecture-list');
    if (lectureList) {
        lectureList.innerHTML = '<li style="color: #999; text-align: center;">시간표를 선택하세요</li>';
    }
}

// 채팅방 선택
function selectChat(lectureName, courseId) {
    const placeholder = document.getElementById("chat-placeholder");
    const userCount = connectedUsers[lectureName] || 1;

    placeholder.innerHTML = `
        <div class="chatroom-header">
            <h3 class="chatroom-title">${lectureName} 채팅방</h3>
            <div class="chatroom-user-count">${userCount}명 참여 중</div>
        </div>
        <div class="lecture-chat-widget">
            <div class="lecture-chat-body"></div>
            <div class="lecture-chat-input">
                <input type="text" placeholder="메시지를 입력하세요">
                <button>전송</button>
            </div>
        </div>
    `;

    const input = document.querySelector(".lecture-chat-input input");
    const sendBtn = document.querySelector(".lecture-chat-input button");
    const chatBody = document.querySelector(".lecture-chat-body");

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keypress", function (e) {
        if (e.key === "Enter") sendMessage();
    });

    if (!visitedLectures[lectureName]) {
        visitedLectures[lectureName] = true;
        setTimeout(() => {
            addBotMessage("안녕하세요! 이 강의에 대한 궁금한 점이 있다면 편하게 물어보세요 :)");
        }, 500);
    }

    function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        const time = document.createElement("div");
        time.className = "chat-time";
        time.textContent = getCurrentTime();
        chatBody.appendChild(time);

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble user";
        bubble.textContent = text;
        chatBody.appendChild(bubble);

        input.value = "";
        chatBody.scrollTop = chatBody.scrollHeight;

        setTimeout(() => {
            addBotMessage(getBotReply(text));
        }, 800);
    }

    function addBotMessage(msg) {
        const time = document.createElement("div");
        time.className = "chat-time";
        time.textContent = getCurrentTime();
        chatBody.appendChild(time);

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble bot";
        bubble.textContent = msg;
        chatBody.appendChild(bubble);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function getCurrentTime() {
        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const period = hours < 12 ? '오전' : '오후';
        const hour12 = hours % 12 === 0 ? 12 : hours % 12;
        return `오늘 ${period} ${hour12}:${minutes}`;
    }

    function getBotReply(userText) {
        const lower = userText.toLowerCase();
        if (lower.includes("시간표")) {
            return "시간표를 만들고 싶으시면 '시간표 생성' 버튼을 눌러보세요!";
        } else if (lower.includes("추천") || lower.includes("과목")) {
            return "관심 분야나 원하는 공강 요일이 있다면 말씀해주세요 :)";
        } else if (lower.includes("안녕") || lower.includes("hello")) {
            return "안녕하세요! 무엇을 도와드릴까요?";
        } else {
            return "죄송해요, 아직 그건 잘 모르겠어요.\n'시간표', '추천', '안녕' 같은 키워드를 써보실래요?";
        }
    }
}

// 빈 채팅방 초기화
function initEmptyChat() {
    const placeholder = document.getElementById("chat-placeholder");
    if (!placeholder) return;
    
    placeholder.innerHTML = `
        <div class="chatroom-header">
            <h3 class="chatroom-title">채팅방을 선택해주세요</h3>
            <div class="chatroom-user-count">0명 참여 중</div>
        </div>
        <div class="lecture-chat-widget">
            <div class="lecture-chat-body">
                <p style="color:#999; text-align:center; margin-top:20px;">시간표를 선택한 후 강의를 클릭하세요</p>
            </div>
            <div class="lecture-chat-input">
                <input type="text" placeholder="채팅방을 선택하세요" disabled>
                <button disabled>전송</button>
            </div>
        </div>
    `;
}

// 시간표 편집
function editTimetable() {
    if (currentTimetableId) {
        window.location.href = `/timetable/?edit=${currentTimetableId}`;
    }
}

// 시간표 삭제
function deleteTimetable() {
    if (!currentTimetableId) return;
    
    if (confirm('정말로 이 시간표를 삭제하시겠습니까?')) {
        fetch(`/timetable/delete/${currentTimetableId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('시간표가 삭제되었습니다.');
                location.reload();
            } else {
                alert('삭제 중 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('삭제 중 오류가 발생했습니다.');
        });
    }
}

// 시간표 숨기기
function hideTimetable() {
    const overlay = document.getElementById('timetable-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

// CSRF 토큰 가져오기
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}