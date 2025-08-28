/**
 * 강의 검색/선택 모달 컴포넌트
 * - 카테고리/조직 드롭다운 초기화 후 과목을 검색하고, 선택 목록에 담아 부모로 전달합니다.
 * - 중복 방지를 위해 이미 추가된 과목은 담기 버튼을 비활성화합니다.
 */

import { initializeCategoryDropdowns, buildCategorySearchParams } from '../../../home/js/dropdown/category_dropdown.js';
import { initializeOrgDropdowns } from '../../../home/js/dropdown/org_dropdown.js';
import { searchCoursesForHistory } from '../api.js';

/**
 * 강의 검색 모달의 뷰-로직을 담당하는 클래스
 */
export class CourseSearchModal {
    /**
     * @param {HTMLElement|null} modalElement - 모달 루트 엘리먼트
     */
    constructor(modalElement) {
        this.modalEl = modalElement;
        this.bsModal = this.modalEl ? new window.bootstrap.Modal(this.modalEl) : null;

        // 내부 상태
        this.selectedCourses = [];
        this.existingCourses = [];
        this.activeSemester = null;
        this.onConfirmCallback = null;

        // 요소 캐시
        this.titleEl = this.modalEl?.querySelector('#modal-title') || null;
        this.searchBtn = this.modalEl?.querySelector('#modal-search-btn') || null;
        this.resultsBody = this.modalEl?.querySelector('#modal-results-body') || null;
        this.selectedList = this.modalEl?.querySelector('#selected-courses-list') || null;
        this.confirmBtn = this.modalEl?.querySelector('#confirm-add-courses') || null;

        // 바인딩
        this._onSearchClick = this._onSearchClick.bind(this);
        this._onConfirmClick = this._onConfirmClick.bind(this);

        // 이벤트
        this.searchBtn?.addEventListener('click', this._onSearchClick);
        this.confirmBtn?.addEventListener('click', this._onConfirmClick);
    }

    /**
     * 모달을 표시하고 초기 상태를 설정합니다.
     * @param {{
     *  activeSemester?: string,
     *  existingCourses?: Array<any>,
     *  onConfirm?: (selected: Array<any>) => void,
     * }} [options]
     */
    show(options) {
        this.activeSemester = options?.activeSemester || null;
        this.existingCourses = Array.isArray(options?.existingCourses) ? options.existingCourses : [];
        this.onConfirmCallback = typeof options?.onConfirm === 'function' ? options.onConfirm : null;

        // 상태/UI 초기화
        this.selectedCourses = [];
        if (this.resultsBody) this.resultsBody.innerHTML = '';
        if (this.selectedList) this.selectedList.innerHTML = '';
        if (this.titleEl && this.activeSemester) this.titleEl.textContent = `${this.activeSemester} 강의 추가`;

        // 드롭다운 초기화 (카테고리/조직)
        try { initializeCategoryDropdowns(); } catch (_) {}
        try { initializeOrgDropdowns(); } catch (_) {}
        this.bsModal?.show();
    }

    /** 모달을 숨깁니다. */
    hide() { this.bsModal?.hide(); }

    /** 리스너 제거 등 정리 작업을 수행합니다. */
    destroy() {
        this.searchBtn?.removeEventListener('click', this._onSearchClick);
        this.confirmBtn?.removeEventListener('click', this._onConfirmClick);
    }

    /** 검색 버튼 클릭 핸들러: 파라미터 구성 후 검색 API 호출 */
    async _onSearchClick() {
        if (!this.resultsBody) return;
        this.resultsBody.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-muted">검색 중...</td></tr>';
        try {
        const params = buildCategorySearchParams();
        // 학기 정보 파라미터 추가
        if (this.activeSemester) {
            const [yStr, term] = this.activeSemester.split('년 ');
            const yr = parseInt(yStr, 10);
            if (!Number.isNaN(yr) && term) {
            params.set('year', String(yr));
            params.set('term', term);
            }
        }
        const data = await searchCoursesForHistory(params);
        this._renderSearchResults(Array.isArray(data) ? data : (data?.results || []));
        } catch (e) {
        console.error(e);
        this.resultsBody.innerHTML = '<tr><td colspan="4" class="text-danger text-center py-3">검색 중 오류가 발생했습니다.</td></tr>';
        }
    }

    /**
     * 검색 결과 테이블 렌더링
     * @param {Array<any>} courses
     */
    _renderSearchResults(courses) {
        if (!this.resultsBody) return;
        this.resultsBody.innerHTML = '';
        if (!courses || courses.length === 0) {
        this.resultsBody.innerHTML = '<tr><td colspan="4" class="text-center py-3">검색 결과가 없습니다.</td></tr>';
        return;
        }
        const normalize = (code) => (code ? String(code).trim().toUpperCase().replace(/\s+/g, '').replace(/-/g, '') : '');
        courses.forEach(c => {
        const tr = document.createElement('tr');
        tr.classList.add('course-block');
        tr.dataset.courseId = c.course_id;

        const tdName = document.createElement('td');
        tdName.classList.add('fw-bold');
        tdName.textContent = c.course_name;

        const tdCode = document.createElement('td');
        tdCode.textContent = c.course_code || '-';

        const tdCred = document.createElement('td');
        tdCred.classList.add('text-center');
        tdCred.textContent = c.credits;

        const tdAction = document.createElement('td');
        tdAction.classList.add('text-center');
        
        // course_code 기준 중복 체크
        const existing = this.existingCourses.find(ec => {
            const codeA = normalize(ec.course_code);
            const codeB = normalize(c.course_code);
            if (codeA && codeB && codeA === codeB) return true;
            return false;
        });

        if (existing) {
            // 중복된 경우
            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-outline-danger';
            btn.textContent = `${existing.year}-${existing.term} 추가 됨`;
            btn.style.fontSize = '80%';
            btn.disabled = true;
            tdAction.appendChild(btn);
        } else {
            // 중복되지 않은 경우
            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-outline-primary';
            btn.textContent = '담기';
            btn.addEventListener('click', () => this._addCourseToSelected(c));
            tdAction.appendChild(btn);
        }

        tr.append(tdName, tdCode, tdCred, tdAction);
        this.resultsBody.appendChild(tr);
        });
    }

    /**
     * 선택 목록에 강의를 추가합니다.
     * @param {any} course
     */
    _addCourseToSelected(course) {
        if (this.selectedCourses.find(sc => sc.course_id === course.course_id)) return;
        const copy = { ...course, selectedGrade: '미입력' };
        this.selectedCourses.push(copy);
        this._renderSelectedList();
    }

    /** 선택된 강의 목록(우측 리스트)을 렌더링합니다. */
    _renderSelectedList() {
        if (!this.selectedList) return;
        this.selectedList.innerHTML = '';
        this.selectedCourses.forEach((c, idx) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.textContent = `${c.course_name} (${c.credits}학점)`;

        const gradeSelect = document.createElement('select');
        gradeSelect.className = 'form-select form-select-sm ms-2';
        const gradeOptions = ['미이수','A+','A0','B+','B0','C+','C0','D+','D0','F'];
        gradeOptions.forEach(g => {
            const opt = document.createElement('option');
            opt.value = g; opt.textContent = g; gradeSelect.appendChild(opt);
        });
        gradeSelect.value = c.selectedGrade;
        gradeSelect.addEventListener('change', () => { this.selectedCourses[idx].selectedGrade = gradeSelect.value; });

        const rm = document.createElement('button');
        rm.className = 'btn btn-sm btn-outline-secondary';
        rm.textContent = '제거';
        rm.addEventListener('click', () => {
            this.selectedCourses.splice(idx, 1);
            this._renderSelectedList();
        });

        const rightBox = document.createElement('div');
        rightBox.className = 'd-flex align-items-center gap-2';
        rightBox.appendChild(gradeSelect);
        rightBox.appendChild(rm);
        li.appendChild(rightBox);
        this.selectedList.appendChild(li);
        });
    }

    /** 확인 버튼 클릭 시 콜백으로 선택 결과를 전달하고 모달을 닫습니다. */
    _onConfirmClick() {
        if (this.onConfirmCallback) {
        this.onConfirmCallback(this.selectedCourses);
        }
        this.hide();
    }
}


