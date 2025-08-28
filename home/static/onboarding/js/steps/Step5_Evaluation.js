/**
 * 온보딩 Step 5 - 졸업요건 평가 단계 UI 로직.
 * - 서버 API를 호출해 졸업요건 평가 결과를 받아 트리 형태로 렌더링합니다.
 * - 이전/제출 버튼에서 각각 `step-previous`, `step-success` 이벤트를 발행합니다.
 */
import { api } from '../api.js';

/**
 * 컴포넌트를 초기화하고 이벤트를 바인딩합니다.
 * @param {HTMLElement} container - 스텝 루트 컨테이너
 */
export function mount(container) {
  fetchAndRender(container);
  container.querySelector('.prev-btn')?.addEventListener('click', () => {
    container.dispatchEvent(new CustomEvent('step-previous', { bubbles: true }));
  });
  container.querySelector('#submit-btn')?.addEventListener('click', () => {
    container.dispatchEvent(new CustomEvent('step-success', { bubbles: true }));
  });
}

/**
 * 정리 훅(현재는 해제할 리소스 없음)
 */
export function destroy() {}

/**
 * 졸업요건 평가 API를 호출하고 테이블/리스트로 결과를 렌더링합니다.
 * @param {HTMLElement} container
 */
async function fetchAndRender(container) {
  try {
    const data = await api.evaluateGraduation();
    renderGraduationMatrix(container, data);
  } catch (e) {
    console.error(e);
    const body = container.querySelector('#graduation-matrix-body');
    if (body) {
      body.innerHTML = `<tr><td colspan="4" class="text-danger">졸업 요건 평가 중 오류가 발생했습니다.</td></tr>`;
    }
  }
}

/**
 * @typedef {Object} GraduationCategory
 * @property {number} category_id
 * @property {number|null} [parent_category_id]
 * @property {string} category_name
 *
 * @typedef {Object} GraduationEvalPayload
 * @property {GraduationCategory[]} [categories]
 * @property {Object.<number, number>} [required_by_category] - 카테고리ID별 요구 학점
 * @property {Object.<number, number>} [earned_by_category] - 카테고리ID별 취득 학점
 * @property {Array} [results]
 * @property {string[]} [lacking]
 * @property {string|null} [ruleset_name]
 */

/**
 * 졸업요건 결과 트리를 테이블과 부가 설명으로 렌더링합니다.
 * @param {HTMLElement} container
 * @param {GraduationEvalPayload} payload
 */
function renderGraduationMatrix(container, payload) {
  const { categories = [], required_by_category = {}, earned_by_category = {}, results = [], lacking = [], ruleset_name = null } = payload || {};

  const idToNode = new Map();
  categories.forEach(cat => { idToNode.set(cat.category_id, { ...cat, children: [] }); });
  const roots = [];
  categories.forEach(cat => {
    const node = idToNode.get(cat.category_id);
    if (cat.parent_category_id && idToNode.has(cat.parent_category_id)) {
      idToNode.get(cat.parent_category_id).children.push(node);
    } else { roots.push(node); }
  });

  const tbody = container.querySelector('#graduation-matrix-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  const renderRow = (node, depth = 0) => {
    const required = required_by_category[node.category_id] ?? 0;
    const earned = Number(earned_by_category[node.category_id] ?? 0);
    const satisfied = earned >= required;
    const indent = '&nbsp;'.repeat(depth * 4);
    const rowHtml = `
      <tr>
        <td>${indent}${node.category_name}</td>
        <td class="text-end">${required}</td>
        <td class="text-end">${earned.toFixed(1)}</td>
        <td class="text-center">${satisfied ? '<span class="badge bg-success">충족</span>' : '<span class="badge bg-warning text-dark">부족</span>'}</td>
      </tr>`;
    tbody.insertAdjacentHTML('beforeend', rowHtml);
    node.children.forEach(child => renderRow(child, depth + 1));
  };

  roots.forEach(root => renderRow(root, 0));

  const rsEl = container.querySelector('#ruleset-name');
  if (rsEl) {
    rsEl.textContent = ruleset_name ? `적용 규칙: ${ruleset_name}` : '적용 규칙 없음';
    rsEl.classList.toggle('bg-secondary', !ruleset_name);
  }

  const remarkList = container.querySelector('#graduation-remarks');
  if (remarkList) {
    remarkList.innerHTML = '';
    const uniq = Array.from(new Set(lacking || []));
    if (uniq.length === 0) {
      const li = document.createElement('li');
      li.innerHTML = '<span class="text-success">모든 규칙을 충족했습니다.</span>';
      remarkList.appendChild(li);
    } else {
      uniq.forEach(text => {
        const li = document.createElement('li');
        li.textContent = text;
        remarkList.appendChild(li);
      });
    }
  }
}
