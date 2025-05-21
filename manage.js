const visitedLectures = {};
const connectedUsers = {
  "강의 1": 3,
  "강의 2": 2,
  "강의 3": 1,
  "강의 4": 5,
  "강의 5": 4
};

function selectChat(lectureName) {
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

    // 1회 자동 안내 메시지
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
            return "안녕하세요! Timey에요 :) 무엇을 도와드릴까요?";
        } else {
            return "죄송해요, 아직 그건 잘 모르겠어요.\n'시간표', '추천', '안녕' 같은 키워드를 써보실래요?";
        }
    }
}
