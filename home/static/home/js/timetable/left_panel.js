import { Course } from "../models/Course.js";
import { getCategoryDOMElements, getSelectedCategoryId } from "../dropdown/category_dropdown.js";
import { getOrgDOMElements } from '../dropdown/org_dropdown.js';
import { timetableState } from "./state.js";

document.addEventListener('DOMContentLoaded', () => {
    // 각 모듈에서 필요한 DOM 요소를 가져옵니다.
    const $categoryElements = getCategoryDOMElements();
    const $orgElements = getOrgDOMElements();

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
        // category_dropdown.js에서 선택된 카테고리 ID를 가져옵니다.
        const categoryId = getSelectedCategoryId();
        const courseName = $panelElements.courseNameSearch ? $panelElements.courseNameSearch.value.trim() : '';

        if (!categoryId && !courseName) {
            alert('교과목 분류를 선택하거나 강의명을 입력하세요.');
            return;
        }

        const collegeName = $orgElements.orgCollege?.value.trim();
        const deptName = $orgElements.orgDept?.value.trim();

        const params = new URLSearchParams();
        if (categoryId) params.append('category_id', categoryId);
        if (courseName) params.append('course_name', courseName);
        if (collegeName) params.append('college_name', collegeName);
        if (deptName) params.append('dept_name', deptName);

        const url = `/course/search/?${params.toString()}`;
        $panelElements.courseListBody.innerHTML = '<tr><td colspan="4" class="text-center py-3">검색 중…</td></tr>';

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            const courses = Course.createFromApiData(data);
            renderCourseList(courses);
        } catch (error) {
            $panelElements.courseListBody.innerHTML = `<tr><td colspan="4" class="text-danger text-center py-3">오류: ${error}</td></tr>`;
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
            courseItem.className = 'course-item';
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

            courseItem.addEventListener('mouseenter', () => {
                document.dispatchEvent(new CustomEvent('previewCourse', {
                    detail: { course: course.toObject() }
                }));
            });

            // 마우스가 강의 카드에서 나갔을 때
            courseItem.addEventListener('mouseleave', () => {
                document.dispatchEvent(new CustomEvent('clearPreview'));
            });

            // 이벤트 리스너 할당 로직은 이전과 동일하게 유지됩니다.
            const addBtn = courseItem.querySelector('.add-course-btn');
            const detailsBtn = courseItem.querySelector('.details-btn');



            addBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                document.dispatchEvent(new CustomEvent('addCourseToView', {
                    detail: { course: course }
                }));

                addBtn.textContent = '✓';
                addBtn.disabled = true;
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

    // --- 이벤트 리스너 등록 ---
    $panelElements.searchButton.addEventListener('click', performSearch);
    // Enter 키로도 검색 가능하도록
    $panelElements.courseNameSearch.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            performSearch();
        }
    });
});