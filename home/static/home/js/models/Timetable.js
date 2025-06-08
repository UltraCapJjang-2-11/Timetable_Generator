// models/Timetable.js
import { Course } from './Course.js'; // Course 클래스를 가져옵니다.

const colorPalette = ['#f28b82', '#fbbc04', '#fff475', '#ccff90', '#a7ffeb', '#cbf0f8', '#aecbfa', '#d7aefb', '#fdcfe8'];

/**
 * 개별 시간표를 나타내는 클래스.
 * Course 객체의 배열을 관리하고 관련 유틸리티 메서드를 제공합니다.
 */
export class Timetable {
    /**
     * @param {Array<Course>} courses 이 시간표를 구성하는 Course 객체의 배열
     * @param {object} options 추가 옵션 (예: title)
     */
    constructor(courses = [], options = {}) {
        this.courses = courses; // Course 객체의 배열
        this.title = options.title || '새 시간표';

        // 생성 시점에 주요 정보를 미리 계산하여 속성으로 저장
        this.totalCredits = this.calculateTotalCredits();
        this.majorCredits = this.calculateCreditsByMajor();
        this.id = this.generateId(); // 강의 ID들을 조합하여 고유 ID 생성
    }

    /**
     * 시간표에 포함된 강의들의 ID를 정렬하고 조합하여 고유한 식별자를 생성합니다.
     * @returns {string} 예: "101-203-450"
     */
    generateId() {
        return this.courses.map(c => c.id).sort((a, b) => a - b).join('-');
    }

    /**
     * 시간표의 총 이수 학점을 계산합니다.
     * @returns {number}
     */
    calculateTotalCredits() {
        return this.courses.reduce((sum, course) => sum + course.credits, 0);
    }

    /**
     * 전공 학점만 계산합니다.
     * @returns {number}
     */
    calculateCreditsByMajor() {
        return this.courses
            .filter(course => course.categoryName.includes('전공'))
            .reduce((sum, course) => sum + course.credits, 0);
    }

    /**
     * 시간표 내 강의들의 시간 충돌 여부를 확인합니다.
     * @returns {boolean} 충돌이 있으면 true, 없으면 false.
     */
    hasConflicts() {
        for (let i = 0; i < this.courses.length; i++) {
            for (let j = i + 1; j < this.courses.length; j++) {
                if (this.courses[i].conflictsWith(this.courses[j])) {
                    // 충돌하는 강의 정보를 로그로 남길 수도 있습니다.
                    console.warn('Conflict detected:', this.courses[i].name, 'and', this.courses[j].name);
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * 이 Timetable 인스턴스를 API 저장용 포맷으로 변환합니다.
     * @returns {object} API /save_timetable/ 엔드포인트가 기대하는 형식의 객체
     */
    toSaveFormat() {

        return {
            title: this.title,
            // 백엔드에서 다시 계산하더라도, 현재 아는 정보를 포함해서 보냅니다.
            total_credits: this.totalCredits,
            major_credits: this.majorCredits,
            // 각 Course 객체도 toObject()를 호출하여 순수 객체로 변환합니다.
            courses: this.courses.map(course => course.toObject())
        };
    }

    /**
     * 이 Timetable 인스턴스를 API 전송에 적합한 순수 객체로 변환합니다.
     * @returns {object}
     */
    toObject() {
        return {
            title: this.title,
            total_credits: this.totalCredits,
            major_credits: this.majorCredits,
            courses: this.courses.map(course => course.toObject())
        };
    }

    /**
     * 주어진 DOM 요소에 시간표를 직접 렌더링합니다.
     * @param {HTMLElement} gridBodyElement 시간표 셀들이 있는 tbody 요소
     */
    render(gridBodyElement) {
        // 1. 그리드 초기화
        gridBodyElement.querySelectorAll(".timetable-cell").forEach(cell => {
            cell.innerHTML = "";
            cell.style.backgroundColor = ''; // 배경색도 초기화
        });

        // 2. 각 강의에 색상 할당
        const courseColors = {};
        this.courses.forEach((course, index) => {
            courseColors[course.id] = colorPalette[index % colorPalette.length];
        });

        // 3. 그리드에 강의 렌더링
        this.courses.forEach(course => {
            const courseColor = courseColors[course.id];
            course.schedules.forEach(schedule => {
                const dayIndex = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }[schedule.day] ?? -1;
                if (dayIndex === -1) return;

                const timeSlots = schedule.times.map(t => t + 8); // 시간대 오프셋 적용
                timeSlots.forEach(slot => {
                    const cell = gridBodyElement.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
                    if (cell) {
                        cell.style.backgroundColor = courseColor;
                        const lectureDiv = document.createElement('div');
                        lectureDiv.className = 'lecture';
                        lectureDiv.innerHTML = `${course.name}<br><small>${schedule.location || ''}</small>`;
                        cell.appendChild(lectureDiv);
                    }
                });
            });
        });
    }
}