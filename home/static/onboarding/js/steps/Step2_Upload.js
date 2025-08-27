// Step2_Upload.js
/**
 * 온보딩 Step 2 - 성적표 PDF 업로드 및 분석 단계 UI 로직.
 * - 드래그앤드롭/파일선택 처리, 업로드·분석 API 호출, 상태 저장(`setPdfResult`), PDF 미리보기.
 * - 외부에서는 `mount(container)`로 초기화하고 `destroy()`로 정리합니다.
 */

import { api } from '../api.js';
import { setPdfResult } from '../state.js';
import { PdfViewer } from '../components/PdfViewer.js';

let selectedFile = null;
let containerRef = null;
let viewer = null;

/**
 * 드래그/드롭 기본 동작을 방지합니다.
 * @param {Event} e
 */
function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
/**
 * 드롭 이벤트에서 파일 목록을 추출하여 처리합니다.
 * @param {DragEvent} e
 */
function handleDrop(e) { const dt = e.dataTransfer; handleFileSelect(dt.files); }

/**
 * 선택된 파일을 검증(PDF만 허용)하고 UI/상태를 갱신합니다.
 * @param {FileList|File[]} files
 */
function handleFileSelect(files) {
  if (files.length > 0) {
    if (files[0].type !== 'application/pdf') {
      alert('PDF 파일만 업로드할 수 있습니다.');
      return;
    }
    selectedFile = files[0];
    containerRef.querySelector('#file-name-display').textContent = selectedFile.name;
    containerRef.querySelector('#upload-process-btn').disabled = false;
  }
}

/**
 * 선택된 PDF를 서버로 업로드하고 분석 결과를 수신하여 상태에 저장합니다.
 * 성공 시 업로드 패널을 숨기고 뷰어 패널을 표시합니다.
 * @returns {Promise<void>}
 */
async function uploadAndProcessFile() {
  if (!selectedFile) { alert('파일을 선택해주세요.'); return; }
  const loadingOverlay = containerRef.querySelector('#loading-overlay');
  loadingOverlay.classList.remove('d-none');
  loadingOverlay.classList.add('d-flex');

  const formData = new FormData();
  formData.append('pdf_file', selectedFile);
  try {
    const data = await api.processPdf(formData);
    if (data.status === 'success') {
      // 상태 저장
      setPdfResult(data);
      // 패널 전환
      containerRef.querySelector('#upload-panel')?.classList.add('d-none');
      containerRef.querySelector('#viewer-panel')?.classList.remove('d-none');
      // 뷰어 표시
      const viewerContainer = containerRef.querySelector('#pdf-viewer-container');
      if (viewer && viewer.destroy) viewer.destroy();
      viewer = new PdfViewer(viewerContainer);
      viewer.init(data.image_urls.original || []);
      // 안내 텍스트
      containerRef.querySelector('#analysis-result-text').textContent = '✓ 분석이 완료되었습니다.';
      const nextBtn = containerRef.querySelector('#next-btn');
      if (nextBtn) nextBtn.textContent = '다음 단계로';
    } else {
      alert(`오류: ${data.message || '알 수 없는 오류가 발생했습니다.'}`);
    }
  } catch (err) {
    console.error('Upload Error:', err);
    alert('업로드 중 오류가 발생했습니다.');
  } finally {
    loadingOverlay.classList.add('d-none');
    loadingOverlay.classList.remove('d-flex');
  }
}

/**
 * Step 2 컴포넌트를 초기화하고 이벤트를 바인딩합니다.
 * - 드래그앤드롭, 파일 선택, 업로드 처리, 재업로드, 다음 버튼 처리.
 * - PdfViewer를 빈 상태로 초기 생성합니다.
 * @param {HTMLElement} container
 */
export function mount(container) {
  containerRef = container;
  selectedFile = null;
  // 초기 뷰어 비움
  const viewerContainer = containerRef.querySelector('#pdf-viewer-container');
  viewer = new PdfViewer(viewerContainer);
  viewer.init([]);

  const dropZone = container.querySelector('#drop-zone');
  const fileInput = container.querySelector('#file-input');
  const fileBrowseBtn = container.querySelector('#file-browse-btn');
  const reuploadBtn = container.querySelector('#reupload-btn');

  fileBrowseBtn?.addEventListener('click', () => fileInput?.click());
  fileInput?.addEventListener('change', (e) => handleFileSelect(e.target.files));
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone?.addEventListener(eventName, preventDefaults, false);
  });
  dropZone?.addEventListener('drop', handleDrop, false);
  container.querySelector('#upload-process-btn')?.addEventListener('click', uploadAndProcessFile);

  reuploadBtn?.addEventListener('click', () => {
    selectedFile = null;
    containerRef.querySelector('#file-name-display').textContent = '';
    containerRef.querySelector('#upload-process-btn').disabled = true;
    containerRef.querySelector('#viewer-panel')?.classList.add('d-none');
    containerRef.querySelector('#upload-panel')?.classList.remove('d-none');
    // 뷰어 리셋
    if (viewer && viewer.destroy) viewer.destroy();
    viewer = new PdfViewer(viewerContainer);
    viewer.init([]);
  });

  // 다음(건너뛰기) → 성공 이벤트 공통 발행
  container.querySelector('#next-btn')?.addEventListener('click', () => {
    container.dispatchEvent(new CustomEvent('step-success', { bubbles: true }));
  });
}

/**
 * PdfViewer 및 내부 레퍼런스를 정리합니다.
 */
export function destroy() {
  if (viewer && viewer.destroy) viewer.destroy();
  containerRef = null;
  selectedFile = null;
  viewer = null;
}


