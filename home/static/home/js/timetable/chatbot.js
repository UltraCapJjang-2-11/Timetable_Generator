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

// 전역 상태: 시간표 목록 및 페이지네이션
let allTimetablesList = [];
let currentPage = 1;
let itemsPerPage = 6;
let currentSortType = 'recommended'; // 'recommended', 'credits', 'free_days'

// 시간표 카드 표시 (개선된 버전)
function showTimetableCards(timetables) {
    if (!timetables || timetables.length === 0) return;

    const chatBody = document.querySelector(".ai-chat-body");
    if (!chatBody) return;

    // 기존 컨테이너가 있으면 제거
    const existingContainer = document.getElementById("nl-timetable-cards-container");
    if (existingContainer) {
        existingContainer.remove();
    }

    // 전역 상태 업데이트
    // timetables는 배열의 배열: [[course1, course2, ...], [course1, course2, ...], ...]
    allTimetablesList = timetables.map((timetableArray, idx) => {
        // timetableArray가 배열인 경우 그대로 사용, 아니면 courses 속성 추출
        const courses = Array.isArray(timetableArray) ? timetableArray : (timetableArray.courses || []);
        
        return {
            courses: courses,
            originalIndex: idx,
            stats: calculateTimetableStats({ courses: courses })
        };
    });

    // 정렬 적용
    sortTimetables(currentSortType);

    // 컨테이너 생성
    const wrapper = document.createElement("div");
    wrapper.className = "timetable-cards-wrapper";
    wrapper.id = "nl-timetable-cards-container";

    // 정렬/필터 컨트롤 추가
    const controls = createTimetableControls();
    wrapper.appendChild(controls);

    // 카드 그리드 컨테이너
    const container = document.createElement("div");
    container.className = "timetable-cards-grid";
    wrapper.appendChild(container);

    // 페이지네이션 컨테이너
    const paginationContainer = document.createElement("div");
    paginationContainer.className = "timetable-pagination";
    paginationContainer.id = "timetable-pagination";
    wrapper.appendChild(paginationContainer);

    chatBody.appendChild(wrapper);
    
    // 첫 페이지 렌더링
    renderTimetablePage(1);

    // 첫 번째 시간표는 자동으로 적용하고 펼침
    if (timetables.length > 0) {
        applyTimetablesArray(timetables, 0);
        
        // 첫 페이지의 첫 번째 카드만 펼치기
        setTimeout(() => {
            const firstCard = container.querySelector('.nl-timetable-card');
            if (firstCard) {
                firstCard.classList.add('expanded');
            }
        }, 100);
    }
}

// 정렬/필터 컨트롤 생성
function createTimetableControls() {
    const controls = document.createElement("div");
    controls.className = "timetable-controls";

    const sortLabel = document.createElement("span");
    sortLabel.className = "control-label";
    sortLabel.textContent = "정렬:";

    const sortSelect = document.createElement("select");
    sortSelect.className = "timetable-sort-select";
    sortSelect.innerHTML = `
        <option value="recommended">추천순</option>
        <option value="credits">학점순</option>
        <option value="free_days">공강순</option>
    `;
    sortSelect.value = currentSortType;
    sortSelect.addEventListener('change', (e) => {
        currentSortType = e.target.value;
        sortTimetables(currentSortType);
        renderTimetablePage(1);
    });

    controls.appendChild(sortLabel);
    controls.appendChild(sortSelect);

    return controls;
}

// 시간표 정렬
function sortTimetables(sortType) {
    switch(sortType) {
        case 'credits':
            allTimetablesList.sort((a, b) => {
                const creditsA = getTotalCredits({ courses: a.courses || [] });
                const creditsB = getTotalCredits({ courses: b.courses || [] });
                return creditsB - creditsA;
            });
            break;
        case 'free_days':
            allTimetablesList.sort((a, b) => {
                const freeA = a.stats ? a.stats.freeDays : 0;
                const freeB = b.stats ? b.stats.freeDays : 0;
                return freeB - freeA;
            });
            break;
        case 'recommended':
        default:
            // 추천순은 원래 순서 유지 (백엔드에서 이미 정렬됨)
            allTimetablesList.sort((a, b) => a.originalIndex - b.originalIndex);
            break;
    }
}

// 시간표 페이지 렌더링
function renderTimetablePage(page) {
    currentPage = page;
    const container = document.querySelector(".timetable-cards-grid");
    if (!container) return;

    container.innerHTML = '';

    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, allTimetablesList.length);
    const pageTimetables = allTimetablesList.slice(startIndex, endIndex);

    pageTimetables.forEach((timetable, index) => {
        const globalIndex = startIndex + index;
        const card = createTimetableCard(timetable, globalIndex, allTimetablesList);
        container.appendChild(card);
        // 페이지 변경 시 모든 카드는 접힌 상태로 시작
        card.classList.remove('expanded');
    });

    // 페이지네이션 UI 업데이트
    renderPagination();

    // 선택된 카드 하이라이트 업데이트
    updateCardHighlight(getCurrentTimetableIndex());
}

// 페이지네이션 렌더링
function renderPagination() {
    const paginationContainer = document.getElementById("timetable-pagination");
    if (!paginationContainer) return;

    const totalPages = Math.ceil(allTimetablesList.length / itemsPerPage);
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    let paginationHTML = '<div class="pagination-controls">';

    // 이전 버튼
    if (currentPage > 1) {
        paginationHTML += `<button class="pagination-btn prev" onclick="goToTimetablePage(${currentPage - 1})">‹ 이전</button>`;
    }

    // 페이지 번호
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        paginationHTML += `<button class="pagination-btn" onclick="goToTimetablePage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        paginationHTML += `<button class="pagination-btn ${activeClass}" onclick="goToTimetablePage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
        paginationHTML += `<button class="pagination-btn" onclick="goToTimetablePage(${totalPages})">${totalPages}</button>`;
    }

    // 다음 버튼
    if (currentPage < totalPages) {
        paginationHTML += `<button class="pagination-btn next" onclick="goToTimetablePage(${currentPage + 1})">다음 ›</button>`;
    }

    paginationHTML += '</div>';
    paginationHTML += `<div class="pagination-info">${currentPage} / ${totalPages} 페이지 (총 ${allTimetablesList.length}개)</div>`;

    paginationContainer.innerHTML = paginationHTML;
}

// 페이지 이동 함수 (전역으로 노출)
window.goToTimetablePage = function(page) {
    const totalPages = Math.ceil(allTimetablesList.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    renderTimetablePage(page);
    const container = document.querySelector(".timetable-cards-grid");
    if (container) {
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

// 현재 시간표 인덱스 가져오기
function getCurrentTimetableIndex() {
    // main.js에서 현재 인덱스를 가져오거나, 기본값 0
    if (window.getCurrentTimetableIndex) {
        return window.getCurrentTimetableIndex();
    }
    return 0;
}

// 시간표 카드 생성 (아코디언 방식)
function createTimetableCard(timetable, index, allTimetables) {
    const card = document.createElement("div");
    card.className = "timetable-card nl-timetable-card";
    card.dataset.timetableIndex = index;

    // courses 배열 추출
    const courses = timetable.courses || (Array.isArray(timetable) ? timetable : []);
    const stats = timetable.stats || calculateTimetableStats({ courses: courses });
    const totalCredits = getTotalCredits({ courses: courses });

    // 헤더 (클릭 가능)
    const header = document.createElement("div");
    header.className = "timetable-card-header";
    
    // 헤더 왼쪽: 기본 정보
    const headerLeft = document.createElement("div");
    headerLeft.style.display = "flex";
    headerLeft.style.alignItems = "center";
    headerLeft.style.gap = "12px";
    headerLeft.style.flex = "1";
    
    const headerInfo = document.createElement("div");
    headerInfo.style.display = "flex";
    headerInfo.style.flexDirection = "column";
    headerInfo.style.gap = "4px";
    
    const numberAndStars = document.createElement("div");
    numberAndStars.style.display = "flex";
    numberAndStars.style.alignItems = "center";
    numberAndStars.style.gap = "8px";
    numberAndStars.innerHTML = `
        <span class="timetable-number">시간표 ${index + 1}</span>
        <span class="timetable-stars">${getStarsDisplay(stats.score)}</span>
        <span class="current-badge" style="display: none;">보는 중</span>
    `;
    
    const quickStats = document.createElement("div");
    quickStats.style.display = "flex";
    quickStats.style.gap = "12px";
    quickStats.style.fontSize = "12px";
    quickStats.style.color = "#6b7280";
    quickStats.innerHTML = `
        <span>📅 공강 ${stats.freeDays}일</span>
        <span>📚 ${totalCredits}학점</span>
        <span>📝 ${courses.length}개 과목</span>
    `;
    
    headerInfo.appendChild(numberAndStars);
    headerInfo.appendChild(quickStats);
    headerLeft.appendChild(headerInfo);
    header.appendChild(headerLeft);

    // 헤더 클릭 시 아코디언 토글
    header.onclick = (e) => {
        e.stopPropagation();
        toggleCardExpand(card, index);
    };

    // 시간표 미리보기 (펼쳐진 상태에서만 표시)
    const preview = generateTimetablePreview(courses);
    preview.className = "timetable-preview";

    // 통계 정보 (펼쳐진 상태에서만 표시)
    const statsSection = document.createElement("div");
    statsSection.className = "timetable-stats";
    statsSection.innerHTML = `
        <div class="stat-item">
            <span class="stat-icon">📅</span>
            <span class="stat-label">공강:</span>
            <span class="stat-value">${stats.freeDays}일</span>
        </div>
        <div class="stat-item">
            <span class="stat-icon">⏰</span>
            <span class="stat-label">평균:</span>
            <span class="stat-value">${stats.avgHours.toFixed(1)}h</span>
        </div>
        <div class="stat-item">
            <span class="stat-icon">📚</span>
            <span class="stat-label">학점:</span>
            <span class="stat-value">${totalCredits}</span>
        </div>
    `;

    // 과목 목록 (펼쳐진 상태에서만 표시)
    const coursesList = document.createElement("div");
    coursesList.className = "courses-list-expanded";
    if (courses.length > 0) {
        courses.forEach(course => {
            const courseItem = document.createElement("div");
            courseItem.className = "course-item";
            const courseName = course.course_name || course.name || '';
            const credits = course.credit || course.credits || 0;
            courseItem.textContent = `${courseName} (${credits}학점)`;
            coursesList.appendChild(courseItem);
        });
    } else {
        coursesList.innerHTML = '<div style="text-align: center; padding: 20px; color: #6b7280;">과목 정보 없음</div>';
    }

    // 액션 버튼 (펼쳐진 상태에서만 표시)
    const actions = document.createElement("div");
    actions.className = "timetable-card-actions";

    const viewBtn = document.createElement("button");
    viewBtn.className = "btn btn-sm btn-primary";
    viewBtn.textContent = '상세보기';
    viewBtn.onclick = (e) => {
        e.stopPropagation();
        showTimetableDetailModal(timetable, index, allTimetables);
    };

    const applyBtn = document.createElement("button");
    applyBtn.className = "btn btn-sm btn-apply";
    applyBtn.textContent = '적용하기';
    applyBtn.onclick = (e) => {
        e.stopPropagation();
        switchToTimetableByIndex(index, allTimetables);
    };

    const saveBtn = document.createElement("button");
    saveBtn.className = "btn btn-sm btn-success";
    saveBtn.textContent = '저장';
    saveBtn.onclick = (e) => {
        e.stopPropagation();
        saveTimetable(courses);
    };

    actions.appendChild(viewBtn);
    actions.appendChild(applyBtn);
    actions.appendChild(saveBtn);

    // 카드 조립
    const body = document.createElement("div");
    body.className = "timetable-card-body";
    body.appendChild(preview);
    body.appendChild(statsSection);
    body.appendChild(coursesList);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);

    // 첫 카드만 기본적으로 펼쳐짐 (첫 페이지의 첫 번째 카드만)
    // 페이지 변경 시에는 renderTimetablePage에서 처리하므로 여기서는 제거

    return card;
}

// 카드 아코디언 토글 함수
function toggleCardExpand(card, index) {
    const isExpanded = card.classList.contains('expanded');
    
    // 모든 카드 접기
    document.querySelectorAll('.nl-timetable-card').forEach(c => {
        c.classList.remove('expanded');
    });
    
    // 클릭한 카드만 펼치기
    if (!isExpanded) {
        card.classList.add('expanded');
        
        // 펼쳤을 때 자동으로 해당 시간표 적용
        switchToTimetableByIndex(index, allTimetablesList);
        
        // 스크롤로 이동
        setTimeout(() => {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }
}

// 시간표 미리보기 생성 (요일별 타임라인)
function generateTimetablePreview(courses) {
    const preview = document.createElement("div");
    preview.className = "timetable-preview";

    // 요일별 시간대 표시 (월~금, 9시~18시)
    const days = ['월', '화', '수', '목', '금'];
    const hours = Array.from({length: 10}, (_, i) => i + 9); // 9~18시

    // 요일별 수업 시간대 계산
    const daySchedule = {
        '월': new Set(),
        '화': new Set(),
        '수': new Set(),
        '목': new Set(),
        '금': new Set()
    };

    courses.forEach(course => {
        const schedules = course.schedules || course.schedule || [];
        schedules.forEach(schedule => {
            const day = schedule.day || schedule.day_of_week || '';
            if (!daySchedule[day]) return;

            const times = schedule.times || schedule.time_slots || '';
            if (Array.isArray(times)) {
                times.forEach(timeSlot => {
                    const hour = parseInt(timeSlot) + 8; // 슬롯 번호를 시간으로 변환 (02 -> 10시)
                    if (hour >= 9 && hour <= 18) {
                        daySchedule[day].add(hour);
                    }
                });
            } else if (typeof times === 'string') {
                // "02,03,04" 형식 파싱
                const timeSlots = times.split(',').map(t => parseInt(t.trim())).filter(t => !isNaN(t));
                timeSlots.forEach(timeSlot => {
                    const hour = timeSlot + 8;
                    if (hour >= 9 && hour <= 18) {
                        daySchedule[day].add(hour);
                    }
                });
            }
        });
    });

    // 타임라인 생성
    days.forEach(day => {
        const dayCol = document.createElement("div");
        dayCol.className = "preview-day";

        const dayLabel = document.createElement("div");
        dayLabel.className = "preview-day-label";
        dayLabel.textContent = day;
        dayCol.appendChild(dayLabel);

        const timeline = document.createElement("div");
        timeline.className = "preview-timeline";

        hours.forEach(hour => {
            const hourBlock = document.createElement("div");
            hourBlock.className = "preview-hour-block";
            if (daySchedule[day].has(hour)) {
                hourBlock.classList.add('has-class');
            }
            timeline.appendChild(hourBlock);
        });

        dayCol.appendChild(timeline);
        preview.appendChild(dayCol);
    });

    return preview;
}

// 시간표 통계 계산
function calculateTimetableStats(timetable) {
    const courses = Array.isArray(timetable) ? timetable : (timetable.courses || []);
    
    const days = ['월', '화', '수', '목', '금'];
    const dayHasClass = {
        '월': false,
        '화': false,
        '수': false,
        '목': false,
        '금': false
    };

    let totalHours = 0;
    const hoursByDay = {
        '월': new Set(),
        '화': new Set(),
        '수': new Set(),
        '목': new Set(),
        '금': new Set()
    };

    courses.forEach(course => {
        const schedules = course.schedules || course.schedule || [];
        schedules.forEach(schedule => {
            const day = schedule.day || schedule.day_of_week || '';
            if (!days.includes(day)) return;

            dayHasClass[day] = true;

            const times = schedule.times || schedule.time_slots || '';
            if (Array.isArray(times)) {
                times.forEach(timeSlot => {
                    const hour = parseInt(timeSlot) + 8;
                    if (hour >= 9 && hour <= 18) {
                        hoursByDay[day].add(hour);
                        totalHours++;
                    }
                });
            } else if (typeof times === 'string') {
                const timeSlots = times.split(',').map(t => parseInt(t.trim())).filter(t => !isNaN(t));
                timeSlots.forEach(timeSlot => {
                    const hour = timeSlot + 8;
                    if (hour >= 9 && hour <= 18) {
                        hoursByDay[day].add(hour);
                        totalHours++;
                    }
                });
            }
        });
    });

    const freeDays = days.filter(day => !dayHasClass[day]).length;
    const daysWithClass = days.filter(day => dayHasClass[day]).length;
    const avgHours = daysWithClass > 0 ? totalHours / daysWithClass : 0;

    // 추천 점수 계산 (0~5)
    let score = 3.0; // 기본 점수
    if (freeDays >= 2) score += 0.5; // 공강이 많으면 좋음
    if (avgHours <= 4) score += 0.3; // 평균 수업 시간이 적당하면 좋음
    if (avgHours <= 3) score += 0.2; // 더 적으면 더 좋음
    score = Math.min(5, Math.max(1, score));

    return {
        freeDays,
        avgHours,
        totalHours,
        score
    };
}

// 총 학점 계산 헬퍼
function getTotalCredits(timetable) {
    const courses = Array.isArray(timetable) ? timetable : (timetable.courses || []);
    return courses.reduce((sum, c) => sum + (c.credit || c.credits || 0), 0);
}

// 별점 표시 헬퍼
function getStarsDisplay(score) {
    const fullStars = Math.floor(score);
    const hasHalfStar = score % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    return '★'.repeat(fullStars) + (hasHalfStar ? '☆' : '') + '☆'.repeat(emptyStars);
}

// 시간표 배열을 main.js에 전달하고 특정 인덱스로 전환
function applyTimetablesArray(timetables, index = 0) {
    // timetables는 배열의 배열: [[course1, course2, ...], ...]
    // 원본 배열 그대로 전달 (main.js에서 처리)
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
    // allTimetablesList에서 원본 시간표 배열 찾기
    const timetable = allTimetablesList[index];
    if (!timetable) return;
    
    // 원본 인덱스 사용 (정렬 전 인덱스)
    const originalIndex = timetable.originalIndex !== undefined ? timetable.originalIndex : index;
    
    // 원본 timetables 배열 재구성 (백엔드 형식: 배열의 배열)
    const originalTimetables = allTimetablesList.map(t => t.courses || []);
    
    // main.js에 원본 배열 전달
    document.dispatchEvent(new CustomEvent('applyNLGeneratedTimetables', {
        detail: { timetables: originalTimetables }
    }));
    
    // 원본 인덱스로 전환
    setTimeout(() => {
        document.dispatchEvent(new CustomEvent('switchToTimetable', {
            detail: { index: originalIndex }
        }));
        updateCardHighlight(index);
    }, 100);
}

// 현재 선택된 카드 하이라이트 업데이트
function updateCardHighlight(currentIndex) {
    const container = document.getElementById('nl-timetable-cards-container');
    if (!container) return;

    // 그리드 내의 모든 카드 찾기
    const cards = container.querySelectorAll('.nl-timetable-card');
    cards.forEach((card, idx) => {
        const cardIndex = parseInt(card.dataset.timetableIndex) || idx;
        const badge = card.querySelector('.current-badge');
        if (cardIndex === currentIndex) {
            card.classList.add('active-timetable');
            if (badge) badge.style.display = 'inline-block';
        } else {
            card.classList.remove('active-timetable');
            if (badge) badge.style.display = 'none';
        }
    });
}

// 시간표 상세보기 모달 표시
function showTimetableDetailModal(timetable, index, allTimetables) {
    // 시간표 데이터 올바르게 파싱
    let courses = [];
    if (Array.isArray(timetable)) {
        courses = timetable;
    } else if (timetable && timetable.courses) {
        courses = timetable.courses;
    } else if (timetable && Array.isArray(timetable)) {
        courses = timetable;
    }
    
    // 통계 계산 (올바른 데이터로)
    const stats = calculateTimetableStats({ courses: courses });
    const totalCredits = courses.reduce((sum, c) => sum + (c.credit || c.credits || 0), 0);

    // 기존 모달이 있으면 제거
    const existingModal = document.getElementById('timetable-detail-modal');
    if (existingModal) {
        existingModal.remove();
    }

    // 모달 생성
    const modal = document.createElement("div");
    modal.id = "timetable-detail-modal";
    modal.className = "timetable-detail-modal";
    modal.dataset.timetableIndex = index; // 모달에 인덱스 저장
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    };

    // 모달 내용
    const modalContent = document.createElement("div");
    modalContent.className = "modal-content";
    modalContent.onclick = (e) => e.stopPropagation();

    // 헤더
    const header = document.createElement("div");
    header.className = "modal-header";
    header.innerHTML = `
        <h3>시간표 ${index + 1} 상세보기</h3>
        <button class="modal-close" onclick="this.closest('.timetable-detail-modal').remove()">×</button>
    `;

    // 통계 섹션
    const statsSection = document.createElement("div");
    statsSection.className = "modal-stats";
    statsSection.innerHTML = `
        <div class="modal-stat-item">
            <span class="stat-label">공강 요일</span>
            <span class="stat-value">${stats.freeDays}일</span>
        </div>
        <div class="modal-stat-item">
            <span class="stat-label">평균 수업 시간</span>
            <span class="stat-value">${stats.avgHours.toFixed(1)}시간</span>
        </div>
        <div class="modal-stat-item">
            <span class="stat-label">총 학점</span>
            <span class="stat-value">${totalCredits}학점</span>
        </div>
        <div class="modal-stat-item">
            <span class="stat-label">과목 수</span>
            <span class="stat-value">${courses.length}개</span>
        </div>
    `;

    // 과목 목록
    const coursesList = document.createElement("div");
    coursesList.className = "modal-courses-list";
    
    if (courses.length === 0) {
        coursesList.innerHTML = '<div style="text-align: center; padding: 20px; color: #6b7280;">과목 정보가 없습니다.</div>';
    } else {
        courses.forEach(course => {
            const courseItem = document.createElement("div");
            courseItem.className = "modal-course-item";
            
            const courseName = course.course_name || course.name || '';
            const credits = course.credit || course.credits || 0;
            const instructor = course.instructor_name || course.instructor || '';
            
            // 시간표 정보
            const schedules = course.schedules || course.schedule || [];
            const scheduleText = schedules.map(s => {
                const day = s.day || s.day_of_week || '';
                const times = s.times || s.time_slots || '';
                const location = s.location || '';
                
                let timeStr = '';
                if (Array.isArray(times)) {
                    const hours = times.map(t => parseInt(t) + 8).filter(h => h >= 9 && h <= 18);
                    timeStr = hours.map(h => `${h}시`).join(', ');
                } else if (typeof times === 'string') {
                    const timeSlots = times.split(',').map(t => parseInt(t.trim())).filter(t => !isNaN(t));
                    const hours = timeSlots.map(t => t + 8).filter(h => h >= 9 && h <= 18);
                    timeStr = hours.map(h => `${h}시`).join(', ');
                }
                
                return `${day} ${timeStr}${location ? ' @ ' + location : ''}`;
            }).join(' | ');

            courseItem.innerHTML = `
                <div class="course-name">${courseName}</div>
                <div class="course-meta">
                    <span class="course-credits">${credits}학점</span>
                    ${instructor ? `<span class="course-instructor">${instructor}</span>` : ''}
                </div>
                <div class="course-schedule">${scheduleText || '시간 정보 없음'}</div>
            `;
            coursesList.appendChild(courseItem);
        });
    }

    // 액션 버튼
    const actions = document.createElement("div");
    actions.className = "modal-actions";
    actions.innerHTML = `
        <button class="btn btn-primary" onclick="applyTimetableFromModal(${index})">이 시간표 적용하기</button>
        <button class="btn btn-success" onclick="saveTimetableFromModal(${index})">저장하기</button>
    `;

    modalContent.appendChild(header);
    modalContent.appendChild(statsSection);
    modalContent.appendChild(coursesList);
    modalContent.appendChild(actions);
    modal.appendChild(modalContent);

    document.body.appendChild(modal);
    
    // 애니메이션
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// 모달에서 시간표 적용
window.applyTimetableFromModal = function(index) {
    // allTimetablesList에서 해당 인덱스의 시간표 찾기
    if (!allTimetablesList || index >= allTimetablesList.length) {
        console.error('Invalid timetable index:', index);
        return;
    }
    
    const timetable = allTimetablesList[index];
    if (!timetable) {
        console.error('Timetable not found at index:', index);
        return;
    }
    
    // 원본 인덱스 사용 (정렬 전 인덱스)
    const originalIndex = timetable.originalIndex !== undefined ? timetable.originalIndex : index;
    
    // 원본 timetables 배열 재구성 (백엔드 형식: 배열의 배열)
    const originalTimetables = allTimetablesList.map(t => t.courses || []);
    
    // main.js에 원본 배열 전달
    document.dispatchEvent(new CustomEvent('applyNLGeneratedTimetables', {
        detail: { timetables: originalTimetables }
    }));
    
    // 원본 인덱스로 전환
    setTimeout(() => {
        document.dispatchEvent(new CustomEvent('switchToTimetable', {
            detail: { index: originalIndex }
        }));
        updateCardHighlight(index);
    }, 100);
    
    // 모달 닫기
    const modal = document.getElementById('timetable-detail-modal');
    if (modal) {
        modal.remove();
    }
};

// 모달에서 시간표 저장
window.saveTimetableFromModal = function(index) {
    if (!allTimetablesList || index >= allTimetablesList.length) {
        console.error('Invalid timetable index:', index);
        return;
    }
    
    const timetable = allTimetablesList[index];
    if (!timetable) {
        console.error('Timetable not found at index:', index);
        return;
    }
    
    const courses = timetable.courses || [];
    saveTimetable(courses);
    
    const modal = document.getElementById('timetable-detail-modal');
    if (modal) {
        modal.remove();
    }
};

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
