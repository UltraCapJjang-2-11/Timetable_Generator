// components/PdfViewer.js

/**
 * 컨테이너 단위로 동작하는 PDF 뷰어 컴포넌트
 * 템플릿은 includes/_pdf_viewer.html 구조를 가정합니다.
 */
export class PdfViewer {
  /**
   * @param {HTMLElement} containerElement - PDF 뷰어 컨테이너(root). includes/_pdf_viewer.html 구조를 가정합니다.
   */
  constructor(containerElement) {
    this.container = containerElement;
    this.imageUrls = [];
    this.currentIndex = 0;
    this.panzoom = null;

    // 바인딩된 핸들러 참조 보관 (remove용)
    this._onNext = this._onNext.bind(this);
    this._onPrev = this._onPrev.bind(this);
    this._onZoom = this._onZoom.bind(this);
    this._onWheel = null; // Panzoom 생성 후 주입

    // 컨트롤 요소 캐시 (id 선택자는 범위 한정 위해 [id="..."] 사용)
    this.el = {
      placeholder: this.container.querySelector('[id="viewer-placeholder"]'),
      imageContainer: this.container.querySelector('[id="image-container"]'),
      body: this.container.querySelector('[id="viewer-body"]'),
      pageIndicator: this.container.querySelector('[id="viewer-page-indicator"]'),
      zoomIndicator: this.container.querySelector('[id="viewer-zoom-indicator"]'),
      prevBtn: this.container.querySelector('[id="viewer-prev-btn"]'),
      nextBtn: this.container.querySelector('[id="viewer-next-btn"]'),
    };

    // 네비게이션 버튼 리스너 (중복 방지 위해 먼저 제거 시도 후 등록)
    this.el.nextBtn?.removeEventListener('click', this._onNext);
    this.el.prevBtn?.removeEventListener('click', this._onPrev);
    this.el.nextBtn?.addEventListener('click', this._onNext);
    this.el.prevBtn?.addEventListener('click', this._onPrev);
  }

  /**
   * 뷰어를 초기화하고 첫 페이지를 렌더링합니다.
   * @param {string[]} imageUrls - 페이지별 이미지 URL 배열
   */
  init(imageUrls) {
    this.imageUrls = Array.isArray(imageUrls) ? imageUrls : [];
    this.currentIndex = 0;

    if (this.imageUrls.length > 0) {
      this.el.placeholder?.classList.add('d-none');
      this._renderCurrentPage();
    } else {
      if (this.el.placeholder) {
        this.el.placeholder.textContent = '표시할 이미지가 없습니다.';
        this.el.placeholder.classList.remove('d-none');
      }
      this._updateUI();
    }
  }

  /**
   * 리스너 및 Panzoom 리소스를 해제합니다.
   */
  destroy() {
    // 이벤트 리스너 제거
    this.el.nextBtn?.removeEventListener('click', this._onNext);
    this.el.prevBtn?.removeEventListener('click', this._onPrev);
    if (this._onWheel && this.el.body) {
      this.el.body.removeEventListener('wheel', this._onWheel);
      this._onWheel = null;
    }

    // Panzoom 해제
    if (this.panzoom) {
      this.panzoom.destroy();
      this.panzoom = null;
    }

    // 컨테이너 정리
    if (this.el.imageContainer) {
      this.el.imageContainer.innerHTML = '';
    }
  }

  /**
   * 현재 인덱스의 페이지 이미지를 렌더링하고 Panzoom을 연결합니다.
   * @private
   */
  _renderCurrentPage() {
    const imageContainer = this.el.imageContainer;
    if (!imageContainer) return;
    imageContainer.innerHTML = '';

    const img = document.createElement('img');
    const imageUrl = this.imageUrls[this.currentIndex];
    
    // 이미지 로드 오류 처리
    img.onerror = () => {
      console.error('이미지 로드 실패:', imageUrl);
      imageContainer.innerHTML = '<p class="text-danger text-center mt-3">이미지를 불러올 수 없습니다.</p>';
    };
    
    img.onload = () => {
      console.log('이미지 로드 성공:', imageUrl);
    };
    
    img.src = imageUrl;
    img.style.maxWidth = '100%';
    img.style.maxHeight = '100%';
    imageContainer.appendChild(img);

    if (this.panzoom) {
      this.panzoom.destroy();
      this.panzoom = null;
    }

    // Panzoom은 전역 로드됨
    this.panzoom = (window.Panzoom || Panzoom)(img, {
      maxScale: 4,
      minScale: 0.5,
      canvas: true,
    });

    // wheel 핸들러는 인스턴스 메서드가 아니라 Panzoom 제공 함수를 사용
    if (this.el.body && this.panzoom) {
      this._onWheel = this.panzoom.zoomWithWheel;
      this.el.body.addEventListener('wheel', this._onWheel);
    }
    img.addEventListener('panzoomzoom', this._onZoom);

    this._updateUI();
  }

  /**
   * 줌/페이지 인디케이터와 네비게이션 버튼 상태를 갱신합니다.
   * @private
   */
  _updateUI() {
    // 줌 표시
    if (this.panzoom && this.el.zoomIndicator) {
      const scale = this.panzoom.getScale();
      const percent = Math.round(scale * 100);
      this.el.zoomIndicator.textContent = `${percent}%`;
    }

    // 페이지/버튼
    if (this.el.pageIndicator && this.el.prevBtn && this.el.nextBtn) {
      if (this.imageUrls.length > 0) {
        this.el.pageIndicator.textContent = `${this.currentIndex + 1} / ${this.imageUrls.length}`;
        this.el.prevBtn.disabled = (this.currentIndex === 0);
        this.el.nextBtn.disabled = (this.currentIndex >= this.imageUrls.length - 1);
      } else {
        this.el.pageIndicator.textContent = '0 / 0';
        this.el.prevBtn.disabled = true;
        this.el.nextBtn.disabled = true;
      }
    }
  }

  /**
   * Panzoom zoom 이벤트 핸들러로, 줌 표시를 갱신합니다.
   * @private
   */
  _onZoom() {
    if (this.panzoom && this.el.zoomIndicator) {
      const scale = this.panzoom.getScale();
      const percent = Math.round(scale * 100);
      this.el.zoomIndicator.textContent = `${percent}%`;
    }
  }

  /**
   * 다음 페이지로 이동합니다.
   * @private
   */
  _onNext() {
    if (this.currentIndex < this.imageUrls.length - 1) {
      this.currentIndex++;
      this._renderCurrentPage();
    }
  }

  /**
   * 이전 페이지로 이동합니다.
   * @private
   */
  _onPrev() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this._renderCurrentPage();
    }
  }
}

// 팩토리 함수 형태도 제공
/**
 * PdfViewer 인스턴스를 생성합니다.
 * @param {HTMLElement} containerElement
 * @returns {PdfViewer}
 */
export function createPdfViewer(containerElement) {
  return new PdfViewer(containerElement);
}
