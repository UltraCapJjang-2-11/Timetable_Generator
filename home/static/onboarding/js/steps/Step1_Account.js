// Step1_Account.js
/**
 * 온보딩 Step 1 - 계정 생성(회원가입) 단계 UI 로직.
 * - 비밀번호 표시 토글, 비밀번호 일치 검사, 입력 피드백 표시.
 * - 가입 버튼 클릭 시 백엔드 `api.register()`를 호출하여 결과에 따라 다음 단계로 진행하거나 에러를 노출합니다.
 * - 외부에서는 `mount(container)`로 이벤트를 바인딩하고, `destroy()`로 정리합니다.
 */

import { api } from '../api.js';

let arePasswordsMatching = false;
let containerRef = null;
let bound = {
  onPwdInput: null,
  onPwdConfirmInput: null,
  onTogglePwd: null,
  onTogglePwdC: null,
  onSubmit: null,
};

/**
 * 피드백 영역에 텍스트 또는 항목 목록을 렌더링합니다.
 * @param {HTMLElement} container - 스텝 루트 컨테이너
 * @param {string} elementId - 피드백 요소의 id (예: 'email-feedback')
 * @param {string|string[]} message - 표시할 메시지(문자열 또는 문자열 배열)
 * @param {string} [color='red'] - 텍스트 색상
 */
function showFeedback(container, elementId, message, color = 'red') {
  const feedbackEl = container.querySelector(`#${elementId}`);
  if (!feedbackEl) return;
  feedbackEl.style.color = color;
  if (Array.isArray(message)) {
    const listItems = message.map(item => `<li>${item}</li>`).join('');
    feedbackEl.innerHTML = `<ul class="list-unstyled mb-0">${listItems}</ul>`;
  } else {
    feedbackEl.textContent = message || '';
  }
}

/**
 * 화면의 모든 피드백 영역을 초기화합니다.
 * @param {HTMLElement} container
 */
function clearAllFeedbacks(container) {
  showFeedback(container, 'email-feedback', '');
  showFeedback(container, 'password-feedback', '');
  showFeedback(container, 'password-confirm-feedback', '');
}

/**
 * 비밀번호 입력 필드의 표시/숨김을 토글합니다.
 * @param {HTMLElement} container
 * @param {string} inputId - 비밀번호 input 요소의 id
 * @param {string} buttonId - 토글 버튼 요소의 id (아이콘은 내부 i 태그)
 */
function togglePasswordVisibility(container, inputId, buttonId) {
  const input = container.querySelector(`#${inputId}`);
  const buttonIcon = container.querySelector(`#${buttonId} i`);
  if (!input || !buttonIcon) return;
  if (input.type === 'password') {
    input.type = 'text';
    buttonIcon.classList.replace('bi-eye', 'bi-eye-slash');
  } else {
    input.type = 'password';
    buttonIcon.classList.replace('bi-eye-slash', 'bi-eye');
  }
}

/**
 * 비밀번호와 확인 입력값이 일치하는지 검사하고 피드백을 표시합니다.
 * 내부 상태 `arePasswordsMatching`을 갱신합니다.
 * @param {HTMLElement} container
 */
function checkPasswordMatch(container) {
  const password = container.querySelector('#password')?.value || '';
  const passwordConfirm = container.querySelector('#password-confirm')?.value || '';
  if (passwordConfirm === '') {
    showFeedback(container, 'password-confirm-feedback', '');
    arePasswordsMatching = false;
    return;
  }
  if (password === passwordConfirm) {
    showFeedback(container, 'password-confirm-feedback', '✓ 비밀번호가 일치합니다.', 'green');
    arePasswordsMatching = true;
  } else {
    showFeedback(container, 'password-confirm-feedback', '비밀번호가 일치하지 않습니다.', 'red');
    arePasswordsMatching = false;
  }
}

/**
 * 가입 버튼 핸들러: 입력 검증 후 회원가입 API를 호출합니다.
 * 성공 시 `step-success` 커스텀 이벤트를 발행합니다.
 * @param {Event} e
 */
async function handleRegistration(e) {
  e.preventDefault();
  const container = containerRef;
  clearAllFeedbacks(container);
  const email = container.querySelector('#email')?.value || '';
  const password = container.querySelector('#password')?.value || '';
  if (!email || !password) {
    showFeedback(container, 'email-feedback', '이메일과 비밀번호를 모두 입력해주세요.');
    return;
  }
  if (!arePasswordsMatching) {
    showFeedback(container, 'password-confirm-feedback', '비밀번호가 일치하지 않습니다.');
    return;
  }
  try {
    const data = await api.register(email, password);
    if (data.status === 'success') {
      container.dispatchEvent(new CustomEvent('step-success', { bubbles: true }));
    } else {
      if (data.field === 'email') {
        showFeedback(container, 'email-feedback', data.message);
      } else if (data.field === 'password') {
        showFeedback(container, 'password-feedback', data.message);
      } else {
        showFeedback(container, 'email-feedback', data.message);
      }
    }
  } catch (err) {
    console.error('Registration Error:', err);
    showFeedback(container, 'email-feedback', '서버 통신 중 오류가 발생했습니다.');
  }
}

/**
 * Step 1 UI를 컨테이너에 마운트하고 이벤트를 바인딩합니다.
 * @param {HTMLElement} container - 스텝 루트 컨테이너
 */
export function mount(container) {
  containerRef = container;
  const pwd = container.querySelector('#password');
  const pwdC = container.querySelector('#password-confirm');
  const togglePwd = container.querySelector('#toggle-password-btn');
  const togglePwdC = container.querySelector('#toggle-password-confirm-btn');
  const nextBtn = container.querySelector('.next-btn');

  bound.onPwdInput = () => checkPasswordMatch(container);
  bound.onPwdConfirmInput = () => checkPasswordMatch(container);
  bound.onTogglePwd = () => togglePasswordVisibility(container, 'password', 'toggle-password-btn');
  bound.onTogglePwdC = () => togglePasswordVisibility(container, 'password-confirm', 'toggle-password-confirm-btn');
  bound.onSubmit = handleRegistration;

  pwd?.addEventListener('input', bound.onPwdInput);
  pwdC?.addEventListener('input', bound.onPwdConfirmInput);
  togglePwd?.addEventListener('click', bound.onTogglePwd);
  togglePwdC?.addEventListener('click', bound.onTogglePwdC);
  nextBtn?.addEventListener('click', bound.onSubmit);
}

/**
 * 마운트 시 등록한 이벤트 리스너와 내부 상태를 정리합니다.
 */
export function destroy() {
  const container = containerRef;
  const pwd = container?.querySelector('#password');
  const pwdC = container?.querySelector('#password-confirm');
  const togglePwd = container?.querySelector('#toggle-password-btn');
  const togglePwdC = container?.querySelector('#toggle-password-confirm-btn');
  const nextBtn = container?.querySelector('.next-btn');

  pwd?.removeEventListener('input', bound.onPwdInput);
  pwdC?.removeEventListener('input', bound.onPwdConfirmInput);
  togglePwd?.removeEventListener('click', bound.onTogglePwd);
  togglePwdC?.removeEventListener('click', bound.onTogglePwdC);
  nextBtn?.removeEventListener('click', bound.onSubmit);

  containerRef = null;
  arePasswordsMatching = false;
  bound = { onPwdInput: null, onPwdConfirmInput: null, onTogglePwd: null, onTogglePwdC: null, onSubmit: null };
}
