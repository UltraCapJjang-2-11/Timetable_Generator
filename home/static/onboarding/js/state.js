/**
 * 온보딩 전역 상태 저장소 (Single Source of Truth)
 * - Step 2 PDF 분석 결과(studentInfo, courseHistory, imageUrls)
 * - Step 3에서 최종 확정된 학사 정보(finalAcademicInfo)
 * 외부에서는 제공되는 Getter/Setter를 통해서만 접근/변경합니다.
 */
let state = {
  // Step 2의 PDF 분석 결과 저장
  studentInfo: null,      // ex) { 대학, 학과(전공), 학번, 성명, 학년, 이수학기, 교과적용년도 }
  courseHistory: [],      // ex) [{ year, term, course_code, course_name, credit, course_type, grade }]
  imageUrls: null,        // ex) { original: string[], student_info: string, course_history: string }

  // Step 3에서 최종 확인된 학사 정보
  finalAcademicInfo: null,
};

// Getters
/**
 * 학생 정보(snapshot)를 반환합니다.
 * @returns {null|{[key:string]: any}}
 */
export function getStudentInfo() {
  return state.studentInfo ? { ...state.studentInfo } : null;
}

/**
 * 수강 이력 배열(snapshot)을 반환합니다.
 * @returns {Array<object>} shallow copy 배열
 */
export function getCourseHistory() {
  return Array.isArray(state.courseHistory) ? state.courseHistory.map(c => ({ ...c })) : [];
}

/**
 * PDF 이미지 URL 묶음(snapshot)을 반환합니다.
 * @returns {null|{original:string[], student_info?:string, course_history?:string}}
 */
export function getImageUrls() {
  return state.imageUrls ? { ...state.imageUrls } : null;
}

/**
 * 최종 확정된 학사 정보(snapshot)를 반환합니다.
 * @returns {null|{[key:string]: any}}
 */
export function getFinalAcademicInfo() {
  return state.finalAcademicInfo ? { ...state.finalAcademicInfo } : null;
}

// Setters
/**
 * PDF 분석 결과를 상태에 반영합니다.
 * @param {{ parsed_data?: any, image_urls?: any }} payload
 */
export function setPdfResult(payload) {
  // payload: { parsed_data, image_urls }
  if (!payload) return;

  const parsed = payload.parsed_data || {};
  const images = payload.image_urls || null;

  // 학생 정보 매핑 (키 이름은 백엔드 파서 결과에 따라 조정)
  const studentInfo = parsed['학생정보'] || null;

  // 이수 내역 매핑
  const courseRows = parsed['학점이수현황'] || [];
  const normalizedCourses = Array.isArray(courseRows)
    ? courseRows.map(course => ({
        // 서버에서 제공하는 대표 course PK 보존 (id 또는 course_id)
        id: course['id'] ?? course['course_id'] ?? null,
        course_id: course['course_id'] ?? course['id'] ?? null,
        year: course['년도'],
        term: course['학기'],
        course_code: course['교과목번호'],
        course_name: course['교과목명'],
        credit: course['학점'],
        course_type: course['이수구분'],
        grade: course['성적'],
      }))
    : [];

  state.studentInfo = studentInfo ? { ...studentInfo } : null;
  state.courseHistory = normalizedCourses;
  state.imageUrls = images ? { ...images } : null;
}

/**
 * 수강 이력 배열을 상태에 저장합니다.
 * @param {Array<object>} updatedCourses
 */
export function updateCourseHistory(updatedCourses) {
  state.courseHistory = Array.isArray(updatedCourses) ? updatedCourses.map(c => ({ ...c })) : [];
}

/**
 * 최종 학사 정보를 상태에 저장합니다.
 * @param {object|null} info
 */
export function setFinalAcademicInfo(info) {
  state.finalAcademicInfo = info ? { ...info } : null;
}

// 개발/디버깅용: 상태를 읽기 전용으로 노출
/**
 * 상태의 깊은 복사본을 반환합니다(디버깅용).
 * @returns {any}
 */
export function __getStateSnapshot() {
  return JSON.parse(JSON.stringify(state));
}


