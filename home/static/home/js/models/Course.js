/**
 * 서버 API로부터 받은 강의 데이터를 캡슐화하고,
 * 관련된 유틸 메서드를 제공하는 클래스입니다.
 */
export class Course {
    /**
     * @param {object} apiData 서버에서 받은 원본 강의 데이터 객체. null일 수 있습니다.
     */
    constructor(apiData) {
        const data = apiData || {};

        this.id = data.course_id || null;
        this.name = data.course_name || '';
        this.code = data.course_code || '';
        this.section = data.section || '';
        this.credits = data.credits || 0;
        this.targetYear = data.target_year || '';
        this.instructor = data.instructor_name || '';
        this.capacity = data.capacity || 0;
        this.deptName = data.dept_name || '';
        this.categoryName = data.category_name || '';
        this.semester = data.semester || '';

        const scheduleData = data.schedules || [];
        this.schedules = scheduleData.map(s => {
            // schedule 배열의 각 아이템(s)이 null일 경우를 대비합니다.
            const scheduleItem = s || {};
            const timeString = scheduleItem.times || '';

            return {
                day: scheduleItem.day || '',
                location: scheduleItem.location || '',
                // timeString이 비어있을 때 split되어 ['']가 되는 것을 방지하고,
                // parseInt 실패로 NaN이 되는 값을 필터링하여 숫자만 남깁니다.
                times: timeString ? timeString.split(',').map(t => parseInt(t, 10)).filter(n => !isNaN(n)) : []
            };
        });
    }

    /**
     * UI에 표시할 시간표 문자열을 반환합니다.
     * @returns {string} 예: "월 3,4<br>수 3,4"
     */
    getScheduleString() {
        if (!this.schedules || this.schedules.length === 0) {
            return '시간 정보 없음';
        }
        return this.schedules
            .map(s => `${s.day} ${s.times.join(',')}`)
            .join('<br>');
    }

    /**
     * 강의 전체 이름을 분반 정보와 함께 반환합니다.
     * @returns {string} 예: "캡스톤 디자인 (1분반)"
     */
    getFullTitle() {
        return `${this.name} (${this.section}분반)`;
    }

    /**
     * 다른 Course 객체와 시간표가 겹치는지 확인합니다.
     * @param {Course} otherCourse 비교할 다른 Course 객체
     * @returns {boolean} 겹치면 true, 아니면 false
     */
    conflictsWith(otherCourse) {
        for (const scheduleA of this.schedules) {
            for (const scheduleB of otherCourse.schedules) {
                // 요일이 같을 경우
                if (scheduleA.day === scheduleB.day) {
                    // 시간이 하나라도 겹치는지 확인
                    if (scheduleA.times.some(time => scheduleB.times.includes(time))) {
                        return true; // 충돌 발생
                    }
                }
            }
        }
        return false; // 충돌 없음
    }

    /**
     * 이 객체를 다시 순수 자바스크립트 객체로 변환합니다.
     * @returns {object}
     */
    toObject() {
        return {
            course_id: this.id,
            course_name: this.name,
            course_code: this.code,
            section: this.section,
            credits: this.credits,
            target_year: this.targetYear,
            instructor_name: this.instructor,
            capacity: this.capacity,
            dept_name: this.deptName,
            category_name: this.categoryName,
            semester: this.semester,
            schedules: this.schedules.map(s => ({
                day: s.day,
                location: s.location,
                times: s.times.join(',') // 다시 문자열로
            }))
        };
    }

    /**
     * 서버에서 받은 API 데이터 배열로부터 Course 객체 배열을 생성하는 정적 메서드
     * @param {Array<object>} apiDataArray
     * @returns {Array<Course>}
     */
    static createFromApiData(apiDataArray) {
        if (!Array.isArray(apiDataArray)) return [];
        return apiDataArray.map(data => new Course(data));
    }
}