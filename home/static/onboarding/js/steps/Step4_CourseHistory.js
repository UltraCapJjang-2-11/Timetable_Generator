/**
 * 온보딩 Step 4 - 이수내역 관리 단계 UI 로직.
 * - 중앙 상태(`getCourseHistory`)의 강의 목록을 기반으로 학기/과목 리스트와 GPA 요약을 렌더링합니다.
 * - 학기를 추가하는 모달과 강의 검색 모달(`CourseSearchModal`)을 초기화합니다.
 * - PDF 이미지가 있으면 모달에서 `PdfViewer`로 이수내역 이미지를 미리봅니다.
 * - 이전/다음 내비게이션 시 `step-previous`/`step-success` 이벤트를 발행합니다.
 */

import { getCourseHistory, updateCourseHistory, getImageUrls } from '../state.js';
import { calculateGpa } from '../utils/gpa.js';
import { PdfViewer } from '../components/PdfViewer.js';
import { CourseSearchModal } from '../components/CourseSearchModal.js';

/**
 * @typedef {Object} CourseEntry
 * @property {number|null} [course_id]
 * @property {number} year
 * @property {string} term
 * @property {string} course_code
 * @property {string} course_name
 * @property {number} credit
 * @property {string} course_type
 * @property {string} grade
 * @property {boolean} [__placeholder] - 렌더링 대상에서 제외되는 자리표시 항목
 */

let allCourses = [];
let activeSemester = null;
let viewer = null; // 모달 내 뷰어 인스턴스
let containerRef = null;
let courseModal = null;

/**
 * Step 4 컴포넌트를 초기화하고 화면을 렌더링합니다.
 * - 학기/요약 렌더링, 학기 추가 모달/강의 검색 모달 초기화, PDF 뷰어 모달 설정.
 * - 이전/다음 버튼 이벤트 바인딩.
 * @param {HTMLElement} container - 스텝 루트 컨테이너
 */
export function mount(container) {
    containerRef = container;
    // 중앙 상태에서 초기 이수내역 불러오기
    allCourses = getCourseHistory();

    renderSemesterList();
    renderOverallSummary();

    const semesterItems = document.querySelectorAll('#semester-list .list-group-item');
    if (semesterItems.length > 0) {
        semesterItems[0].click();
    }

    // 모달 관련 기능 바인딩 (학기 추가)
    populateYearOptions();
    bindAddSemesterModal();

    // 강의 검색 모달 컴포넌트 초기화
    const addCourseModalEl = document.getElementById('add-course-modal');
    courseModal = new CourseSearchModal(addCourseModalEl);

    // PDF 뷰어 모달 초기화
    const historyModal = document.getElementById('course-history-modal');

    historyModal?.addEventListener('show.bs.modal', () => {
        const viewerContainer = historyModal.querySelector('#pdf-viewer-container');
        if (viewer && viewer.destroy) viewer.destroy();
        viewer = new PdfViewer(viewerContainer);
        const urls = getImageUrls();
        const img = urls?.course_history ? [urls.course_history] : [];
        viewer.init(img);
    });
    
    historyModal?.addEventListener('hidden.bs.modal', () => {
        if (viewer && viewer.destroy) viewer.destroy();
        viewer = null;
    });

    // 내비게이션 버튼 이벤트
    container.querySelector('.prev-btn')?.addEventListener('click', () => {
        container.dispatchEvent(new CustomEvent('step-previous', { bubbles: true }));
    });
    container.querySelector('.next-btn')?.addEventListener('click', () => {
        // 중앙 상태에 반영 후 성공 이벤트
        updateCourseHistory(allCourses);
        container.dispatchEvent(new CustomEvent('step-success', { detail: { courses: allCourses }, bubbles: true }));
    });

    // 이 학기에 강의 추가 버튼 → 코스 검색 모달 표시
    const addCourseBtn = document.getElementById('add-course-btn');
    addCourseBtn?.addEventListener('click', (e) => {
        if (!activeSemester) {
            e.preventDefault();
            e.stopPropagation();
            alert('먼저 왼쪽에서 학기를 선택하세요.');
            return;
        }
        courseModal.show({
            activeSemester,
            existingCourses: allCourses,
            onConfirm: (newlySelected) => {
                const [yStr, term] = activeSemester.split('년 ');
                const year = parseInt(yStr, 10);
                newlySelected.forEach(c => {
                    allCourses.push({
                        course_id: c.course_id ?? c.id ?? null,
                        year,
                        term,
                        course_code: c.course_code,
                        course_name: c.course_name,
                        credit: Number(c.credits) || 0,
                        course_type: '추가',
                        grade: c.selectedGrade || '미입력',
                    });
                });
                renderOverallSummary();
                renderCourseListFor(activeSemester);
            },
        });
    });
}

// 학기 전환 시 모달 UI 및 선택 상태 초기화
// 코스 검색 모달로 대체됨: resetAddCourseModalUI 제거

/**
 * 전체 요약 정보를 렌더링합니다.
 * - 전체 학점 합산과 전체 GPA 값을 화면에 표시합니다.
 * @returns {void}
 */
function renderOverallSummary() {
    const totalCredits = allCourses.reduce((sum, c) => sum + Number(c.credit), 0);
    document.getElementById('total-credits').textContent = totalCredits;
    document.getElementById('total-gpa').textContent = calculateGpa(allCourses);
}

/**
 * 학기 목록을 렌더링하고 항목 클릭 시 해당 학기 상세를 표시하도록 바인딩합니다.
 * @returns {void}
 */
function renderSemesterList() {
    const semesterListEl = document.getElementById('semester-list');
    semesterListEl.innerHTML = '';

    const semesters = [...new Set(allCourses.map(c => `${c.year}년 ${c.term}`))].sort().reverse();

    semesters.forEach(semester => {
        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action';
        li.textContent = semester;
        li.dataset.semester = semester;

        li.addEventListener('click', () => {
            activeSemester = semester;
            document.querySelectorAll('#semester-list .list-group-item').forEach(item => item.classList.remove('active'));
            li.classList.add('active');
            renderCourseListFor(semester);
        });
        semesterListEl.appendChild(li);
    });
}

/**
 * 특정 학기의 강의 목록과 요약 정보를 렌더링합니다.
 * @param {string} semester - 'YYYY년 학기' 형식의 학기 키
 * @returns {void}
 */
function renderCourseListFor(semester) {
    const coursesInSemester = allCourses.filter(c => `${c.year}년 ${c.term}` === semester);
    const semesterCredits = coursesInSemester.reduce((sum, c) => sum + Number(c.credit), 0);

    document.getElementById('semester-title').textContent = semester;
    document.getElementById('semester-credits').textContent = semesterCredits;
    document.getElementById('semester-gpa').textContent = calculateGpa(coursesInSemester);

    const courseListEl = document.getElementById('course-list');
    courseListEl.innerHTML = '';

    coursesInSemester.forEach(course => {
        if (course.__placeholder) return; // 더미 데이터는 표시하지 않음
        const courseHtml = `
            <div class="card mb-2">
                <div class="card-body p-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-0">${course.course_name}</h6>
                            <small class="text-muted">${course.course_code} | ${course.credit}학점</small>
                        </div>
                        <span class="badge bg-primary rounded-pill">${course.grade}</span>
                    </div>
                </div>
            </div>`;
        courseListEl.insertAdjacentHTML('beforeend', courseHtml);
    });
}

/**
 * '학기 추가' 모달의 년도 드롭다운을 채웁니다.
 * @returns {void}
 */
function populateYearOptions() {
    const sel = document.getElementById('new-semester-year');
    if (!sel) return;

    const now = new Date().getFullYear();
    sel.innerHTML = '<option value="">선택</option>'; // 초기화
    for (let y = now; y >= now - 10; y--) {
        sel.add(new Option(String(y), String(y)));
    }
}

/**
 * '학기 추가' 모달의 확인 버튼에 이벤트 리스너를 바인딩합니다.
 * - 선택된 연/학기를 기존 목록에 없을 경우 자리표시 항목으로 추가합니다.
 * @returns {void}
 */
function bindAddSemesterModal() {
    const btn = document.getElementById('confirm-add-semester');
    if (!btn) return;
    btn.addEventListener('click', () => {
        const year = document.getElementById('new-semester-year').value;
        const term = document.getElementById('new-semester-term').value;
        if (!year || !term) {
            alert('년도와 학기를 선택하세요.');
            return;
        }

        const key = `${year}년 ${term}`;
        const exists = new Set(allCourses.map(c => `${c.year}년 ${c.term}`));
        if (!exists.has(key)) {
            allCourses.push({ year: parseInt(year), term: term, credit: 0, __placeholder: true });
        }

        renderSemesterList();

        document.querySelectorAll('#semester-list .list-group-item').forEach(li => {
            if (li.dataset.semester === key) li.click();
        });

        const modalEl = document.getElementById('add-semester-modal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal?.hide();

        document.getElementById('new-semester-year').value = '';
        document.getElementById('new-semester-term').value = '';
    });
}