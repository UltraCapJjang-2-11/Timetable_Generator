// --- Helper Functions ---
function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';').find(c => c.trim().startsWith(name + '='));
        return cookies ? decodeURIComponent(cookies.split('=')[1]) : null;
    }
    return null;
}

function addMessageToChat(text, type, buttons = null) {
    const chatBody = document.querySelector(".ai-chat-body");
    if (!chatBody) return;
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${type}`;
    bubble.textContent = text;
    chatBody.appendChild(bubble);

    if (buttons) {
        const buttonContainer = document.createElement("div");
        buttonContainer.className = "chat-buttons";
        buttons.forEach(buttonInfo => {
            const btn = document.createElement("button");
            btn.className = "bookmarkBtn";
            btn.innerHTML = `<span class="IconContainer"><svg viewBox="0 0 384 512" height="0.9em" class="icon"><path d="M0 48V487.7C0 501.1 10.9 512 24.3 512c5 0 9.9-1.5 14-4.4L192 400 345.7 507.6c4.1 2.9 9 4.4 14 4.4c13.4 0 24.3-10.9 24.3-24.3V48c0-26.5-21.5-48-48-48H48C21.5 0 0 21.5 0 48z"></path></svg></span><p class="text">${buttonInfo.title}</p>`;
            btn.onclick = buttonInfo.action;
            buttonContainer.appendChild(btn);
        });
        chatBody.appendChild(buttonContainer);
    }
    chatBody.scrollTop = chatBody.scrollHeight;
}

function showWelcomeMessage() {
    addMessageToChat(`안녕하세요! 저는 시간표 생성 도우미 Timey입니다! 😊

원하는 시간표를 만들어 드릴게요. 다음과 같이 말씀해주세요:

• '전공 12학점, 교양 6학점으로 시간표 만들어줘'
• '월요일 공강으로 시간표 만들어줘'  
• '데이터베이스 과목 포함해서 시간표 만들어줘'
• '오후 수업 빼고 시간표 만들어줘'`, "bot");
}

// --- Core Chatbot Logic ---
async function handleSendMessage() {
    const input = document.querySelector(".ai-chat-input input");
    const text = input.value.trim();
    if (!text) return;

    addMessageToChat(text, "user");
    input.value = "";
    addMessageToChat("...", "bot loading");

    const sessionId = sessionStorage.getItem('sessionId') || `user_${Date.now()}`;
    sessionStorage.setItem('sessionId', sessionId);

    try {
        const response = await fetch("/parse_constraints/", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
            body: JSON.stringify({ text, session_id: sessionId })
        });
        document.querySelector(".chat-bubble.loading")?.remove();
        if (!response.ok) throw new Error(`HTTP 오류: ${response.status}`);

        const data = await response.json();
        if (data.length === 0) {
            addMessageToChat("응답을 받지 못했어요.", "bot");
            return;
        }

        data.forEach(message => {
            if (message.text) addMessageToChat(message.text, "bot");

            const customData = message.custom?.payload || message.custom;
            if (!customData) return;

            switch (customData.event_type) {
                case 'initiate_timetable_generation_sse':
                    document.dispatchEvent(new CustomEvent('requestTimetableAction', { detail: customData }));
                    break;
                case 'exclude_and_regenerate_timetable':
                    document.dispatchEvent(new CustomEvent('requestTimetableAction', { detail: { ...customData, is_modification: true } }));
                    break;
                case 'save_timetable':
                    document.dispatchEvent(new CustomEvent('requestTimetableSave'));
                    break;
            }
        });
    } catch (error) {
        document.querySelector(".chat-bubble.loading")?.remove();
        addMessageToChat("연결 문제가 발생했습니다.", "bot");
    }
}

// --- Initialization ---
function initChatbot() {
    const chatToggle = document.getElementById("ai-chat-toggle");
    const chatWidget = document.getElementById("ai-chat-widget");
    const closeBtn = document.getElementById("ai-close-btn");
    const sendBtn = document.querySelector(".ai-chat-input button");
    const input = document.querySelector(".ai-chat-input input");

    if (!chatToggle || !chatWidget) return;

    let hasShownWelcome = false;

    chatToggle.addEventListener("click", () => {
        chatWidget.style.display = "flex";
        chatToggle.style.display = "none";
        if (!hasShownWelcome) {
            showWelcomeMessage();
            hasShownWelcome = true;
        }
    });
    
    closeBtn?.addEventListener("click", () => {
        chatWidget.style.display = "none";
        chatToggle.style.display = "flex";
    });
    
    sendBtn?.addEventListener("click", handleSendMessage);
    input?.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSendMessage();
    });

    // 외부에서 챗봇에 메시지를 보내는 이벤트를 리스닝
    document.addEventListener('sendBotMessage', e => {
        addMessageToChat(e.detail.message, "bot", e.detail.buttons);
    });
}

document.addEventListener("DOMContentLoaded", initChatbot);

// Updated: 2024-12-19 