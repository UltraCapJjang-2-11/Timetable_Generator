// utils/gpa.js
/**
 * gpa.js - GPA 계산 유틸리티
 * - 학점 문자(A+, A0, B+ ...)를 점수로 변환하여 가중 평균(GPA)을 계산합니다.
 */

// 학점 문자 → 점수 매핑
const gradeToPoint = {
  'A+': 4.5,
  'A0': 4.0,
  'B+': 3.5,
  'B0': 3.0,
  'C+': 2.5,
  'C0': 2.0,
  'D+': 1.5,
  'D0': 1.0,
  'F': 0.0,
};

/**
 * @typedef {Object} CourseForGpa
 * @property {string} grade - 등급 문자 (예: 'A+', 'B0', 'F')
 * @property {number|string} credit - 학점 (숫자 또는 숫자 문자열)
 */

/**
 * 강의 배열로부터 평점 평균(GPA)을 계산합니다.
 * - 유효한 등급과 학점만 합산합니다.
 * - 총 학점이 0이거나 입력이 비정상이면 '0.00'을 반환합니다.
 * @param {CourseForGpa[]} courses - 등급과 학점 정보를 가진 강의 목록
 * @returns {string} - 소수점 둘째 자리까지의 문자열
 */
export function calculateGpa(courses) {

    // 강의 배열이 비어있거나 배열이 아닌 경우 0.00 반환
    if (!Array.isArray(courses) || courses.length === 0) return '0.00';

    // 총 평점 점수 초기화
    let totalPoints = 0;
    // 총 학점 수 초기화
    let totalCreditsForGpa = 0;

    // 강의 배열을 순회하며 평점 점수와 학점 수를 계산
    for (const course of courses) {
        const point = gradeToPoint[course?.grade];
        const credit = Number(course?.credit);
        if (point !== undefined && !Number.isNaN(credit)) {
        totalPoints += point * credit;
        totalCreditsForGpa += credit;
        }
    }

    if (totalCreditsForGpa === 0) return '0.00';
    return (totalPoints / totalCreditsForGpa).toFixed(2);
}


