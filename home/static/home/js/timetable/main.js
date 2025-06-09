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
    total_credits: 0,
    major_credits: 0,
    elective_credits: 0,
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
// 시간표 생성 시 고정 상태를 유지하기 위한 Set 변수
let pinnedCourseIdsToPreserve = new Set();

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

            // '고정' 상태를 복원
            if (pinnedCourseIdsToPreserve.size > 0) {
                timetables.forEach(timetable => {
                    timetable.courses.forEach(course => {
                        if (pinnedCourseIdsToPreserve.has(course.id)) {
                            course.isPinned = true;
                        }
                    });
                });
            }

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

    // 현재 시간표에서 고정된(pinned) 강의들의 ID를 수집합니다.
    if (timetableState.currentTimetable) {
        constraints.existing_courses = timetableState.currentTimetable.courses
            .filter(course => course.isPinned)
            .map(course => course.id);
    } else {
        constraints.existing_courses = [];
    }

    // 현재 고정된 강의 ID들을 저장합니다.
    pinnedCourseIdsToPreserve.clear(); // 이전 기록 초기화
    if (timetableState.currentTimetable) {
        timetableState.currentTimetable.courses.forEach(course => {
            if (course.isPinned) {
                pinnedCourseIdsToPreserve.add(course.id);
            }
        });
    }

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
        } else {
            constraints.existing_courses = [];
        }
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
            // 생성과 수정에 따라 다른 메시지 표시
            const message = constraints.is_modification 
                ? "시간표가 수정되었습니다! 마음에 드시나요?" 
                : "시간표가 생성되었습니다! 마음에 드시나요?";
            
            document.dispatchEvent(new CustomEvent('sendBotMessage', {
                detail: {
                    message: message,
                    buttons: [{ title: "저장하기", action: handleSaveRequest }]
                }
            }));
        }
    });
}

async function handleSaveRequest() {
    const result = await saveCurrentTimetable();
    
    // 시간표 생성 중처럼 잠시 표시되는 알림
    showProgressMessage(result.message, result.success);
}

function showProgressMessage(message, isSuccess = true) {
    const overlay = document.getElementById('progress-overlay');
    const messageText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');
    const progressCount = document.getElementById('progress-count');
    
    // 메시지 설정
    messageText.textContent = message;
    
    // 진행 바 숨기고 카운트 텍스트도 숨김
    progressBar.style.display = 'none';
    progressCount.style.display = 'none';
    
    // 오버레이 표시
    overlay.style.display = 'block';
    
    // 2초 후 자동으로 사라짐 (시간표 생성 완료 시와 동일)
    setTimeout(() => {
        overlay.style.display = 'none';
        // 다시 진행 바와 카운트 표시 (다음 시간표 생성을 위해)
        progressBar.style.display = 'block';
        progressCount.style.display = 'block';
    }, 2000);
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

// 새로운 간단한 미리보기 시스템
let currentPreviewCourse = null;

// 강의 미리보기 표시 함수
function showCoursePreview(course) {
    if (!course || !course.schedules) return;

    // 이미 같은 강의가 미리보기 중이면 무시
    if (currentPreviewCourse && currentPreviewCourse.id === course.id) {
        return;
    }

    // 현재 미리보기 설정
    currentPreviewCourse = course;

    // 색상 배열
    const colorPalette = ['#f28b82', '#fbbc04', '#fff475', '#ccff90', '#a7ffeb', '#cbf0f8', '#aecbfa', '#d7aefb', '#fdcfe8'];
    const currentCourseCount = timetableState.currentTimetable ? timetableState.currentTimetable.courses.length : 0;
    const previewColor = colorPalette[currentCourseCount % colorPalette.length];

    course.schedules.forEach(schedule => {
        const dayIndex = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }[schedule.day] ?? -1;
        if (dayIndex === -1) return;

        const timeSlots = schedule.times.split(',').map(t => parseInt(t, 10) + 8);

        timeSlots.forEach(slot => {
            const cell = document.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
            if (cell) {
                const hasExistingLecture = cell.querySelector('.lecture') !== null;
                
                cell.classList.add('course-preview');
                cell.dataset.previewCourse = course.id;
                
                const rgb = hexToRgb(previewColor);
                if (rgb) {
                    if (hasExistingLecture) {
                        cell.style.border = `3px solid ${previewColor}`;
                        cell.style.boxShadow = `0 0 8px rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.6)`;
                    } else {
                        cell.style.backgroundColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
                        cell.style.border = `2px solid ${previewColor}`;
                    }
                }
            }
        });
    });
}

// 강제로 모든 미리보기를 제거하는 함수 (더 강력한 버전)
function forceClearAllPreviews() {
    currentPreviewCourse = null;
    
    // 모든 미리보기 관련 클래스와 스타일을 제거
    document.querySelectorAll('.course-preview').forEach(cell => {
        cell.classList.remove('course-preview');
        delete cell.dataset.previewCourse;
        
        // 모든 인라인 스타일 제거
        cell.style.border = '';
        cell.style.boxShadow = '';
        cell.style.backgroundColor = '';
    });
    
    // 기존 방식으로도 한 번 더 정리
    clearCoursePreview();
}

// 강의 미리보기 제거 함수
function clearCoursePreview() {
    currentPreviewCourse = null;
    
    document.querySelectorAll('.course-preview').forEach(cell => {
        cell.classList.remove('course-preview');
        delete cell.dataset.previewCourse;
        
        const hasExistingLecture = cell.querySelector('.lecture') !== null;
        
        if (hasExistingLecture) {
            cell.style.border = '';
            cell.style.boxShadow = '';
        } else {
            cell.style.backgroundColor = '';
            cell.style.border = '';
            cell.style.boxShadow = '';
        }
    });
}

// 헥스 색상을 RGB로 변환하는 유틸리티 함수
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// 새로운 이벤트 핸들러들
function handleClearAllPreviews() {
    forceClearAllPreviews();
}

function handleShowCoursePreview(e) {
    const course = e.detail.course;
    showCoursePreview(course);
}

function handleHideCoursePreview(e) {
    // 시간표 영역으로 마우스가 이동했는지 확인
    const mouseEvent = e.originalEvent || e;
    const relatedTarget = mouseEvent.relatedTarget;
    
    if (relatedTarget && (
        relatedTarget.closest('.middle-panel') || 
        relatedTarget.closest('.timetable') ||
        relatedTarget.classList.contains('course-preview')
    )) {
        // 시간표 영역으로 이동한 경우 미리보기 유지
        return;
    }
    
    // 다른 곳으로 이동한 경우만 제거
    clearCoursePreview();
}

// 강의 고정 상태를 토글하는 함수
function handleTogglePin(e) {
    const courseIdToToggle = e.detail.courseId;
    if (!timetableState.currentTimetable) return;

    // Timetable 모델의 메서드를 사용하여 상태 변경
    timetableState.currentTimetable.togglePin(courseIdToToggle);

    // 변경된 상태를 right_panel에 즉시 반영하기 위해 이벤트를 다시 발생
    document.dispatchEvent(new CustomEvent('timetableRendered', {
        detail: { timetable: timetableState.currentTimetable }
    }));
}

/**
 * ----------------------------------------------------------------
 * 6. 초기화 및 이벤트 리스너 바인딩
 * ----------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {

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

    // 시간표 영역에 간단한 마우스 이벤트 추가
    const timetableContainer = document.querySelector('.middle-panel');
    if (timetableContainer) {
        timetableContainer.addEventListener('mouseleave', () => {
            forceClearAllPreviews();
        });
    }

    // 새로운 미리보기 이벤트 리스너
    document.addEventListener('clearAllPreviews', handleClearAllPreviews);
    document.addEventListener('showCoursePreview', handleShowCoursePreview);
    document.addEventListener('hideCoursePreview', handleHideCoursePreview);
    
    document.addEventListener('requestTimetableAction', handleTimetableActionRequest);
    document.addEventListener('requestTimetableSave', handleSaveRequest);
    document.addEventListener('addCourseToView', handleAddCourse);
    document.addEventListener('removeCourseFromView', handleRemoveCourse);
    document.addEventListener('togglePinCourse', handleTogglePin);
});