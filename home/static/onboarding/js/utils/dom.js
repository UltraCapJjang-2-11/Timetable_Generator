// utils/dom.js
/**
 * dom.js - DOM 선택 유틸리티
 * - `$`, `$$`로 querySelector, querySelectorAll을 축약 제공
 * - parent를 지정하면 해당 컨테이너 범위에서만 탐색
 */

/**
 * querySelector 단축 함수
 * @param {string} selector
 * @param {ParentNode} parent
 * @returns {Element|null}
 */
export function $(selector, parent = document) {
  return parent.querySelector(selector);
}

/**
 * querySelectorAll 단축 함수
 * @param {string} selector
 * @param {ParentNode} parent
 * @returns {NodeListOf<Element>}
 */
export function $$(selector, parent = document) {
  return parent.querySelectorAll(selector);
}


