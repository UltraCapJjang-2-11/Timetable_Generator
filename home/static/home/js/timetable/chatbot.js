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
    bubble.innerHTML = text.replace(/\n/g, '<br>');
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
    addMessageToChat(`안녕하세요! 저는 시간표 생성 도우미 Timey입니다! 🤖

원하는 시간표를 설명해주세요:

• "월화는 공강이고 전공 12학점 원해"
• "오전 수업 피하고 오후로 만들어줘"
• "데이터베이스 과목 포함해서 시간표 만들어줘"
• "밀집 시간표로 만들어줘"`, "bot");
}

// 제약조건 요약 표시
function showConstraintsSummary(constraints) {
    if (!constraints || Object.keys(constraints).length === 0) return;

    const parts = [];
    if (constraints.target_total) parts.push(`총 ${constraints.target_total}학점`);
    if (constraints.target_major) parts.push(`전공 ${constraints.target_major}학점`);
    if (constraints.target_elective) parts.push(`교양 ${constraints.target_elective}학점`);
    if (constraints.free_days && constraints.free_days.length > 0) {
        parts.push(`${constraints.free_days.join(', ')} 공강`);
    }
    if (constraints.prefer_morning) parts.push('오전 선호');
    if (constraints.prefer_afternoon) parts.push('오후 선호');
    if (constraints.prefer_compact) parts.push('밀집 시간표');

    if (parts.length > 0) {
        const summary = parts.join(' • ');
        addMessageToChat(`📋 ${summary}`, "bot info");
    }
}

// 시간표 카드 표시
function showTimetableCards(timetables) {
    if (!timetables || timetables.length === 0) return;

    const chatBody = document.querySelector(".ai-chat-body");
    if (!chatBody) return;

    const container = document.createElement("div");
    container.className = "timetable-cards-container";
    container.id = "nl-timetable-cards-container";

    timetables.forEach((timetable, index) => {
        const card = createTimetableCard(timetable, index, timetables);
        container.appendChild(card);
    });

    chatBody.appendChild(container);
    chatBody.scrollTop = chatBody.scrollHeight;

    // 자동으로 첫 번째 시간표를 적용
    if (timetables.length > 0) {
        applyTimetablesArray(timetables, 0);
    }
}

// 시간표 카드 생성
function createTimetableCard(timetable, index, allTimetables) {
    const card = document.createElement("div");
    card.className = "timetable-card nl-timetable-card";
    card.dataset.timetableIndex = index;

    // 카드 클릭 시 해당 시간표로 전환
    card.onclick = (e) => {
        // 버튼 클릭은 제외
        if (e.target.tagName === 'BUTTON') return;

        switchToTimetableByIndex(index, allTimetables);
    };

    const header = document.createElement("div");
    header.className = "timetable-card-header";
    header.innerHTML = `
        <span class="timetable-number">시간표 ${index + 1}</span>
        <span class="timetable-stars">★★★</span>
        <span class="current-badge" style="display: none;">보는 중</span>
    `;

    const body = document.createElement("div");
    body.className = "timetable-card-body";

    // 과목 목록 (timetable 자체가 이미 과목 배열)
    const coursesList = document.createElement("div");
    coursesList.className = "courses-list";

    // timetable이 배열인 경우 (백엔드에서 과목 리스트를 직접 반환)
    const courses = Array.isArray(timetable) ? timetable : (timetable.courses || []);

    if (courses && courses.length > 0) {
        courses.forEach(course => {
            const courseItem = document.createElement("div");
            courseItem.className = "course-item";
            courseItem.textContent = `${course.course_name} (${course.credit || course.credits}학점)`;
            coursesList.appendChild(courseItem);
        });
    }

    // 총 학점
    const totalCredits = courses.reduce((sum, c) => sum + (c.credit || c.credits || 0), 0);

    const creditsInfo = document.createElement("div");
    creditsInfo.className = "credits-info";
    creditsInfo.textContent = `총 ${totalCredits}학점`;

    body.appendChild(coursesList);
    body.appendChild(creditsInfo);

    // 액션 버튼
    const actions = document.createElement("div");
    actions.className = "timetable-card-actions";

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn btn-sm btn-success";
    saveBtn.textContent = '저장하기';
    saveBtn.onclick = (e) => {
        e.stopPropagation();
        saveTimetable(courses);
    };

    actions.appendChild(saveBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);

    return card;
}

// 시간표 배열을 main.js에 전달하고 특정 인덱스로 전환
function applyTimetablesArray(timetables, index = 0) {
    // main.js에 시간표 배열 전달
    document.dispatchEvent(new CustomEvent('applyNLGeneratedTimetables', {
        detail: { timetables: timetables }
    }));

    // 특정 인덱스로 전환
    setTimeout(() => {
        document.dispatchEvent(new CustomEvent('switchToTimetable', {
            detail: { index: index }
        }));
        updateCardHighlight(index);
    }, 100);
}

// 특정 인덱스의 시간표로 전환
function switchToTimetableByIndex(index, allTimetables) {
    document.dispatchEvent(new CustomEvent('switchToTimetable', {
        detail: { index: index }
    }));
    updateCardHighlight(index);
}

// 현재 선택된 카드 하이라이트 업데이트
function updateCardHighlight(currentIndex) {
    const container = document.getElementById('nl-timetable-cards-container');
    if (!container) return;

    // 모든 카드에서 active 클래스 제거
    container.querySelectorAll('.nl-timetable-card').forEach((card, idx) => {
        const badge = card.querySelector('.current-badge');
        if (idx === currentIndex) {
            card.classList.add('active-timetable');
            if (badge) badge.style.display = 'inline-block';
        } else {
            card.classList.remove('active-timetable');
            if (badge) badge.style.display = 'none';
        }
    });
}

// 시간표 저장
async function saveTimetable(courses) {
    try {
        const response = await fetch('/save_timetable/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                title: `AI 생성 시간표 ${new Date().toLocaleDateString()}`,
                courses: courses
            })
        });

        const result = await response.json();

        if (result.success) {
            addMessageToChat("✅ 시간표가 저장되었습니다!", "bot success");
        } else {
            addMessageToChat("❌ 저장 실패: " + (result.error || '알 수 없는 오류'), "bot error");
        }
    } catch (error) {
        console.error('Save error:', error);
        addMessageToChat("❌ 저장 중 오류가 발생했습니다.", "bot error");
    }
}

// --- Core Chatbot Logic (OpenAI 기반) ---
async function handleSendMessage() {
    const input = document.querySelector(".ai-chat-input input");
    const text = input.value.trim();
    if (!text) return;

    addMessageToChat(text, "user");
    input.value = "";

    // 로딩 메시지 표시
    const loadingBubble = document.createElement("div");
    loadingBubble.className = "chat-bubble bot loading";
    loadingBubble.textContent = "...";
    document.querySelector(".ai-chat-body").appendChild(loadingBubble);

    const sessionId = sessionStorage.getItem('nlSessionId') || `user_${Date.now()}`;
    sessionStorage.setItem('nlSessionId', sessionId);

    // Progress overlay 표시
    const progressOverlay = document.getElementById("progress-overlay");
    const progressText = document.getElementById("progress-text");
    if (progressOverlay && progressText) {
        progressOverlay.style.display = "block";
        progressText.textContent = "AI가 시간표 생성 중...";

        // Dots 애니메이션
        const baseText = "AI가 시간표 생성 중";
        let dotCount = 0;
        const dotsInterval = setInterval(() => {
            dotCount = (dotCount + 1) % 4;
            progressText.textContent = baseText + ".".repeat(dotCount === 0 ? 3 : dotCount);
        }, 500);

        // interval ID 저장 (나중에 중지하기 위해)
        progressOverlay._dotsInterval = dotsInterval;
    }

    try {
        const response = await fetch("/api/nl-timetable/chat/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({
                message: text,
                session_id: sessionId
            })
        });

        // 로딩 메시지 제거
        loadingBubble.remove();

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP 오류: ${response.status}`);
        }

        const data = await response.json();

        // 에러 처리
        if (data.error) {
            addMessageToChat(`❌ ${data.error}`, "bot error");

            // 에러 시 progress-overlay 숨김
            if (progressOverlay) {
                if (progressOverlay._dotsInterval) {
                    clearInterval(progressOverlay._dotsInterval);
                    progressOverlay._dotsInterval = null;
                }
                progressOverlay.style.display = "none";
            }
            return;
        }

        // AI 응답 표시
        if (data.message) {
            const messageType = data.stage === 'generating' ? 'bot generating' : 'bot';
            addMessageToChat(data.message, messageType);
        }

        // 제약조건 요약 표시
        if (data.constraints) {
            showConstraintsSummary(data.constraints);
        }

        // 시간표 결과 표시
        if (data.timetables && data.timetables.length > 0) {
            showTimetableCards(data.timetables);

            // 시간표 렌더링 완료 후 progress-overlay 숨김
            if (progressOverlay) {
                // Dots 애니메이션 중지
                if (progressOverlay._dotsInterval) {
                    clearInterval(progressOverlay._dotsInterval);
                    progressOverlay._dotsInterval = null;
                }
                // 렌더링 완료 후 오버레이 숨김
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        progressOverlay.style.display = "none";
                    }, 1500);
                });
            }
        } else {
            // 시간표가 없으면 바로 오버레이 숨김
            if (progressOverlay) {
                if (progressOverlay._dotsInterval) {
                    clearInterval(progressOverlay._dotsInterval);
                    progressOverlay._dotsInterval = null;
                }
                progressOverlay.style.display = "none";
            }
        }

    } catch (error) {
        loadingBubble.remove();
        console.error('Chat error:', error);
        addMessageToChat(`❌ ${error.message || '연결 문제가 발생했습니다.'}`, "bot error");

        // 에러 시 progress-overlay 숨김
        if (progressOverlay) {
            if (progressOverlay._dotsInterval) {
                clearInterval(progressOverlay._dotsInterval);
                progressOverlay._dotsInterval = null;
            }
            progressOverlay.style.display = "none";
        }
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

    // 챗봇 토글 버튼 클릭 이벤트
    chatToggle.addEventListener("click", function(e) {
        e.preventDefault();
        e.stopPropagation();

        chatWidget.classList.add('visible');
        chatToggle.classList.add('hidden');
        chatWidget.style.setProperty('display', 'flex', 'important');
        chatToggle.style.setProperty('display', 'none', 'important');

        if (!hasShownWelcome) {
            showWelcomeMessage();
            hasShownWelcome = true;
        }
    });

    // 챗봇 닫기 버튼 이벤트
    if (closeBtn) {
        closeBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();

            chatWidget.classList.remove('visible');
            chatToggle.classList.remove('hidden');
            chatWidget.style.setProperty('display', 'none', 'important');
            chatToggle.style.setProperty('display', 'flex', 'important');
        });
    }

    // 메시지 전송 버튼 이벤트
    if (sendBtn) {
        sendBtn.addEventListener("click", handleSendMessage);
    }

    // 엔터키 이벤트
    if (input) {
        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleSendMessage();
        });
    }

    // 외부에서 챗봇에 메시지를 보내는 이벤트를 리스닝
    document.addEventListener('sendBotMessage', e => {
        addMessageToChat(e.detail.message, "bot", e.detail.buttons);
    });
}

// DOM이 준비되면 초기화
if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initChatbot);
} else {
    initChatbot();
}
