// home/js/timetable/left_panel.js

// 외부 모듈에서 필요한 함수와 DOM 요소를 가져옵니다.
import { getCategoryDOMElements, getSelectedCategoryId } from "../dropdown/category_dropdown.js";
import { getOrgDOMElements } from '../dropdown/org_dropdown.js';

document.addEventListener('DOMContentLoaded', () => {
    // 각 모듈에서 필요한 DOM 요소를 가져옵니다.
    const $categoryElements = getCategoryDOMElements();
    const $orgElements = getOrgDOMElements();

    // left_panel.js가 직접 사용하는 DOM 요소를 캐싱합니다.
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
            renderCourseList(data);
        } catch (error) {
            $panelElements.courseListBody.innerHTML = `<tr><td colspan="4" class="text-danger text-center py-3">오류: ${error}</td></tr>`;
        }
    }

    /**
     * 검색 결과를 테이블에 렌더링합니다.
     * @param {Array<Object>} courses 검색된 강의 목록.
     */
    function renderCourseList(courses) {
        $panelElements.courseListBody.innerHTML = '';

        if (!courses || courses.length === 0) {
            $panelElements.courseListBody.innerHTML = '<tr><td colspan="4" class="text-center py-3">검색 결과가 없습니다.</td></tr>';
            return;
        }

        courses.forEach(course => {
            const tr = document.createElement('tr');
            tr.className = 'search-row course-block';
            tr.style.cursor = 'pointer';
            tr.dataset.courseId = course.course_id;

            tr.innerHTML = `
                <td class="fw-bold">${course.course_name}</td>
                <td>${course.instructor_name || '-'}</td>
                <td>${(course.schedules || []).map(s => `${s.day} ${s.times}`).join('<br>')}</td>
                <td class="text-center">${course.credits}</td>
            `;

            tr.addEventListener('click', () => fetchCourseSummaryAndShowPopup(course));
            $panelElements.courseListBody.appendChild(tr);
        });
    }

    /**
     * 강의 요약을 가져와 강의 팝업을 표시합니다.
     * @param {Object} courseData 기본 강의 정보.
     */
    async function fetchCourseSummaryAndShowPopup(courseData) {
        try {
            const response = await fetch(`/data-manager/course/${courseData.course_id}/summary/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const summary = await response.json();
            showCoursePopup({ ...courseData, ...summary });
        } catch (error) {
            alert('강의 요약을 불러오지 못했습니다: ' + error);
        }
    }

    /**
     * 강의 상세 정보를 표시하는 팝업을 띄웁니다.
     * @param {Object} data 강의 상세 데이터.
     */
    function showCoursePopup(data) {
        const modal = bootstrap.Modal.getOrCreateInstance($panelElements.coursePopup);

        $panelElements.popupTitle.textContent = data.course_name;
        $panelElements.popupCode.textContent = data.course_code;
        $panelElements.popupSection.textContent = data.section;
        $panelElements.popupYear.textContent = data.target_year;
        $panelElements.popupCredits.textContent = data.credits;
        $panelElements.popupInstructor.textContent = data.instructor_name;
        $panelElements.popupGroup.textContent = data.group_activity === 'Y' ? '있음' : '없음';
        $panelElements.popupSchedules.innerHTML = (data.schedules || [])
            .map(s => `${s.day} ${s.times} (${s.location || '-'})`)
            .join('<br>');
        $panelElements.popupSummary.textContent = data.course_summary || '(요약 정보 없음)';

        setupAddToTimetableButton(data);
        setupViewReviewsButton(data);

        modal.show();
    }

    /**
     * 팝업 내 '시간표에 추가' 버튼을 설정합니다.
     * @param {Object} courseData 시간표에 추가할 강의 데이터.
     */
    function setupAddToTimetableButton(courseData) {
        // .cloneNode(true)와 replaceChild를 사용하여 기존 이벤트 리스너를 효과적으로 제거합니다.
        const oldBtn = document.getElementById('add-to-timetable-btn-popup');
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);

        newBtn.textContent = '시간표에 추가';
        newBtn.disabled = false;

        newBtn.onclick = function() {
            const event = new CustomEvent('addCourseToTimetable', {
                detail: {
                    course_id: String(courseData.course_id),
                    course_name: courseData.course_name,
                    credits: courseData.credits,
                    schedules: courseData.schedules || [],
                }
            });
            document.dispatchEvent(event);

            this.textContent = '추가됨';
            this.disabled = true;
        };
    }

    /**
     * 팝업 내 '강의 평가 보기' 버튼을 설정합니다.
     * @param {Object} courseData 강의 평가를 볼 강의 데이터.
     */
    function setupViewReviewsButton(courseData) {
        const oldBtn = $panelElements.viewReviewsButton;
        const newBtn = oldBtn.cloneNode(true);
        oldBtn.parentNode.replaceChild(newBtn, oldBtn);

        newBtn.addEventListener('click', () => {
            const { course_code, instructor_name } = courseData;
            if (course_code && instructor_name) {
                const params = new URLSearchParams({ course_code, instructor_name });
                window.location.href = `/reviews/?${params.toString()}`;
            } else {
                alert('강의 코드 또는 교수자 정보가 없어 강의 평가를 볼 수 없습니다.');
            }
        });
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