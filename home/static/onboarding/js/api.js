/**
 * API 유틸리티 모듈
 * - JSON GET/POST, Form POST 래퍼 제공
 * - CSRF 쿠키 자동 첨부 및 same-origin 자격 증명 사용
 * - 4xx는 비즈니스 오류로 간주하여 예외를 던지지 않고 payload를 그대로 반환
 * - 5xx(서버 오류)만 예외를 발생시켜 상위에서 처리하도록 함
 */
import { getCookie } from './utils/cookies.js';

/**
 * GET JSON 요청을 수행합니다.
 * @param {string} url - 요청 URL
 * @returns {Promise<any>} - 파싱된 JSON 응답
 * @throws {Error} - 응답 상태가 2xx가 아니고, 서버가 메시지를 제공하는 경우
 */
async function getJson(url) {
  const resp = await fetch(url, { credentials: 'same-origin' });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data?.message || `GET ${url} failed`);
  return data;
}

/**
 * JSON 본문을 포함한 POST 요청을 수행합니다.
 * - 4xx 범주의 응답은 비즈니스 로직 오류로 간주하여 예외를 던지지 않고 data를 반환합니다.
 * - 5xx 범주의 응답은 예외를 던집니다.
 * @param {string} url - 요청 URL
 * @param {object} payload - 전송할 JSON 객체
 * @returns {Promise<any>} - 파싱된 JSON 응답 (성공/실패 메시지 포함 가능)
 * @throws {Error} - 5xx 서버 오류
 */
async function postJson(url, payload) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    credentials: 'same-origin',
    body: JSON.stringify(payload || {}),
  });
  const data = await resp.json();
  // 4xx 오류는 비즈니스 로직 오류이므로 예외를 던지지 않고 데이터 반환
  // 5xx 서버 오류만 예외 처리
  if (!resp.ok && resp.status >= 500) {
    throw new Error(data?.message || `POST ${url} failed`);
  }
  return data;
}

/**
 * multipart/form-data로 파일 등을 업로드하는 POST 요청을 수행합니다.
 * @param {string} url - 요청 URL
 * @param {FormData} formData - 전송할 FormData 인스턴스
 * @returns {Promise<any>} - 파싱된 JSON 응답
 * @throws {Error} - 응답 상태가 2xx가 아닌 경우
 */
async function postForm(url, formData) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    credentials: 'same-origin',
    body: formData,
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data?.message || `POST ${url} failed`);
  return data;
}

// API Endpoint wrappers
/**
 * 온보딩 플로우에서 사용하는 API 엔드포인트 래퍼
 */
export const api = {
  /**
   * 회원 등록 요청
   * @param {string} email
   * @param {string} password
   */
  register: (email, password) => postJson('/onboarding/register/', { email, password }),
  /**
   * PDF 업로드 및 분석 요청
   * @param {FormData} formData - pdf_file을 포함한 FormData
   */
  processPdf: (formData) => postForm('/onboarding/process-pdf/', formData),
  /**
   * 학사 정보 저장
   * @param {object} payload - 대학/학과/학번/성명/학년/이수학기/교과적용년도 등
   */
  saveAcademicInfo: (payload) => postJson('/onboarding/save-academic-info/', payload),
  /**
   * 이수 내역 저장
   * @param {Array<{course_id:number|null, grade:string}>} courses
   */
  saveTranscripts: (courses) => postJson('/onboarding/save-transcripts/', { courses }),
  /**
   * 졸업 요건 평가 요청
   */
  evaluateGraduation: () => getJson('/onboarding/evaluate-graduation/'),
};
