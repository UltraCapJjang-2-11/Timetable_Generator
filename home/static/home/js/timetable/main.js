import { initChatbot } from './chatbot.js'; // 챗봇 모듈 임포트
import { Course } from '../models/Course.js';
import { Timetable } from '../models/Timetable.js';

/**
 * ----------------------------------------------------------------
 * 1. 상태 관리 (State Management)
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
let lastGeneratedTimetable = null; // 가장 최근에 생성된 시간표

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
 * 3. API 및 데이터 처리
 * ----------------------------------------------------------------
 */

function buildApiParams() {
    const params = new URLSearchParams();
    const totalCredits = constraints.total_credits || (constraints.major_credits + constraints.elective_credits) || 0;

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
    if (!lastGeneratedTimetable || lastGeneratedTimetable.courses.length === 0) {
        return { success: false, message: "저장할 시간표가 없습니다. 먼저 시간표를 생성해주세요." };
    }

    // 저장할 데이터 Format 생성
    const timetableData = lastGeneratedTimetable.toSaveFormat();


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
 * 4. UI 렌더링 및 조작
 * ----------------------------------------------------------------
 */

function applyTimetableToMiddlePanel() {
    const timetableIndexElem = document.getElementById("timetable-index");
    const gridBody = document.querySelector(".timetable tbody");

    if (timetables.length === 0) {
        timetableIndexElem.textContent = "0 / 0";
        lastGeneratedTimetable = null;
        // 그리드 클리어 로직도 render 메서드에 포함되므로 여기서 호출 가능
        new Timetable([]).render(gridBody);
        return;
    }

    // ✅ 3. 렌더링 로직을 Timetable 객체에 완전히 위임합니다.
    lastGeneratedTimetable = timetables[currentIndex];
    lastGeneratedTimetable.render(gridBody); // "이 시간표야, 저기(gridBody)에 네 자신을 그려줘"

    timetableIndexElem.textContent = `${currentIndex + 1} / ${timetables.length}`;
}

/**
 * ----------------------------------------------------------------
 * 5. 이벤트 핸들러 및 비즈니스 로직
 * ----------------------------------------------------------------
 */

function handleGenerateButtonClick() {
    constraints.total_credits = Number(document.getElementById("total-credits").value);
    constraints.major_credits = Number(document.getElementById("major-credits").value);
    constraints.elective_credits = Number(document.getElementById("elective-credits").value);
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
        const fixedCourses = lastGeneratedTimetable.courses.filter(course =>
            !excludeCoursesLower.some(exName => course.name.toLowerCase().trim().includes(exName))
        );
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


/**
 * ----------------------------------------------------------------
 * 6. 초기화 및 이벤트 리스너 바인딩
 * ----------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
    initChatbot();

    constraints.total_credits = Number(document.getElementById("total-credits").value);
    constraints.major_credits = Number(document.getElementById("major-credits").value);
    constraints.elective_credits = Number(document.getElementById("elective-credits").value);

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
});