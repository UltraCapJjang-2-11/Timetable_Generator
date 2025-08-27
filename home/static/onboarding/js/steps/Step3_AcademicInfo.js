import { getImageUrls, getStudentInfo } from '../state.js';
import { PdfViewer } from '../components/PdfViewer.js';
import { SearchModal } from '../components/SearchModal.js';

/**
 * 온보딩 Step 3 - 학사정보 입력 단계 UI 로직.
 * - 상태(`getStudentInfo`)에서 초기값을 채우고, 교과적용년도 셀렉트박스를 구성합니다.
 * - 성적표 이미지가 있으면 `PdfViewer`를 초기화하여 오른쪽에 미리보기를 표시합니다.
 * - 대학/학과 검색을 위해 `SearchModal`을 설정하고, 선택 결과를 입력 필드에 반영합니다.
 * - 다음 버튼 클릭 시 현재 입력값을 payload로 담아 `step-success` 이벤트를 발행합니다.
 */

let viewer = null;
let containerRef = null;
let collegeModal = null;
let deptModal = null;

/**
 * 교과적용년도 드롭다운을 현재 년도를 기준으로 최근 10년 범위로 채웁니다.
 * @param {HTMLElement} container - 스텝 루트 컨테이너
 * @param {string|number} [selectedYear] - 선택할 연도(옵션)
 */
function populateCurriculumYears(container, selectedYear) {
  const select = container.querySelector('#curriculum-year');
  if (!select) return;
  const now = new Date().getFullYear();
  const years = [];
  for (let y = now; y >= now - 10; y--) years.push(y);
  select.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
  years.forEach(y => {
    const opt = document.createElement('option');
    opt.value = String(y);
    opt.textContent = String(y);
    select.appendChild(opt);
  });
  if (selectedYear && years.includes(parseInt(selectedYear))) {
    select.value = String(selectedYear);
  }
}

/**
 * 중앙 상태의 학생정보를 읽어 폼 필드를 채웁니다.
 * 상태가 없으면 교과적용년도만 기본 범위로 채웁니다.
 * @param {HTMLElement} container
 */
function fillInitial(container) {
  const info = getStudentInfo();
  if (info) {
    const college = (info['대학'] || '').trim();
    const dept = (info['학과(전공)'] || '').trim();
    const year = parseInt(info['학년']);
    container.querySelector('#college').value = college;
    container.querySelector('#department').value = dept;
    container.querySelector('#student-id').value = info['학번'] || '';
    container.querySelector('#name').value = info['성명'] || '';
    if (!Number.isNaN(year)) {
      container.querySelector('#year').value = String(year);
    }
    container.querySelector('#completed-semesters').value = info['이수학기'] || '';
    populateCurriculumYears(container, info['교과적용년도']);
  } else {
    populateCurriculumYears(container);
  }
}

/**
 * 성적표 이미지가 존재하면 PDF 뷰어를 초기화합니다.
 * @param {HTMLElement} container
 */
function initViewerIfAny(container) {
  const urls = getImageUrls();
  const viewerContainer = container.querySelector('#pdf-viewer-container');
  viewer = new PdfViewer(viewerContainer);
  const img = urls?.student_info ? [urls.student_info] : [];
  viewer.init(img);
}

/**
 * 대학/학과 검색 모달을 초기화하고 버튼 클릭 시 표시되도록 이벤트를 바인딩합니다.
 * 선택 시 입력 필드 값을 갱신합니다.
 * @param {HTMLElement} container
 */
function initSearchModals(container) {
  const collegeModalEl = container.querySelector('#collegeSearchModal');
  const deptModalEl = container.querySelector('#deptSearchModal');

  collegeModal = new SearchModal(collegeModalEl, {
    inputSelector: '#college-search-input',
    resultsSelector: '#college-search-results',
    searchBtnSelector: '#college-search-btn',
    buildApiUrl: (q) => `/data-manager/search/colleges/?q=${encodeURIComponent(q)}`,
    renderResultItem: (item) => item.name,
    onSelect: (item) => {
      container.querySelector('#college').value = item.name;
      container.querySelector('#department').value = '';
    },
  });

  deptModal = new SearchModal(deptModalEl, {
    inputSelector: '#dept-search-input',
    resultsSelector: '#dept-search-results',
    searchBtnSelector: '#dept-search-btn',
    buildApiUrl: (q) => {
      const college = (container.querySelector('#college')?.value || '').trim();
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (college) params.set('college_name', college);
      return `/data-manager/search/departments/?${params.toString()}`;
    },
    renderResultItem: (item) => item.name + (item.college ? ` · ${item.college}` : ''),
    onSelect: (item) => {
      container.querySelector('#department').value = item.name;
    },
  });

  container.querySelector('#btn-college-search')?.addEventListener('click', () => {
    container.querySelector('#college-search-input').value = '';
    container.querySelector('#college-search-results').innerHTML = '';
    collegeModal.show();
  });
  container.querySelector('#btn-dept-search')?.addEventListener('click', () => {
    container.querySelector('#dept-search-input').value = '';
    container.querySelector('#dept-search-results').innerHTML = '';
    deptModal.show();
  });
}

/**
 * Step 3 컴포넌트를 초기화하고 이벤트를 바인딩합니다.
 * 다음 버튼 클릭 시 현재 입력값을 `detail`에 담아 `step-success` 이벤트를 발행합니다.
 * @param {HTMLElement} container
 */
export function mount(container) {
  containerRef = container;
  fillInitial(container);
  initViewerIfAny(container);

  // 다음 버튼 → 현재 폼 데이터 전달
  container.querySelector('.next-btn')?.addEventListener('click', () => {
    const payload = {
      college: container.querySelector('#college').value,
      department: container.querySelector('#department').value,
      studentId: container.querySelector('#student-id').value,
      name: container.querySelector('#name').value,
      year: container.querySelector('#year').value,
      completedSemesters: container.querySelector('#completed-semesters').value,
      curriculumYear: container.querySelector('#curriculum-year').value,
    };
    container.dispatchEvent(new CustomEvent('step-success', { detail: payload, bubbles: true }));
  });

  container.querySelector('.prev-btn')?.addEventListener('click', () => {
    container.dispatchEvent(new CustomEvent('step-previous', { bubbles: true }));
  });

  initSearchModals(container);
}

/**
 * PdfViewer와 SearchModal을 포함한 자원을 정리합니다.
 */
export function destroy() {
  if (viewer && viewer.destroy) viewer.destroy();
  collegeModal?.destroy?.();
  deptModal?.destroy?.();
  viewer = null;
  containerRef = null;
}
