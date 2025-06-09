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

    // 1회 자동 안내 메시지 제거함

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
        return null; // 봇 메시지 우선 삭제해놓음
    }
}