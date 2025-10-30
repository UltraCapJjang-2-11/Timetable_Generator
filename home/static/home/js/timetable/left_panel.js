import { Course } from "../models/Course.js";
import { initializeCategoryDropdowns, buildCategorySearchParams } from "../dropdown/category_dropdown.js";
import { timetableState } from "./state.js";

// 자동완성 관리자
const searchAutocompleteManager = {
    currentFocus: -1,
    debounceTimer: null,
    inputElement: null,
    dropdownElement: null,

    async fetchSuggestions(query) {
        if (!query || query.length < 1) return { courses: [], instructors: [] };

        try {
            // 강의명과 교수명 자동완성을 동시에 가져옴
            const [coursesRes, instructorsRes] = await Promise.all([
                fetch(`/api/autocomplete/courses/?q=${encodeURIComponent(query)}`),
                fetch(`/api/autocomplete/instructors/?q=${encodeURIComponent(query)}`)
            ]);

            const coursesData = await coursesRes.json();
            const instructorsData = await instructorsRes.json();

            return {
                courses: (coursesData.results || []).slice(0, 5),
                instructors: (instructorsData.results || []).slice(0, 5)
            };
        } catch (error) {
            console.error('자동완성 데이터 로드 실패:', error);
            return { courses: [], instructors: [] };
        }
    },

    renderDropdown(data) {
        this.dropdownElement.innerHTML = '';

        const { courses, instructors } = data;
        const hasResults = courses.length > 0 || instructors.length > 0;

        if (!hasResults) {
            this.dropdownElement.classList.remove('active');
            return;
        }

        // 강의명 결과
        if (courses.length > 0) {
            const courseHeader = document.createElement('div');
            courseHeader.className = 'autocomplete-header';
            courseHeader.textContent = '강의명';
            this.dropdownElement.appendChild(courseHeader);

            courses.forEach(course => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.innerHTML = `
                    <span class="autocomplete-text">${course}</span>
                    <span class="autocomplete-tag course-tag">강의</span>
                `;
                item.addEventListener('click', () => this.selectItem(course));
                this.dropdownElement.appendChild(item);
            });
        }

        // 교수명 결과
        if (instructors.length > 0) {
            const instructorHeader = document.createElement('div');
            instructorHeader.className = 'autocomplete-header';
            instructorHeader.textContent = '교수명';
            this.dropdownElement.appendChild(instructorHeader);

            instructors.forEach(instructor => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.innerHTML = `
                    <span class="autocomplete-text">${instructor}</span>
                    <span class="autocomplete-tag instructor-tag">교수</span>
                `;
                item.addEventListener('click', () => this.selectItem(instructor));
                this.dropdownElement.appendChild(item);
            });
        }

        this.dropdownElement.classList.add('active');
        this.currentFocus = -1;
    },

    selectItem(value) {
        this.inputElement.value = value;
        this.dropdownElement.classList.remove('active');
        this.dropdownElement.innerHTML = '';
    },

    handleKeyDown(e) {
        const items = this.dropdownElement.querySelectorAll('.autocomplete-item');
        if (!items.length) return;

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
            }
        } else if (e.key === 'Escape') {
            this.dropdownElement.classList.remove('active');
            this.dropdownElement.innerHTML = '';
        }
    },

    setActive(items) {
        items.forEach((item, index) => {
            if (index === this.currentFocus) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    },

    initialize(inputId, dropdownId) {
        this.inputElement = document.getElementById(inputId);
        this.dropdownElement = document.getElementById(dropdownId);

        if (!this.inputElement || !this.dropdownElement) {
            console.warn(`자동완성 초기화 실패: ${inputId}, ${dropdownId}`);
            return;
        }

        this.inputElement.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            clearTimeout(this.debounceTimer);

            if (!query) {
                this.dropdownElement.classList.remove('active');
                this.dropdownElement.innerHTML = '';
                return;
            }

            this.debounceTimer = setTimeout(async () => {
                const data = await this.fetchSuggestions(query);
                this.renderDropdown(data);
            }, 300);
        });

        this.inputElement.addEventListener('keydown', (e) => this.handleKeyDown(e));

        // 외부 클릭 시 드롭다운 닫기
        document.addEventListener('click', (e) => {
            if (!this.inputElement.contains(e.target) && !this.dropdownElement.contains(e.target)) {
                this.dropdownElement.classList.remove('active');
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // 드롭다운 초기화
    try { initializeCategoryDropdowns(); } catch (_) {}

    // 자동완성 초기화
    searchAutocompleteManager.initialize('course_name_search', 'course-search-autocomplete');

    // DOM 요소 캐싱
    const $panelElements = {
        courseNameSearch: document.getElementById('course_name_search'),
        searchButton: document.getElementById('search-button'),
        courseListBody: document.getElementById('course-list-body'),
        coursePopup: document.getElementById('course-popup'),
        popupTitle: document.getElementById('popup-title'),
        popupCode: document.getElementById('popup-code'),
        popupSection: document.getElementById('popup-section'),
        popupYear: document.getElementById('popup-year'),
        popupCredits: document.getElementById('popup-credits'),
        popupInstructor: document.getElementById('popup-instructor'),
        popupGroup: document.getElementById('popup-group'),
        popupSchedules: document.getElementById('popup-schedules'),
        popupSummary: document.getElementById('popup-summary'),
        popupFooter: document.getElementById('course-popup')?.querySelector('.modal-footer'),
        viewReviewsButton: document.getElementById('view-reviews-button')
    };

    /**
     * 강의 검색을 수행하고 결과를 표시합니다.
     */
    async function performSearch() {
        // 공용 드롭다운 유틸을 통해 검색 파라미터 구성
        const params = buildCategorySearchParams();
        if (!params.get('category_id') && !params.get('course_name')) {
            alert('교과목 분류를 선택하거나 강의명을 입력하세요.');
            return;
        }

        const url = `/course/search/?${params.toString()}&year=2025&term=1학기`;

        // 로딩 표시 개선
        $panelElements.courseListBody.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-warning pulse" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">검색 중...</span>
                </div>
                <p class="mt-3 text-muted fade-in">강의를 검색하고 있습니다...</p>
                <div class="loading-dots mt-2">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
        `;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            const courses = Course.createFromApiData(data);
            renderCourseList(courses);

            // 결과 개수 업데이트 애니메이션
            const resultCount = document.getElementById('result-count');
            if (resultCount) {
                resultCount.classList.add('bounce-in');
                resultCount.textContent = courses.length;
                setTimeout(() => resultCount.classList.remove('bounce-in'), 750);
            }
        } catch (error) {
            $panelElements.courseListBody.innerHTML = `
                <div class="alert alert-danger m-3" role="alert">
                    <strong>오류 발생!</strong><br>
                    ${error.message}
                </div>
            `;
        }
    }

    /**
     * 검색 결과를 Bootstrap 그리드 기반의 카드로 렌더링합니다.
     * @param {Array<Course>} courses 검색된 Course 객체 목록.
     */
    function renderCourseList(courses) {
        const container = $panelElements.courseListBody;
        container.innerHTML = '';

        if (!courses || courses.length === 0) {
            container.innerHTML = '<p class="text-center py-3">검색 결과가 없습니다.</p>';
            return;
        }

        courses.forEach(course => {
            const courseItem = document.createElement('div');
            courseItem.className = 'course-item fade-in-up';
            courseItem.dataset.courseId = course.id;

            const scheduleHtml = course.schedules.map(s => `
                <div class="schedule-entry">
                    <span><strong>${s.day}</strong> | ${s.times.join(',')}교시 | ${s.location || '장소 미정'}</span>
                </div>
            `).join('');

            courseItem.innerHTML = `
                <div class="row align-items-center">
                    <div class="col-md-10">
                        <div class="course-item-content">
                            <div class="course-info">
                                <div class="course-title-line">
                                    <span class="course-name">${course.name}</span>
                                    <span class="course-code">(${course.code}-${course.section})</span>
                                    <span class="bg-success-subtle text-secondary-emphasis fw-bold" disabled style="font-size:1.0rem">${course.targetYear}</span>
                                </div>
                                <div class="course-detail-line">
                                    <span class="professor-name bg-secondary-subtle text-secondary-emphasis">${course.instructor || '미지정'}</span>
                                    <span class="credits-info bg-secondary-subtle text-secondary-emphasis">${course.credits}학점</span>
                                    <span class="category-info bg-secondary-subtle text-secondary-emphasis">${course.categoryName}</span>
                                    <span class="semester-info bg-secondary-subtle text-secondary-emphasis">${course.semester}</span>
                                </div>
                            </div>
                            ${scheduleHtml ? `<div class="course-item-schedule">${scheduleHtml}</div>` : ''}
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="course-item-actions">
                            <button class="add-course-btn" title="시간표에 추가">+</button>
                            <button class="details-btn" title="상세 정보 보기">ⓘ</button>
                        </div>
                    </div>
                </div>
            `;

            // 새로운 간단한 미리보기 시스템
            // 디바운싱을 위한 타이머
            let hoverTimer;

            courseItem.addEventListener('mouseenter', () => {
                // 짧은 지연 후 미리보기 표시 (깜빡임 방지)
                hoverTimer = setTimeout(() => {
                    document.dispatchEvent(new CustomEvent('clearAllPreviews'));
                    document.dispatchEvent(new CustomEvent('showCoursePreview', {
                        detail: { course: course.toObject() }
                    }));
                }, 100);
            });

            courseItem.addEventListener('mouseleave', (e) => {
                // 타이머 취소
                if (hoverTimer) {
                    clearTimeout(hoverTimer);
                    hoverTimer = null;
                }

                const relatedTarget = e.relatedTarget;
                const isMovingToTimetable = relatedTarget && (
                    relatedTarget.closest('.middle-panel') ||
                    relatedTarget.closest('.timetable')
                );
                const isMovingToOtherCourse = relatedTarget &&
                    relatedTarget.closest('.course-item');

                if (!isMovingToTimetable && !isMovingToOtherCourse) {
                    document.dispatchEvent(new CustomEvent('hideCoursePreview', {
                        detail: { course: course.toObject() }
                    }));
                }
            });

            // 이벤트 리스너 할당 로직은 이전과 동일하게 유지됩니다.
            const addBtn = courseItem.querySelector('.add-course-btn');
            const detailsBtn = courseItem.querySelector('.details-btn');

            addBtn.addEventListener('click', (e) => {
                e.stopPropagation();

                // 리플 효과 추가
                const ripple = document.createElement('span');
                ripple.className = 'ripple';
                addBtn.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);

                course.isPinned = true;
                document.dispatchEvent(new CustomEvent('addCourseToView', {
                    detail: { course: course }
                }));

                addBtn.textContent = '✓';
                addBtn.disabled = true;
                courseItem.classList.add('selected');

                setTimeout(() => {
                    addBtn.textContent = '+';
                    addBtn.disabled = false;
                }, 1000);
            });

            detailsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fetchCourseSummaryAndShowPopup(course);
            });

            container.appendChild(courseItem);
        });
    }

    /**
     * 강의 요약을 가져와 강의 팝업을 표시합니다.
     * @param {Course} course 기본 강의 정보.
     */
    async function fetchCourseSummaryAndShowPopup(course) {
        try {
            const response = await fetch(`/data-manager/course/${course.id}/summary/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const summary = await response.json();

            // 원본 Course 객체의 데이터와 요약 정보를 합쳐 팝업에 전달
            showCoursePopup(course, summary);
        } catch (error) {
            alert('강의 요약을 불러오지 못했습니다: ' + error);
        }
    }

    /**
     * 강의 상세 정보를 표시하는 팝업을 띄웁니다.
     *  @param {Course} course 상세 정보를 표시할 Course 객체.
     *  @param {Object} summary 추가적인 요약 정보 (예: course_summary).
     */
    function showCoursePopup(course, summary) {
        const modal = bootstrap.Modal.getOrCreateInstance($panelElements.coursePopup);

        // Course 객체의 속성과 메서드를 사용하여 팝업 내용을 채웁니다.
        $panelElements.popupTitle.textContent = course.name;
        $panelElements.popupCode.textContent = course.code;
        $panelElements.popupSection.textContent = course.section;
        $panelElements.popupYear.textContent = course.targetYear;
        $panelElements.popupCredits.textContent = course.credits;
        $panelElements.popupInstructor.textContent = course.instructor;
        $panelElements.popupGroup.textContent = course.group_activity === 'Y' ? '있음' : '없음'; // 이 속성이 Course 클래스에 있다면
        $panelElements.popupSchedules.innerHTML = course.getScheduleString().replace(/<br>/g, ' / '); // 팝업에서는 다른 포맷으로
        $panelElements.popupSummary.textContent = summary.course_summary || '(요약 정보 없음)';

        setupAddToTimetableButton(course); // Course 객체 전달
        setupViewReviewsButton(course);   // Course 객체 전달

        modal.show();
    }

    /**
     * 팝업 내 '시간표에 추가/제거' 버튼을 설정합니다.
     * @param {Course} course 시간표에 추가/제거할 강의 데이터.
     */
    function setupAddToTimetableButton(course) {
        const addBtn = document.getElementById('add-to-timetable-btn-popup');

        const isAdded = timetableState.currentTimetable?.courses.some(c => c.id === course.id) || false;
        const isConflict = timetableState.currentTimetable?.courses.some(c => c.conflictsWith(course)) || false;

        if (isAdded) {
            addBtn.textContent = '시간표에서 제거';
            addBtn.style.backgroundColor = '#dc3545';
            addBtn.disabled = false;

            addBtn.onclick = function() {
                document.dispatchEvent(new CustomEvent('removeCourseFromView', {
                    detail: { courseId: course.id }
                }));
                bootstrap.Modal.getInstance(document.getElementById('course-popup'))?.hide();
            };
        }
        else if (isConflict) {
            addBtn.textContent = '시간이 겹치는 강의';
            addBtn.style.backgroundColor = '#dc3545';
            addBtn.disabled = true;
        }
        else {
            addBtn.textContent = '시간표에 추가';
            addBtn.style.backgroundColor = '#007bff';
            addBtn.disabled = false;

            addBtn.onclick = function() {
                course.isPinned = true // 시간표에 고정
                document.dispatchEvent(new CustomEvent('addCourseToView', {
                    detail: { course: course }
                }));
                this.textContent = '추가됨';
                this.disabled = true;
            };
        }
    }

    /**
     * 팝업 내 '강의 평가 보기' 버튼을 설정합니다.
     * @param {Course} course 강의 평가를 볼 Course 객체.
     */
    function setupViewReviewsButton(course) {
        const viewBtn = $panelElements.viewReviewsButton;
        viewBtn.onclick = () => { // 이전 리스너가 누적되지 않도록 onclick으로 재할당
            if (course.code) {
                const params = new URLSearchParams({
                    course_code: course.code,
                    instructor_name: course.instructor || ''
                });
                window.open(`/reviews/?${params.toString()}`, '_blank'); // 새 탭에서 열기
            } else {
                alert('강의 코드가 없어 강의 평가를 볼 수 없습니다.');
            }
        };
    }

    /**
     * 검색 필터를 초기화합니다.
     */
    function resetSearchFilters() {
        // 카테고리 드롭다운 초기화
        const categoryRoot = document.getElementById('category_root');
        const categoryChild = document.getElementById('category_child');
        const categoryGrandchild = document.getElementById('category_grandchild');
        const childContainer = document.getElementById('child-container');
        const grandchildContainer = document.getElementById('grandchild-container');
        const orgContainer = document.getElementById('org-container');

        if (categoryRoot) categoryRoot.value = '';
        if (categoryChild) {
            categoryChild.value = '';
            categoryChild.disabled = true;
        }
        if (categoryGrandchild) {
            categoryGrandchild.value = '';
            categoryGrandchild.disabled = true;
        }
        if (childContainer) childContainer.style.display = 'none';
        if (grandchildContainer) grandchildContainer.style.display = 'none';
        if (orgContainer) orgContainer.style.display = 'none';

        // 학과 드롭다운 초기화
        const college = document.getElementById('college');
        const dept = document.getElementById('dept');
        if (college) college.value = '';
        if (dept) {
            dept.value = '';
            dept.disabled = true;
        }

        // 강의명 검색 입력 초기화
        if ($panelElements.courseNameSearch) {
            $panelElements.courseNameSearch.value = '';
        }

        // 결과 영역 초기화
        $panelElements.courseListBody.innerHTML = `
            <div class="text-center text-muted py-4">
                <i>검색 조건을 선택하고 검색 버튼을 클릭하세요</i>
            </div>
        `;

        // 결과 개수 초기화
        const resultCount = document.getElementById('result-count');
        if (resultCount) {
            resultCount.textContent = '0';
        }
    }

    // --- 이벤트 리스너 등록 ---
    const resetButton = document.getElementById('reset-button');

    if ($panelElements.searchButton) {
        $panelElements.searchButton.addEventListener('click', performSearch);
    }

    if (resetButton) {
        resetButton.addEventListener('click', resetSearchFilters);
    }

    // Enter 키로도 검색 가능하도록
    if ($panelElements.courseNameSearch) {
        $panelElements.courseNameSearch.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                performSearch();
            }
        });
    }

    // 페이지 로드 시 애니메이션
    document.querySelectorAll('.search-section-header, .category-dropdown-section, .search-input-section, .button-section, .survey-section').forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        setTimeout(() => {
            el.style.transition = 'all 0.5s ease';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 100);
    });
});