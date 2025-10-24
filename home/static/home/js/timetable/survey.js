// survey.js - 설문조사 오버레이 기능 구현

document.addEventListener("DOMContentLoaded", () => {
    const steps = document.querySelectorAll(".survey-step");
    const nextBtn = document.querySelector(".next-btn");
    const prevBtn = document.querySelector(".prev-btn");
    const progressFill = document.getElementById("survey-progress-fill");
    const currentStepText = document.getElementById("current-step-text");
    const dots = document.querySelectorAll(".survey-dots .dot");
    let currentStep = 0;

    // 초기 상태 설정
    updateProgress();
    updateButtons();

    // 자동완성 관리 객체
    const autocompleteManager = {
        currentFocus: -1,
        debounceTimer: null,

        // API 호출 함수
        async fetchSuggestions(query, type) {
            if (!query || query.length < 1) {
                return [];
            }

            try {
                const endpoint = type === 'instructor'
                    ? '/api/autocomplete/instructors/'
                    : '/api/autocomplete/courses/';

                const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                return data.results || [];
            } catch (error) {
                console.error('자동완성 API 오류:', error);
                return [];
            }
        },

        // 디바운싱 함수
        debounce(func, delay = 300) {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(func, delay);
        },

        // 자동완성 결과 렌더링
        renderSuggestions(suggestions, dropdownElement, inputElement, type, managerType) {
            // 이미 추가된 항목 제외
            const existingItems = preferenceManager[managerType];
            const filteredSuggestions = suggestions.filter(item => !existingItems.includes(item));

            if (filteredSuggestions.length === 0) {
                dropdownElement.classList.remove('active');
                return;
            }

            dropdownElement.innerHTML = filteredSuggestions.map((item, index) =>
                `<div class="autocomplete-item" data-index="${index}" data-value="${item}">${item}</div>`
            ).join('');

            dropdownElement.classList.add('active');
            this.currentFocus = -1;

            // 클릭 이벤트 추가
            dropdownElement.querySelectorAll('.autocomplete-item').forEach(item => {
                item.addEventListener('click', () => {
                    const value = item.getAttribute('data-value');
                    preferenceManager.add(managerType, value);
                    inputElement.value = '';
                    dropdownElement.classList.remove('active');
                });
            });
        },

        // 키보드 내비게이션
        handleKeyDown(e, dropdownElement, inputElement, managerType) {
            const items = dropdownElement.querySelectorAll('.autocomplete-item');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.currentFocus++;
                if (this.currentFocus >= items.length) this.currentFocus = 0;
                this.setActive(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.currentFocus--;
                if (this.currentFocus < 0) this.currentFocus = items.length - 1;
                this.setActive(items);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.currentFocus > -1 && items[this.currentFocus]) {
                    items[this.currentFocus].click();
                } else {
                    // 자동완성 없이 직접 입력
                    const value = inputElement.value.trim();
                    if (value) {
                        preferenceManager.add(managerType, value);
                        inputElement.value = '';
                        dropdownElement.classList.remove('active');
                    }
                }
            } else if (e.key === 'Escape') {
                dropdownElement.classList.remove('active');
            }
        },

        setActive(items) {
            items.forEach((item, index) => {
                if (index === this.currentFocus) {
                    item.classList.add('selected');
                } else {
                    item.classList.remove('selected');
                }
            });
        },

        // 자동완성 초기화
        initialize(inputId, dropdownId, type, managerType) {
            const inputElement = document.getElementById(inputId);
            const dropdownElement = document.getElementById(dropdownId);

            if (!inputElement || !dropdownElement) return;

            // input 이벤트
            inputElement.addEventListener('input', (e) => {
                const query = e.target.value.trim();

                if (!query) {
                    dropdownElement.classList.remove('active');
                    return;
                }

                this.debounce(async () => {
                    const suggestions = await this.fetchSuggestions(query, type);
                    this.renderSuggestions(suggestions, dropdownElement, inputElement, type, managerType);
                });
            });

            // keydown 이벤트
            inputElement.addEventListener('keydown', (e) => {
                if (dropdownElement.classList.contains('active')) {
                    this.handleKeyDown(e, dropdownElement, inputElement, managerType);
                }
            });

            // 외부 클릭 시 닫기
            document.addEventListener('click', (e) => {
                if (!inputElement.contains(e.target) && !dropdownElement.contains(e.target)) {
                    dropdownElement.classList.remove('active');
                }
            });
        }
    };

    // 선호도 리스트 관리 객체
    const preferenceManager = {
        preferredInstructors: [],
        avoidInstructors: [],
        preferredCourses: [],
        avoidCourses: [],

        add: function(type, value) {
            if (value && !this[type].includes(value)) {
                this[type].push(value);
                this.render(type);
            }
        },

        remove: function(type, value) {
            const index = this[type].indexOf(value);
            if (index > -1) {
                this[type].splice(index, 1);
                this.render(type);
            }
        },

        render: function(type) {
            const listId = type.replace(/([A-Z])/g, '-$1').toLowerCase() + '-list';
            const listElement = document.getElementById(listId);
            if (listElement) {
                listElement.innerHTML = this[type].map(item =>
                    `<span class="preference-item">${item}<span class="remove-btn" data-type="${type}" data-value="${item}">✕</span></span>`
                ).join('');
            }
        }
    };

    // 시간표 셀 생성 (3단계용)
    const tbody = document.getElementById("survey-tbody");
    for (let hour = 9; hour <= 18; hour++) {
        const row = document.createElement("tr");
        const timeCell = document.createElement("td");
        timeCell.textContent = `${hour}:00`;
        row.appendChild(timeCell);

        for (let day = 0; day < 5; day++) {
            const cell = document.createElement("td");
            cell.classList.add("survey-cell");
            cell.setAttribute("data-hour", hour);
            cell.setAttribute("data-day", day);
            cell.addEventListener("click", () => {
                cell.classList.toggle("selected");
            });
            row.appendChild(cell);
        }
        tbody.appendChild(row);
    }

    // 태그 선택 기능 (4단계용)
    document.querySelectorAll(".tag-options span").forEach(tag => {
        tag.addEventListener("click", () => {
            tag.classList.toggle("selected");
        });
    });

    // 자동완성 초기화
    autocompleteManager.initialize(
        'preferred-instructor-input',
        'preferred-instructor-autocomplete',
        'instructor',
        'preferredInstructors'
    );

    autocompleteManager.initialize(
        'avoid-instructor-input',
        'avoid-instructor-autocomplete',
        'instructor',
        'avoidInstructors'
    );

    autocompleteManager.initialize(
        'preferred-course-input',
        'preferred-course-autocomplete',
        'course',
        'preferredCourses'
    );

    autocompleteManager.initialize(
        'avoid-course-input',
        'avoid-course-autocomplete',
        'course',
        'avoidCourses'
    );

    // 선호도 항목 삭제 이벤트 (이벤트 위임)
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-btn')) {
            const type = e.target.getAttribute('data-type');
            const value = e.target.getAttribute('data-value');
            if (type && value) {
                preferenceManager.remove(type, value);
            }
        }
    });

    // "없음" 체크박스 선택 시 다른 요일 선택 해제
    const noneCheckbox = document.getElementById("none");
    const weekdayCheckboxes = document.querySelectorAll(".weekday-options input[type='checkbox']:not(#none)");
    
    noneCheckbox.addEventListener("change", () => {
        if (noneCheckbox.checked) {
            weekdayCheckboxes.forEach(cb => cb.checked = false);
        }
    });

    // 다른 요일 선택 시 "없음" 해제
    weekdayCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            if (cb.checked) {
                noneCheckbox.checked = false;
            }
        });
    });

    // 프로그레스 바와 단계 표시 업데이트
    function updateProgress() {
        const progress = ((currentStep + 1) / steps.length) * 100;
        progressFill.style.width = `${progress}%`;
        currentStepText.textContent = currentStep + 1;

        // 점 업데이트
        dots.forEach((dot, index) => {
            if (index < currentStep) {
                dot.classList.add("completed");
                dot.classList.remove("active");
            } else if (index === currentStep) {
                dot.classList.add("active");
                dot.classList.remove("completed");
            } else {
                dot.classList.remove("active", "completed");
            }
        });
    }

    // 버튼 상태 업데이트
    function updateButtons() {
        // 첫 단계면 이전 버튼 비활성화
        prevBtn.disabled = currentStep === 0;

        // 마지막 단계면 버튼 텍스트 변경
        if (currentStep === steps.length - 1) {
            nextBtn.innerHTML = "완료 ✓";
        } else {
            nextBtn.innerHTML = "다음 →";
        }
    }

    // 이전 버튼 클릭 처리
    prevBtn.addEventListener("click", () => {
        if (currentStep > 0) {
            steps[currentStep].classList.remove("active");
            currentStep--;
            steps[currentStep].classList.add("active");
            updateProgress();
            updateButtons();

            // 스크롤을 위로
            document.querySelector(".survey-container").scrollTop = 0;
        }
    });

    // 다음 버튼 클릭 처리
    nextBtn.addEventListener("click", () => {
        // 현재 단계 유효성 검사
        if (!validateCurrentStep()) {
            return;
        }

        if (currentStep < steps.length - 1) {
            // 다음 단계로 이동
            steps[currentStep].classList.remove("active");
            currentStep++;
            steps[currentStep].classList.add("active");
            updateProgress();
            updateButtons();

            // 스크롤을 위로
            document.querySelector(".survey-container").scrollTop = 0;
        } else {
            // 최종 제출
            submitSurvey();
        }
    });

    // 현재 단계 유효성 검사
    function validateCurrentStep() {
        switch (currentStep) {
            case 0: // 1단계: 학점 입력
                const majorCredit = document.getElementById("major-credit-input").value;
                const electiveCredit = document.getElementById("elective-credit-input").value;
                
                if (!majorCredit || !electiveCredit) {
                    alert("전공 학점과 교양 학점을 모두 입력해주세요.");
                    return false;
                }
                
                if (majorCredit < 0 || majorCredit > 24 || electiveCredit < 0 || electiveCredit > 24) {
                    alert("학점은 0-24 사이의 값을 입력해주세요.");
                    return false;
                }
                break;
                
            case 1: // 2단계: 공강 요일 선택
                const checkedDays = document.querySelectorAll(".weekday-options input[type='checkbox']:checked");
                if (checkedDays.length === 0) {
                    alert("희망하는 공강 요일을 선택해주세요.");
                    return false;
                }
                break;
                
            case 2: // 3단계: 제외 시간 선택 (선택사항)
                // 이 단계는 선택사항이므로 유효성 검사 없음
                break;
                
            case 3: // 4단계: 교양 과목 특징 선택 (선택사항)
                // 이 단계는 선택사항이므로 유효성 검사 없음
                break;

            case 4: // 5단계: 선호 교수 (선택사항)
            case 5: // 6단계: 기피 교수 (선택사항)
            case 6: // 7단계: 선호 과목 (선택사항)
            case 7: // 8단계: 기피 과목 (선택사항)
            case 8: // 9단계: 시간표 스타일 (선택사항)
                // 모두 선택사항이므로 유효성 검사 없음
                break;
        }
        return true;
    }

    // 설문조사 제출
    function submitSurvey() {
        const major = document.getElementById("major-credit-input").value;
        const elective = document.getElementById("elective-credit-input").value;
        const freeDays = Array.from(document.querySelectorAll(".weekday-options input:checked")).map(cb => cb.value);
        const blocked = Array.from(document.querySelectorAll(".survey-cell.selected")).map(cell => ({
            day: parseInt(cell.dataset.day),
            hour: parseInt(cell.dataset.hour)
        }));
        const tags = Array.from(document.querySelectorAll(".tag-options span.selected")).map(tag => tag.textContent);

        // 시간표 스타일 선호도
        const maxWalkingTime = parseInt(document.getElementById('max-walking-time').value) || 10;
        const preferCompact = document.querySelector('input[name="compact"]:checked')?.value === 'yes';
        const preferMorning = document.getElementById('prefer-morning')?.checked || false;
        const preferAfternoon = document.getElementById('prefer-afternoon')?.checked || false;
        const optimizationLevel = document.querySelector('input[name="optimization"]:checked')?.value || 'ADVANCED';

        const surveyData = {
            majorCredit: parseInt(major),
            electiveCredit: parseInt(elective),
            freeDays: freeDays,
            blockedTimes: blocked,
            preferenceTags: tags,  // 변경: preferences -> preferenceTags
            preferredInstructors: preferenceManager.preferredInstructors,
            avoidInstructors: preferenceManager.avoidInstructors,
            preferredCourses: preferenceManager.preferredCourses,
            avoidCourses: preferenceManager.avoidCourses,
            maxWalkingTime: maxWalkingTime,
            preferCompact: preferCompact,
            preferMorning: preferMorning,
            preferAfternoon: preferAfternoon,
            optimizationLevel: optimizationLevel
        };

        console.log("설문조사 결과:", surveyData);
        
        // 설문조사 오버레이 닫기
        document.getElementById("survey-overlay").style.display = "none";
        
        // 즉시 시간표 생성 시작
        console.log("설문조사 완료 - 시간표 생성 시작");
        startTimetableGeneration(surveyData);
    }

    // 설문조사 오버레이 열기 함수 (전역 함수로 노출)
    window.showSurvey = function() {
        // 초기 상태로 리셋
        currentStep = 0;
        steps.forEach((step, index) => {
            if (index === 0) {
                step.classList.add("active");
            } else {
                step.classList.remove("active");
            }
        });
        updateProgress();
        updateButtons();

        // 스크롤을 위로
        document.querySelector(".survey-container").scrollTop = 0;

        document.getElementById("survey-overlay").style.display = "flex";
    };

    // 설문조사 오버레이 닫기 함수 (전역 함수로 노출)
    window.hideSurvey = function() {
        document.getElementById("survey-overlay").style.display = "none";
    };

    // 설문조사 완료 후 시간표 생성 시작 함수
    function startTimetableGeneration(surveyData) {
        console.log('설문조사 데이터로 시간표 생성 시작:', surveyData);
        
        // 설문조사 데이터를 시간표 생성 제약조건으로 변환
        const convertedConstraints = {
            major_credits: surveyData.majorCredit || 0,
            elective_credits: surveyData.electiveCredit || 0,
            free_days: surveyData.freeDays || [],
            specific_avoid_times: [], // blockedTimes를 변환하여 저장
            is_modification: false, // 새로운 시간표 생성
            required_courses: [],
            exclude_courses: [],
            avoid_times: [],
            avoid_time_ranges: [],
            only_time_ranges: [],
            specific_avoid_time_ranges: [],
            existing_courses: [],
            // 선호도 관련 파라미터 추가
            preferred_instructors: surveyData.preferredInstructors || [],
            avoid_instructors: surveyData.avoidInstructors || [],
            preferred_courses: surveyData.preferredCourses || [],
            avoid_courses: surveyData.avoidCourses || [],
            max_walking_time: surveyData.maxWalkingTime || 10,
            prefer_compact: surveyData.preferCompact || false,
            prefer_morning: surveyData.preferMorning || false,
            prefer_afternoon: surveyData.preferAfternoon || false,
            preference_tags: surveyData.preferenceTags || [],  // 태그 추가
            optimization_level: surveyData.optimizationLevel || 'ADVANCED'  // 최적화 수준 추가
        };

        // 제외할 시간(blockedTimes)을 specific_avoid_times 형식으로 변환
        if (surveyData.blockedTimes && surveyData.blockedTimes.length > 0) {
            const dayMapping = {
                0: '월',
                1: '화', 
                2: '수',
                3: '목',
                4: '금'
            };
            
            surveyData.blockedTimes.forEach(blockedTime => {
                if (blockedTime.day !== undefined && blockedTime.hour !== undefined) {
                    const dayName = dayMapping[blockedTime.day];
                    if (dayName) {
                        convertedConstraints.specific_avoid_times.push({
                            day: dayName,
                            hour: blockedTime.hour
                        });
                    }
                }
            });
        }

        console.log('변환된 제약조건:', convertedConstraints);

        // 설문조사 오버레이 닫기
        hideSurvey();

        // requestTimetableAction 커스텀 이벤트 발생
        // main.js의 setupSseConnection이 자동으로 progress-overlay를 관리함
        document.dispatchEvent(new CustomEvent('requestTimetableAction', {
            detail: convertedConstraints
        }));

        // 시간표 생성 완료 후 피드백 메시지 표시
        document.addEventListener('timetableRendered', function onTimetableRendered(e) {
            if (e.detail.timetable && e.detail.timetable.courses.length > 0) {
                // 한 번만 실행되도록 이벤트 리스너 제거
                document.removeEventListener('timetableRendered', onTimetableRendered);

                // 설문조사 기반으로 생성된 시간표에 대한 피드백 메시지
                if (window.showBotMessage) {
                    window.showBotMessage(`설문조사 응답을 바탕으로 ${e.detail.timetable.courses.length}개의 강의로 구성된 시간표를 생성했습니다! 마음에 드시나요?`);
                }
            }
        });
    }

    // 설문조사용 진행 메시지 표시 함수
    function showSurveyProgressMessage(message, isSuccess = true) {
        const overlay = document.getElementById('progress-overlay');
        const messageText = document.getElementById('progress-text');
        const progressBar = document.getElementById('progress-bar');
        const progressCount = document.getElementById('progress-count');
        
        if (overlay && messageText) {
            // 메시지 설정
            messageText.textContent = message;
            
            // 진행 바 숨기고 카운트 텍스트도 숨김
            if (progressBar) progressBar.style.display = 'none';
            if (progressCount) progressCount.style.display = 'none';
            
            // 오버레이 표시
            overlay.style.display = 'block';
            
            // 1초 후 자동으로 사라짐
            setTimeout(() => {
                overlay.style.display = 'none';
                // 다시 진행 바와 카운트 표시 (다음 시간표 생성을 위해)
                if (progressBar) progressBar.style.display = 'block';
                if (progressCount) progressCount.style.display = 'block';
            }, 1000);
        }
    }
}); 