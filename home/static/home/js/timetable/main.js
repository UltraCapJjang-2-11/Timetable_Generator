import { initChatbot } from './chatbot.js'; // 챗봇 모듈 임포트
import { Course } from '../models/Course.js';
import { Timetable } from '../models/Timetable.js';
import { timetableState } from './state.js';

/**
 * ----------------------------------------------------------------
 * 상태 관리 (State Management)
 * - 애플리케이션의 전역 상태를 관리하는 변수들
 * ----------------------------------------------------------------
 */

const constraints = {
    total_credits: 18,
    major_credits: 9,
    elective_credits: 9,
    required_courses: [],
    free_days: [],
    avoid_times: [],
    avoid_time_ranges: [],
    only_time_ranges: [],
    exclude_courses: [],
    specific_avoid_times: [],
    specific_avoid_time_ranges: [],
    is_modification: false,
    existing_courses: []
};
let timetables = [];  // 생성된 Timetable 객체의 배열
let currentIndex = 0;  // 현재 렌더링(선택된)시간표의 인덱스

/**
 * ----------------------------------------------------------------
 * 2. 유틸리티 함수 (Utility Functions)
 * ----------------------------------------------------------------
 */

function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
    }
    return null;
}

/**
 * ----------------------------------------------------------------
 * API 및 데이터 처리
 * ----------------------------------------------------------------
 */

function buildApiParams() {
    const params = new URLSearchParams();

    const totalCredits = (constraints.major_credits || 0) + (constraints.elective_credits || 0);

    params.append("total_credits", totalCredits);
    params.append("major_credits", constraints.major_credits || 0);
    params.append("elective_credits", constraints.elective_credits || 0);

    ['existing_courses', 'free_days', 'required_courses', 'exclude_courses'].forEach(key => {
        constraints[key]?.forEach(value => params.append(`${key}[]`, value));
    });

    ['specific_avoid_times', 'specific_avoid_time_ranges'].forEach(key => {
        constraints[key]?.forEach(value => params.append(`${key}[]`, JSON.stringify(value)));
    });

    return params;
}

function setupSseConnection(url, onComplete) {
    const progressOverlay = document.getElementById("progress-overlay");
    const progressText = document.getElementById("progress-text");
    progressOverlay.style.display = "block";
    progressText.textContent = "시간표 생성 중…";

    const evtSource = new EventSource(url);

    evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.progress === "완료") {

            timetables = data.timetables.map(timetableCourseData => {
                const courses = Course.createFromApiData(timetableCourseData);
                return new Timetable(courses); // Course 배열로 Timetable 인스턴스 생성
            });

            currentIndex = 0;
            if (constraints.is_modification) {
                constraints.is_modification = false;
            }
            setTimeout(() => progressOverlay.style.display = "none", 800);
            applyTimetableToMiddlePanel();
            evtSource.close();
            if (onComplete) onComplete(true);
        } else {
            progressText.textContent = (data.processed !== undefined && data.found !== undefined)
                ? `처리된 조합: ${data.processed}, 후보: ${data.found}`
                : "시간표 생성 중...";
        }
    };

    evtSource.onerror = () => {
        progressText.textContent = "오류 발생";
        evtSource.close();
        setTimeout(() => { progressOverlay.style.display = "none"; }, 2000);
        if (onComplete) onComplete(false);
    };
}

async function saveCurrentTimetable() {
    if (!timetableState.currentTimetable || timetableState.currentTimetable.courses.length === 0) {
        return { success: false, message: "저장할 시간표가 없습니다. 먼저 시간표를 생성해주세요." };
    }

    // 저장할 데이터 Format 생성
    const timetableData = timetableState.currentTimetable.toSaveFormat();

    // API(시간표 저장) 요청
    try {
        const response = await fetch('/save_timetable/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(timetableData)
        });
        const result = await response.json();
        return {
            success: response.ok && result.success,
            message: response.ok && result.success ? "시간표가 성공적으로 저장되었습니다!" : `저장 실패: ${result.error || "알 수 없는 오류"}`
        };
    } catch (error) {
        return { success: false, message: `저장 중 오류가 발생했습니다: ${error.message}` };
    }
}

/**
 * ----------------------------------------------------------------
 * UI 렌더링 및 조작
 * ----------------------------------------------------------------
 */

function applyTimetableToMiddlePanel() {
    const timetableIndexElem = document.getElementById("timetable-index");
    const gridBody = document.querySelector(".timetable tbody");

    if (timetables.length === 0) {
        timetableIndexElem.textContent = "0 / 0";
        timetableState.currentTimetable = null;
        new Timetable([]).render(gridBody);
        // timetableRendered 이벤트를 빈 상태에서도 발생시켜 우측 패널을 업데이트
        document.dispatchEvent(new CustomEvent('timetableRendered', {
            detail: { timetable: null }
        }));
        return;
    }

    timetableState.currentTimetable = timetables[currentIndex];
    timetableState.currentTimetable.render(gridBody);

    timetableIndexElem.textContent = `${currentIndex + 1} / ${timetables.length}`;

    document.dispatchEvent(new CustomEvent('timetableRendered', {
        detail: { timetable: timetableState.currentTimetable }
    }));
}

/**
 * ----------------------------------------------------------------
 * 5. 이벤트 핸들러 및 비즈니스 로직
 * ----------------------------------------------------------------
 */

function handleGenerateButtonClick() {
    constraints.major_credits = Number(document.getElementById("major-credits").value);
    constraints.elective_credits = Number(document.getElementById("elective-credits").value);
    constraints.required_courses = Array.from(document.querySelectorAll(".required-courses input:checked")).map(cb => cb.value);
    constraints.free_days = Array.from(document.querySelectorAll(".day-options input:checked")).map(cb => cb.value);
    constraints.existing_courses = [];

    const params = buildApiParams();
    setupSseConnection(`/generate_timetable_stream/?${params.toString()}`);
}

function handleTimetableActionRequest(e) {
    const parsedData = e.detail;
    
    if (parsedData.is_modification) {
        // 시간표 수정의 경우: 기존 제약조건 + 새로운 제약조건
        constraints.is_modification = true;
        
        // 새로운 제약조건만 업데이트 (기존 조건 유지)
        Object.keys(parsedData).forEach(key => {
            if (parsedData[key] !== undefined && key !== 'is_modification') {
                constraints[key] = parsedData[key];
            }
        });
        
        const excludeCoursesLower = (constraints.exclude_courses || []).map(name => name.toLowerCase().trim());
        if (timetableState.currentTimetable) {
            const fixedCourses = timetableState.currentTimetable.courses.filter(course =>
                !excludeCoursesLower.some(exName => course.name.toLowerCase().trim().includes(exName))
            );
            constraints.existing_courses = fixedCourses.map(course => String(course.id));
        }
        constraints.existing_courses = fixedCourses.map(course => String(course.id));
    } else {
        // 새로운 시간표 생성의 경우: 모든 제약조건을 새로 설정
        constraints.is_modification = false;
        constraints.existing_courses = [];
        
        // 모든 제약조건을 새로 설정 (기존 조건 초기화)
        Object.keys(constraints).forEach(key => {
            if (parsedData[key] !== undefined) {
                constraints[key] = parsedData[key];
            } else if (key !== 'total_credits' && key !== 'is_modification') {
                // total_credits는 유지하고, 나머지는 초기화
                if (key === 'free_days' || key === 'required_courses' || key === 'avoid_times' || 
                    key === 'avoid_time_ranges' || key === 'only_time_ranges' || key === 'exclude_courses' ||
                    key === 'specific_avoid_times' || key === 'specific_avoid_time_ranges') {
                    constraints[key] = [];
                }
            }
        });
    }

    document.getElementById('major-credits').value = constraints.major_credits;
    document.getElementById('elective-credits').value = constraints.elective_credits;

    const params = buildApiParams();
    setupSseConnection(`/generate_timetable_stream/?${params.toString()}`, (success) => {
        if (success) {
            document.dispatchEvent(new CustomEvent('sendBotMessage', {
                detail: {
                    message: "시간표가 생성(수정)되었습니다! 마음에 드시나요?",
                    buttons: [{ title: "저장하기", action: handleSaveRequest }]
                }
            }));
        }
    });
}

async function handleSaveRequest() {
    const result = await saveCurrentTimetable();
    document.dispatchEvent(new CustomEvent('sendBotMessage', {
        detail: { message: result.message }
    }));
}

function handleAddCourse(e) {
    // detail에서 Course 객체를 직접 받지 않고, 순수 객체를 받아 Course 인스턴스로 변환합니다.
    const courseToAdd = e.detail.course;

    if (!timetableState.currentTimetable) {
        // 현재 시간표가 없으면, 이 강의 하나만 있는 새 시간표를 만듭니다.
        const newTimetable = new Timetable([courseToAdd]);
        timetables = [newTimetable];
        currentIndex = 0;
        applyTimetableToMiddlePanel();
        return;
    }

    const success = timetableState.currentTimetable.addCourse(courseToAdd);
    if (success) {
        applyTimetableToMiddlePanel(); // re-render and re-dispatch event
    } else {
        alert("시간이 겹치는 강의는 추가할 수 없습니다.");
    }
}

function handleRemoveCourse(e) {
    const courseIdToRemove = e.detail.courseId;
    if (!timetableState.currentTimetable) return;

    timetableState.currentTimetable.removeCourse(courseIdToRemove);
    applyTimetableToMiddlePanel(); // re-render and re-dispatch event
}

// 강의 시간 미리보기 표시 함수
function handlePreviewCourse(e) {
    const course = e.detail.course;
    if (!course || !course.schedules) return;

    course.schedules.forEach(schedule => {
        const dayIndex = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }[schedule.day] ?? -1;
        if (dayIndex === -1) return;

        // times는 "3,4" 같은 문자열이므로 다시 배열로 변환
        const timeSlots = schedule.times.split(',').map(t => parseInt(t, 10) + 8);

        timeSlots.forEach(slot => {
            const cell = document.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
            if (cell) {
                // ✅ 미리보기를 위한 특별한 CSS 클래스를 추가합니다.
                cell.classList.add('preview-cell');
            }
        });
    });
}

// 모든 미리보기를 지우는 함수
function handleClearPreview() {
    // 'preview-cell' 클래스를 가진 모든 셀을 찾아서 클래스를 제거합니다.
    document.querySelectorAll('.preview-cell').forEach(cell => {
        cell.classList.remove('preview-cell');
    });
}


/**
 * ----------------------------------------------------------------
 * 6. 초기화 및 이벤트 리스너 바인딩
 * ----------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
    initChatbot();

    document.getElementById("generate-btn")?.addEventListener("click", handleGenerateButtonClick);
    document.getElementById("save-timetable-btn")?.addEventListener("click", handleSaveRequest);
    document.getElementById("prev-timetable")?.addEventListener("click", () => {
        if (currentIndex > 0) {
            currentIndex--;
            applyTimetableToMiddlePanel();
        }
    });
    document.getElementById("next-timetable")?.addEventListener("click", () => {
        if (currentIndex < timetables.length - 1) {
            currentIndex++;
            applyTimetableToMiddlePanel();
        }
    });

    document.addEventListener('requestTimetableAction', handleTimetableActionRequest);
    document.addEventListener('requestTimetableSave', handleSaveRequest);
    document.addEventListener('addCourseToView', handleAddCourse);
    document.addEventListener('removeCourseFromView', handleRemoveCourse);
    document.addEventListener('previewCourse', handlePreviewCourse);
    document.addEventListener('clearPreview', handleClearPreview);
});