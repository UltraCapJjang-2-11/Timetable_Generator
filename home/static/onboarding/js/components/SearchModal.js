/**
 * 검색 모달의 공통 컴포넌트
 * - 입력값으로 API URL을 빌드하고 결과를 렌더링하여 선택값을 부모로 전달합니다.
 * - 구체적인 렌더링/선택 처리는 options 콜백으로 주입합니다.
 */

export class SearchModal {
  /**
   * @param {HTMLElement} modalElement
   * @param {{
   *  buildApiUrl: (q: string) => string,
   *  renderResultItem: (item: any) => string | HTMLElement,
   *  onSelect: (item: any) => void,
   *  inputSelector?: string,
   *  resultsSelector?: string,
   *  searchBtnSelector?: string,
   * }} options
   */
  constructor(modalElement, options) {
    this.modalEl = modalElement;
    this.options = options || {};
    this.bsModal = this.modalEl ? new window.bootstrap.Modal(this.modalEl) : null;

    this.input = this.modalEl?.querySelector(this.options.inputSelector || 'input[type="text"]') || null;
    this.results = this.modalEl?.querySelector(this.options.resultsSelector || '.list-group') || null;
    this.searchBtn = this.modalEl?.querySelector(this.options.searchBtnSelector || 'button[type="button"]') || null;

    this._onSearchClick = this._onSearchClick.bind(this);
    this._onKeydown = this._onKeydown.bind(this);
    this._onResultsClick = this._onResultsClick.bind(this);

    this._bind();
  }

  /** 모달을 표시합니다. */
  show() { this.bsModal?.show(); }
  /** 모달을 숨깁니다. */
  hide() { this.bsModal?.hide(); }

  /** 이벤트 리스너를 해제합니다. */
  destroy() {
    this.searchBtn?.removeEventListener('click', this._onSearchClick);
    this.input?.removeEventListener('keydown', this._onKeydown);
    this.results?.removeEventListener('click', this._onResultsClick);
  }

  /** 내부 요소에 이벤트 리스너를 바인딩합니다. */
  _bind() {
    this.searchBtn?.addEventListener('click', this._onSearchClick);
    this.input?.addEventListener('keydown', this._onKeydown);
    this.results?.addEventListener('click', this._onResultsClick);
  }

  /** 검색 버튼 클릭 또는 Enter 입력 시 실행되어 API를 호출합니다. */
  async _onSearchClick() {
    const q = (this.input?.value || '').trim();
    if (!this.results) return;
    this.results.innerHTML = '<div class="text-muted px-2">검색 중...</div>';
    try {
      const url = this.options.buildApiUrl(q);
      const resp = await fetch(url, { credentials: 'same-origin' });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.message || '검색 실패');
      this._renderResults(data?.results || []);
    } catch (e) {
      this.results.innerHTML = '<div class="text-danger px-2">검색 중 오류가 발생했습니다.</div>';
    }
  }

  /** 입력창에서 Enter 키를 누르면 검색을 트리거합니다. */
  _onKeydown(e) {
    if (e.key === 'Enter') this._onSearchClick();
  }

  /** 결과 목록의 항목을 클릭하면 선택 콜백을 호출하고 모달을 닫습니다. */
  _onResultsClick(e) {
    const target = e.target.closest('[data-item]');
    if (!target) return;
    e.preventDefault();
    const payload = target.dataset.item ? JSON.parse(target.dataset.item) : null;
    if (payload) this.options.onSelect?.(payload);
    this.hide();
  }

  /** 검색 결과를 목록 형태로 렌더링합니다. */
  _renderResults(items) {
    if (!this.results) return;
    if (!items.length) {
      this.results.innerHTML = '<div class="text-muted px-2">검색 결과가 없습니다.</div>';
      return;
    }
    this.results.innerHTML = '';
    items.forEach((item) => {
      const html = this.options.renderResultItem?.(item);
      if (typeof html === 'string') {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'list-group-item list-group-item-action';
        a.dataset.item = JSON.stringify(item);
        a.innerHTML = html;
        this.results.appendChild(a);
      } else if (html instanceof HTMLElement) {
        html.dataset.item = JSON.stringify(item);
        html.classList.add('list-group-item', 'list-group-item-action');
        this.results.appendChild(html);
      } else {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'list-group-item list-group-item-action';
        a.dataset.item = JSON.stringify(item);
        a.textContent = item?.name || '항목';
        this.results.appendChild(a);
      }
    });
  }
}


