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

원하는 시간표 조건을 자유롭게 말씀해주세요:

• "월화는 공강이고 전공 12학점 원해"
• "오전 수업 피하고 오후로 만들어줘"
• "데이터베이스 과목 포함해서 시간표 만들어줘"
• "밀집 시간표로 만들어줘"`, "bot");
}

// 제약조건 요약 표시 (간단 버전)
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

// 제약조건 확인 카드 표시 (확인 단계용)
function showConfirmationCard(constraints, sessionId) {
    const chatBody = document.querySelector(".ai-chat-body");
    if (!chatBody) return;

    // 제약조건 요약 카드 생성
    const confirmCard = document.createElement("div");
    confirmCard.className = "confirmation-card";

    // 제약조건 목록 생성
    const parts = [];
    if (constraints.target_total) parts.push(`• 총 ${constraints.target_total}학점`);
    if (constraints.target_major) parts.push(`• 전공 ${constraints.target_major}학점`);
    if (constraints.target_elective) parts.push(`• 교양 ${constraints.target_elective}학점`);

    if (constraints.free_days && constraints.free_days.length > 0) {
        parts.push(`• ${constraints.free_days.join(', ')} 공강`);
    }

    if (constraints.avoid_time_ranges && constraints.avoid_time_ranges.length > 0) {
        constraints.avoid_time_ranges.forEach(range => {
            const days = range.days.join(', ');
            if (range.start_hour === 9 && range.end_hour === 12) {
                parts.push(`• ${days} 오전 회피`);
            } else if (range.start_hour === 13 && range.end_hour === 18) {
                parts.push(`• ${days} 오후 회피`);
            } else {
                parts.push(`• ${days} ${range.start_hour}-${range.end_hour}시 회피`);
            }
        });
    }

    // 특정 시간 회피 (avoid_times)
    if (constraints.avoid_times && constraints.avoid_times.length > 0) {
        // 요일별로 그룹화
        const timesByDay = {};
        constraints.avoid_times.forEach(time => {
            if (!timesByDay[time.day]) {
                timesByDay[time.day] = [];
            }
            timesByDay[time.day].push(time.hour);
        });

        // 요일별로 표시
        Object.keys(timesByDay).forEach(day => {
            const hours = timesByDay[day].sort((a, b) => a - b);
            const hoursStr = hours.map(h => `${h}시`).join(', ');
            parts.push(`• ${day}요일 ${hoursStr} 회피`);
        });
    }

    if (constraints.prefer_morning) parts.push('• 오전 선호');
    if (constraints.prefer_afternoon) parts.push('• 오후 선호');
    if (constraints.prefer_compact) parts.push('• 밀집 시간표');
    if (constraints.preferred_instructors && constraints.preferred_instructors.length > 0) {
        parts.push(`• 선호 교수: ${constraints.preferred_instructors.join(', ')}`);
    }
    if (constraints.required_courses && constraints.required_courses.length > 0) {
        parts.push(`• 필수 과목: ${constraints.required_courses.join(', ')}`);
    }

    const summaryHTML = parts.length > 0
        ? parts.join('<br>')
        : '• 기본 설정으로 시간표 생성';

    confirmCard.innerHTML = `
        <div class="confirmation-header">
            <span class="confirmation-icon">📋</span>
            <span class="confirmation-title">시간표 생성 조건</span>
        </div>
        <div class="confirmation-body">
            ${summaryHTML}
        </div>
        <div class="confirmation-actions">
            <button class="btn-modify">조건 수정</button>
            <button class="btn-generate">시간표 생성하기</button>
        </div>
    `;

    chatBody.appendChild(confirmCard);
    chatBody.scrollTop = chatBody.scrollHeight;

    // 버튼 이벤트 리스너
    const modifyBtn = confirmCard.querySelector('.btn-modify');
    const generateBtn = confirmCard.querySelector('.btn-generate');

    modifyBtn.onclick = () => {
        addMessageToChat("어떤 조건을 수정하시겠어요?", "bot");
    };

    generateBtn.onclick = async () => {
        // 버튼 비활성화
        generateBtn.disabled = true;
        generateBtn.textContent = '생성 중...';

        // 시간표 생성 호출
        await triggerTimetableGeneration(constraints, sessionId);
    };
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

// 시간표 생성 트리거 (확인 버튼 클릭 시 호출)
async function triggerTimetableGeneration(constraints, sessionId) {
    const progressOverlay = document.getElementById("progress-overlay");
    const progressText = document.getElementById("progress-text");

    try {
        // 전체 화면 progress overlay 표시
        if (progressOverlay && progressText) {
            progressOverlay.style.display = "block";
            progressText.textContent = "최적화 시간표 생성 중...";

            // Dots 애니메이션
            const baseText = "최적화 시간표 생성 중";
            let dotCount = 0;
            const dotsInterval = setInterval(() => {
                dotCount = (dotCount + 1) % 4;
                progressText.textContent = baseText + ".".repeat(dotCount === 0 ? 3 : dotCount);
            }, 500);

            // interval ID 저장
            progressOverlay._dotsInterval = dotsInterval;
        }

        // 시간표 생성 API 호출
        const generateResponse = await fetch("/api/nl-timetable/generate/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({
                constraints: constraints,
                session_id: sessionId
            })
        });

        if (!generateResponse.ok) {
            const errorData = await generateResponse.json();
            throw new Error(errorData.error || `HTTP 오류: ${generateResponse.status}`);
        }

        const generateData = await generateResponse.json();

        // 생성 완료 메시지
        if (generateData.message) {
            addMessageToChat(generateData.message, "bot success");
        }

        // 시간표 결과 표시
        if (generateData.timetables && generateData.timetables.length > 0) {
            showTimetableCards(generateData.timetables);
        }

        // 에러 처리
        if (generateData.error) {
            addMessageToChat(`❌ ${generateData.error}`, "bot error");
        }

    } catch (error) {
        console.error('Generate error:', error);
        addMessageToChat(`❌ ${error.message || '시간표 생성 중 오류가 발생했습니다.'}`, "bot error");
    } finally {
        // progress-overlay 숨김
        if (progressOverlay) {
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
    }
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
                title: `최적화 시간표 ${new Date().toLocaleDateString()}`,
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

// --- Core Chatbot Logic ---
async function handleSendMessage() {
    const input = document.querySelector(".ai-chat-input input");
    const text = input.value.trim();
    if (!text) return;

    addMessageToChat(text, "user");
    input.value = "";

    // 타이핑 인디케이터 표시
    const loadingBubble = document.createElement("div");
    loadingBubble.className = "chat-bubble bot loading";
    loadingBubble.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    document.querySelector(".ai-chat-body").appendChild(loadingBubble);

    const sessionId = sessionStorage.getItem('nlSessionId') || `user_${Date.now()}`;
    sessionStorage.setItem('nlSessionId', sessionId);

    // Progress overlay 요소 참조만 가져오기 (아직 표시하지 않음)
    const progressOverlay = document.getElementById("progress-overlay");
    const progressText = document.getElementById("progress-text");

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
            return;
        }

        // 챗봇 응답 표시
        if (data.message) {
            addMessageToChat(data.message, 'bot');
        }

        // stage별 처리
        if (data.stage === 'confirming' && data.confirmation_required) {
            // Confirming 단계: 확인 카드 표시
            if (data.constraints) {
                showConfirmationCard(data.constraints, sessionId);
            }
        } else if (data.stage === 'gathering') {
            // Gathering 단계: 간단한 요약만 표시
            if (data.constraints) {
                showConstraintsSummary(data.constraints);
            }
        } else if (data.stage === 'generating' && data.ready_to_generate) {
            // Generating 단계: 사용자가 confirming 단계에서 버튼을 클릭한 경우
            // 즉시 시간표 생성 (백엔드에서 사용자가 "네", "확인" 등을 입력한 경우)
            await triggerTimetableGeneration(data.constraints, sessionId);
        }

    } catch (error) {
        loadingBubble.remove();
        console.error('Chat error:', error);
        addMessageToChat(`❌ ${error.message || '연결 문제가 발생했습니다.'}`, "bot error");

        // 에러 시 progress-overlay 숨김 (혹시 표시되었을 경우)
        if (progressOverlay && progressOverlay.style.display === "block") {
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
