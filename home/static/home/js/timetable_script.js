// 전역 변수: 강좌 색상 관리 및 색상 팔레트
var lectureColors = {};
var colorPalette = ['#f28b82', '#fbbc04', '#fff475', '#ccff90', '#a7ffeb', '#cbf0f8', '#aecbfa', '#d7aefb', '#fdcfe8'];
function convertDayToIndex(day) {
  const days = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
  return days[day] !== undefined ? days[day] : -1;
}

// 채팅·버튼 양쪽에서 누적 관리할 제약조건 (DOM 로드 후 초기화)
window.constraints = {
  total_credits:    18,  // 기본값으로 설정, DOM 로드 후 실제 값으로 업데이트
  major_credits:    9,   // 기본값으로 설정, DOM 로드 후 실제 값으로 업데이트
  elective_credits: 9,   // 기본값으로 설정, DOM 로드 후 실제 값으로 업데이트
  required_courses: [],
  free_days:        [],
  avoid_times:      [],
  avoid_time_ranges:[],
  only_time_ranges: [],
  exclude_courses:  [],
  is_modification: false
};
window.existingCourses = []; // Manually added courses from left panel OR courses to fix for modification
window.lastGeneratedTimetable = null; // Store the full data of the last displayed timetable
window.currentTimetableCourseIds = []; // Store IDs of the last displayed timetable

// Modified: Accepts an optional array of course IDs to use for the 'existing_courses' parameter.
// If not provided, defaults to the global window.existingCourses (manually added).
function buildParamsFromConstraints(idsToUse) {
  console.log("[buildParamsFromConstraints] Received idsToUse:", JSON.stringify(idsToUse));
  
  // 초기화: 파라미터 객체 생성
  let params = new URLSearchParams();
  
  // 학점 정보 - total_credits를 우선적으로 사용하고, 없으면 major + elective로 계산
  let totalCredits = window.constraints.total_credits || 0;
  let majorCredits = window.constraints.major_credits || 0;
  let electiveCredits = window.constraints.elective_credits || 0;
  
  console.log("[buildParamsFromConstraints] 학점 정보 확인:");
  console.log("  window.constraints.total_credits:", window.constraints.total_credits);
  console.log("  window.constraints.major_credits:", window.constraints.major_credits);
  console.log("  window.constraints.elective_credits:", window.constraints.elective_credits);
  console.log("  계산된 totalCredits:", totalCredits);
  console.log("  계산된 majorCredits:", majorCredits);
  console.log("  계산된 electiveCredits:", electiveCredits);
  
  // total_credits가 설정되지 않았으면 major + elective로 계산
  if (totalCredits === 0) {
    totalCredits = majorCredits + electiveCredits;
    console.log("  total_credits가 0이므로 major + elective로 계산:", totalCredits);
  }
  
  params.append("total_credits", totalCredits);
  params.append("major_credits", majorCredits);
  params.append("elective_credits", electiveCredits);
  
  console.log("[buildParamsFromConstraints] 최종 전송 학점:");
  console.log("  total_credits:", totalCredits);
  console.log("  major_credits:", majorCredits);
  console.log("  elective_credits:", electiveCredits);
  
  // 기존 등록된 과목 처리
  console.log("[buildParamsFromConstraints] Processing idsToUse for existing_courses[]:", JSON.stringify(idsToUse));
  let existingCoursesToUse = idsToUse || window.existingCourses;
  existingCoursesToUse.forEach(id => {
    params.append("existing_courses[]", id);
  });
  
  // 공강 요일 처리
  if (window.constraints.free_days && window.constraints.free_days.length > 0) {
    window.constraints.free_days.forEach(day => {
      params.append("free_days[]", day);
    });
  }
  
  // 필수 과목 처리
  if (window.constraints.required_courses && window.constraints.required_courses.length > 0) {
    window.constraints.required_courses.forEach(course => {
      params.append("required_courses[]", course);
    });
  }
  
  // 제외할 과목 처리 (추가)
  console.log("[buildParamsFromConstraints] window.constraints.exclude_courses 확인:", window.constraints.exclude_courses);
  if (window.constraints.exclude_courses && window.constraints.exclude_courses.length > 0) {
    console.log("[buildParamsFromConstraints] 제외할 과목 처리 시작:", window.constraints.exclude_courses);
    window.constraints.exclude_courses.forEach(course => {
      params.append("exclude_courses[]", course);
      console.log("[buildParamsFromConstraints] 제외할 과목 추가됨:", course);
    });
    console.log("[buildParamsFromConstraints] 제외할 과목 추가 완료");
  } else {
    console.log("[buildParamsFromConstraints] 제외할 과목이 없거나 비어있음");
  }
  
  // 특정 시간대 공강 처리 (specific_avoid_times)
  if (window.constraints.specific_avoid_times && window.constraints.specific_avoid_times.length > 0) {
    console.log("[buildParamsFromConstraints] 특정 시간 공강 처리:", window.constraints.specific_avoid_times);
    window.constraints.specific_avoid_times.forEach(timeInfo => {
      if (timeInfo.day && timeInfo.hour) {
        params.append("specific_avoid_times[]", JSON.stringify({
          day: timeInfo.day,
          hour: timeInfo.hour
        }));
        console.log("[buildParamsFromConstraints] 특정 시간 추가:", timeInfo.day, timeInfo.hour);
      }
    });
  }
  
  // 특정 시간대 범위 공강 처리 (specific_avoid_time_ranges)
  if (window.constraints.specific_avoid_time_ranges && window.constraints.specific_avoid_time_ranges.length > 0) {
    console.log("[buildParamsFromConstraints] 특정 시간 범위 공강 처리:", window.constraints.specific_avoid_time_ranges);
    window.constraints.specific_avoid_time_ranges.forEach(rangeInfo => {
      if (rangeInfo.day && rangeInfo.start_hour && rangeInfo.end_hour) {
        params.append("specific_avoid_time_ranges[]", JSON.stringify({
          day: rangeInfo.day,
          start_hour: rangeInfo.start_hour,
          end_hour: rangeInfo.end_hour
        }));
        console.log("[buildParamsFromConstraints] 특정 시간 범위 추가:", rangeInfo.day, rangeInfo.start_hour + "-" + rangeInfo.end_hour);
      }
    });
  }
  
  console.log("최종 URL 파라미터:", params.toString());
  
  return params;
}
window.timetables   = [];
window.currentIndex = 0;

function applyTimetableToMiddlePanel() {
  const timetableCells = document.querySelectorAll(".timetable-cell");
  timetableCells.forEach(cell => cell.innerHTML = "");
  const timetableIndexElem = document.getElementById("timetable-index");

  if (window.timetables.length === 0) {
    timetableIndexElem.textContent = "0 / 0";
    return;
  }

  // Store the currently displayed timetable data and IDs
  window.lastGeneratedTimetable = window.timetables[window.currentIndex];
  window.currentTimetableCourseIds = window.lastGeneratedTimetable.map(c => String(c.course_id)); // Store as strings
  
  console.log("시간표 적용됨 - window.lastGeneratedTimetable 설정:", window.lastGeneratedTimetable);
  console.log("시간표 과목 수:", window.lastGeneratedTimetable.length);

  let timetable = window.lastGeneratedTimetable; // Use the stored one
  let currentColors = {};
  let usedColors = [];
  timetable.forEach(course => {
    if (!currentColors[course.course_id]) {
      let availableColors = colorPalette.filter(c => !usedColors.includes(c));
      let color = availableColors.length > 0 ? availableColors[0] : colorPalette[Math.floor(Math.random() * colorPalette.length)];
      currentColors[course.course_id] = color;
      usedColors.push(color);
    }
  });

  timetable.forEach(course => {
    let courseColor = currentColors[course.course_id];
    course.schedules.forEach(schedule => {
      let day = schedule.day;
      let timesStr = schedule.times;
      let location = schedule.location;
      if (!timesStr) {
        console.warn("No schedule times for course:", course.course_name);
        return;
      }
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      let dayIndex = convertDayToIndex(day);
      if (dayIndex === -1) return;
      timeSlots.forEach(slot => {
        const cell = document.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
        if (cell) {
          cell.innerHTML += `<div class="lecture" style="background-color: ${courseColor} !important;">
                               ${course.course_name}<br>${location}
                             </div>`;
        }
      });
    });
  });
  timetableIndexElem.textContent = `${window.currentIndex + 1} / ${window.timetables.length}`;
}
// 강의 고유 색상을 밝게 만드는 함수 (입력된 percent 만큼 밝게)
function lightenColor(hex, percent) {
  hex = hex.replace(/^#/, '');
  let num = parseInt(hex, 16);
  let r = (num >> 16) & 0xFF;
  let g = (num >> 8) & 0xFF;
  let b = num & 0xFF;
  r = Math.min(255, Math.floor(r + (255 - r) * percent / 100));
  g = Math.min(255, Math.floor(g + (255 - g) * percent / 100));
  b = Math.min(255, Math.floor(b + (255 - b) * percent / 100));
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM 로드 완료");
  
  // DOM 로드 후 실제 입력 필드 값으로 window.constraints 초기화
  const totalCreditsElem = document.getElementById("total-credits");
  const majorCreditsElem = document.getElementById("major-credits");
  const electiveCreditsElem = document.getElementById("elective-credits");
  
  if (totalCreditsElem) {
    window.constraints.total_credits = Number(totalCreditsElem.value) || 18;
  }
  if (majorCreditsElem) {
    window.constraints.major_credits = Number(majorCreditsElem.value) || 9;
  }
  if (electiveCreditsElem) {
    window.constraints.elective_credits = Number(electiveCreditsElem.value) || 9;
  }
  
  console.log("DOM 로드 후 window.constraints 초기화:");
  console.log("  total_credits:", window.constraints.total_credits);
  console.log("  major_credits:", window.constraints.major_credits);
  console.log("  elective_credits:", window.constraints.elective_credits);
  
  // 시간표 저장 버튼 확인
  const saveBtnCheck = document.getElementById("save-timetable-btn");
  console.log("시간표 저장 버튼 존재 여부:", saveBtnCheck ? "있음" : "없음");
  
  // ---------------------------
  // 기본 변수 및 DOM 요소 설정
  // ---------------------------
  const searchInput = document.getElementById("course-search");
  const filterButtons = document.querySelectorAll(".filter-btn");
  let activeFilter = "all";
  
  // 예약된 시간 슬롯 (이미 추가된 강좌의 시간들)
  var scheduledSlots = {
    '월': [],
    '화': [],
    '수': [],
    '목': [],
    '금': []
  };
  
  // 요일과 timetable의 data-day 인덱스 매핑
  const dayMapping = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
  
  // // 이미 왼쪽 영역에서 추가한 강좌의 course_id를 저장하는 배열 -> Use window.existingCourses instead
  // let existingCourses = []; // REMOVED - Use global window.existingCourses

  // 진행 상황 오버레이 관련 DOM 요소
  const progressOverlay = document.getElementById("progress-overlay");
  const progressText = document.getElementById("progress-text");
  const progressFill = document.getElementById("progress-fill");
  const progressCount = document.getElementById("progress-count");
  
  // ---------------------------
  // 필터 및 검색 관련 이벤트 핸들러
  // ---------------------------
  filterButtons.forEach(button => {
    button.addEventListener("click", function () {
      filterButtons.forEach(btn => btn.classList.remove("active"));
      this.classList.add("active");
      activeFilter = this.dataset.type;
      filterCourses();
    });
  });
  if (searchInput) {
    searchInput.addEventListener("input", filterCourses);
  }
  
  function filterCourses() {
    const keyword = searchInput ? searchInput.value.toLowerCase() : "";
    document.querySelectorAll(".course-item").forEach(item => {
      const name = item.querySelector(".course-name").textContent.toLowerCase();
      const instructor = item.querySelector(".instructor") ? item.querySelector(".instructor").textContent.toLowerCase() : "";
      const itemType = item.getAttribute("data-type") || "";
      const textMatch = name.includes(keyword) || instructor.includes(keyword);
      const typeMatch = (activeFilter === "all" || itemType === activeFilter);
      let available = true;
      const schedulesElem = item.querySelector(".course-schedules");
      if (schedulesElem) {
        const schedulesStr = schedulesElem.textContent.trim();
        let scheduleEntries = schedulesStr.split(";").map(entry => {
          let parts = entry.split(":");
          return {
            day: parts[0].trim(),
            times: parts.length > 1 ? parts[1].split("@")[0].trim() : ""
          };
        });
        for (let schedule of scheduleEntries) {
          let day = schedule.day;
          let timeSlots = schedule.times.split(",").map(str => parseInt(str, 10) + 8);
          for (let slot of timeSlots) {
            if (scheduledSlots[day] && scheduledSlots[day].includes(slot)) {
              available = false;
              break;
            }
          }
          if (!available) break;
        }
      }
      item.style.display = (textMatch && typeMatch && available) ? "flex" : "none";
    });
  }
  
  // ---------------------------
  // 강의 추가/삭제 관련 이벤트 핸들러
  // ---------------------------
  document.querySelectorAll(".add-course-btn").forEach(btn => {
    btn.addEventListener("click", function (event) {
      event.stopPropagation();
      const courseItem = this.closest(".course-item");
      addCourse(courseItem);
    });
  });

  function addCourse(courseData) { // 인자를 courseData 객체로 변경
    const courseId = String(courseData.course_id); // 문자열로 통일

    if (window.existingCourses.includes(courseId)) {
      alert("이 강의는 이미 추가되었습니다.");
      return;
    }

    // schedules_text 대신 courseData.schedules (객체 배열)를 직접 사용
    const scheduleEntries = courseData.schedules; // 이미 파싱된 형태 [{day:"월", times:"01,02", location:"강의실A"}, ...]

    if (!scheduleEntries || scheduleEntries.length === 0) {
      // 서버 응답에 schedules가 없거나 비어있는 경우에 대한 처리 (실제로는 거의 없을 것으로 예상)
      // 만약 schedules가 null일 수 있다면, courseData.schedules || [] 와 같이 처리
      console.warn(`강좌 ID ${courseId}: 스케줄 정보가 없습니다.`);
      // 필요하다면 사용자에게 알림
      // alert("해당 강의의 스케줄 정보가 없습니다.");
      // return; // 스케줄이 없는 과목을 추가할 수 없게 하려면 return
    }

    const courseName = courseData.course_name;
    let courseColor = getCourseColor(courseId); // getCourseColor 함수는 courseId를 사용

    // scheduleEntries (객체 배열)를 순회하며 시간표 셀에 강좌 정보 표시
    scheduleEntries.forEach(schedule => {
      let day = schedule.day;
      let timesStr = schedule.times; // 예: "05,06,07,08"
      let location = schedule.location || ""; // location이 없을 경우 빈 문자열

      if (!timesStr) { // times 정보가 없는 스케줄 엔트리는 건너뛰기
        console.warn(`Course ID ${courseId}, Day ${day}: 시간 정보가 없습니다.`);
        return;
      }

      // timesStr을 파싱하여 숫자 배열로 변환 (기존 로직 유지: 0부터 시작하는 인덱스 + 8)
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      timeSlots.sort((a, b) => a - b); // 시간 순으로 정렬

      // 요일 문자열을 숫자 인덱스로 변환
      let dayIndex = convertDayToIndex(day); // convertDayToIndex 함수가 필요합니다. (원본 코드에 있었음)
      if (dayIndex === -1) {
          console.warn(`Invalid day: ${day} for course ${courseName}`);
          return; // 유효하지 않은 요일이면 건너뛰기
      }

      // 연속된 시간인지 확인 (rowspan 적용을 위해)
      let contiguous = true;
      for (let i = 0; i < timeSlots.length - 1; i++) {
        if (timeSlots[i+1] !== timeSlots[i] + 1) {
          contiguous = false;
          break;
        }
      }

      if (contiguous && timeSlots.length > 0) {
        const startSlot = timeSlots[0];
        const rowspan = timeSlots.length;
        const firstCell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot}"]`);
        if (firstCell) {
          // 이미 해당 시간에 다른 강의가 있는지 확인 (scheduledSlots 사용 또는 직접 DOM 확인)
          // 여기서는 scheduledSlots를 업데이트하는 로직이 뒤에 나오므로, 우선 덮어쓰도록 둡니다.
          // 필요하다면 여기서 충돌 검사를 추가할 수 있습니다.

          firstCell.innerHTML = `
            <div class="lecture" data-course-id="${courseId}" data-course-name="${courseName}" style="background-color: ${courseColor} !important; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; font-size: 0.8em; padding: 2px;">
              <span style="font-weight: bold;">${courseName}</span>
              <span style="font-size: 0.9em;">${location}</span>
              <button class="remove-btn" style="position: absolute; top: 0; right: 0; background: rgba(0,0,0,0.3); color: white; border: none; cursor: pointer; padding: 0 3px; font-size: 0.7em;" onclick="event.stopPropagation(); removeLecture('${courseId}');">X</button>
            </div>
          `;
          firstCell.setAttribute("rowspan", rowspan);
          // rowspan으로 인해 숨겨질 셀들 처리
          for (let i = 1; i < rowspan; i++) {
            const cellToHide = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot + i}"]`);
            if (cellToHide) {
              cellToHide.style.display = "none";
              cellToHide.innerHTML = ""; // 내용도 비워줌
            }
          }
        }
      } else { // 연속되지 않거나 timeSlots이 비어있지 않은 단일 슬롯들
        timeSlots.forEach(slot => {
          const cell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${slot}"]`);
          if (cell) {
            // rowspan이 없으므로 기존 display 속성 복원 불필요
            cell.style.display = ""; // 혹시 이전 rowspan으로 숨겨졌을 수 있으므로 table-cell로
            cell.removeAttribute("rowspan"); // rowspan 속성 제거

            cell.innerHTML = `
              <div class="lecture" data-course-id="${courseId}" data-course-name="${courseName}" style="background-color: ${courseColor} !important; font-size: 0.8em; padding: 2px; text-align: center;">
                <span style="font-weight: bold;">${courseName}</span><br>
                <span style="font-size: 0.9em;">${location}</span>
                <button class="remove-btn" style="position: absolute; top: 0; right: 0; background: rgba(0,0,0,0.3); color: white; border: none; cursor: pointer; padding: 0 3px; font-size: 0.7em;" onclick="event.stopPropagation(); removeLecture('${courseId}');">X</button>
              </div>
            `;
          }
        });
      }

      // 업데이트: 등록된 시간 슬롯 저장 (scheduledSlots - 원본 코드에 있었음)
      // scheduledSlots 변수가 이 함수 스코프 또는 전역 스코프에 있어야 함
      if (typeof scheduledSlots !== 'undefined') {
          timeSlots.forEach(slot => {
              if (scheduledSlots[day]) {
                  if (!scheduledSlots[day].includes(slot)) { // 중복 방지
                      scheduledSlots[day].push(slot);
                  }
              } else {
                  scheduledSlots[day] = [slot];
              }
          });
      } else {
          console.warn("scheduledSlots is not defined. Cannot update scheduled time slots.");
      }

    }); // End of scheduleEntries.forEach

    // courseItem.classList.add("added"); // 왼쪽 패널의 DOM 요소 직접 조작 불가
    // filterCourses(); // 왼쪽 패널의 필터링 직접 조작 불가

    // 해결책: "강좌 추가 완료" 이벤트를 발생시켜 왼쪽 패널(category_dropdown.js)이 처리하도록 함
    const courseAddedEvent = new CustomEvent('courseSuccessfullyAdded', {
      detail: { courseId: courseId }
    });
    document.dispatchEvent(courseAddedEvent);

    window.existingCourses.push(courseId);

    // 시간표 UI에 변화가 있었으므로, 다른 UI 요소(예: 학점 계산 등) 업데이트가 필요하면 여기서 호출
    // updateCreditSummary(); // 예시
  }

      // 왼쪽 패널(category_dropdown.js)에서 강좌 추가 요청 이벤트를 리스닝
    document.addEventListener('addCourseToTimetable', function(event) {
        const courseData = event.detail; // category_dropdown.js에서 보낸 courseDataForTimetable 객체

        if (!courseData || !courseData.course_id) {
            console.error("[timetable.js] 'addCourseToTimetable' 이벤트 수신: course_id가 없는 잘못된 데이터입니다.", event.detail);
            alert("강좌를 추가하는 중 오류가 발생했습니다: 정보 부족");
            // 실패 이벤트를 보내서 왼쪽 패널의 버튼 상태를 원복시킬 수 있음
            if (courseData && courseData.course_id) {
                 const courseAdditionFailedEvent = new CustomEvent('courseAdditionFailed', {
                    detail: { courseId: courseData.course_id, reason: 'invalid_data' }
                });
                document.dispatchEvent(courseAdditionFailedEvent);
            }
            return;
        }

        console.log(`[timetable.js] 'addCourseToTimetable' 이벤트 수신:`, courseData);
        addCourse(courseData); // 수정된 addCourse 함수에 객체 그대로 전달
    });
    // 강좌 삭제 이벤트 리스너는 이전 답변과 동일하게 유지 (필요하다면)
    document.addEventListener('removeCourseFromTimetable', function(event) {
        const { courseId } = event.detail;
        if (courseId) {
            window.removeLecture(courseId);
        }
    });

  window.removeLecture = function(courseId) {
    // Remove from timetable UI
    document.querySelectorAll(`.lecture[data-course-id="${courseId}"]`).forEach(lecture => {
      let cell = lecture.closest("td");
      if (cell) {
        let rowspan = parseInt(cell.getAttribute("rowspan"), 10);
        cell.innerHTML = "";
        cell.style.display = "";
        cell.removeAttribute("rowspan");
        if (!isNaN(rowspan) && rowspan > 1) {
          const day = cell.getAttribute("data-day");
          const startHour = parseInt(cell.getAttribute("data-hour"), 10);
          for (let i = 1; i < rowspan; i++) {
            const nextCell = document.querySelector(`.timetable-cell[data-hour="${startHour + i}"][data-day="${day}"]`);
            if (nextCell) {
              nextCell.style.display = "table-cell";
            }
          }
        }
      }
    });
    // Remove from global state
    window.existingCourses = window.existingCourses.filter(id => id !== courseId);

    // Recalculate scheduledSlots based on remaining lectures in the UI
    scheduledSlots = { '월': [], '화': [], '수': [], '목': [], '금': [] };
    const inverseDayMapping = { 0: "월", 1: "화", 2: "수", 3: "목", 4: "금" };
    document.querySelectorAll(".timetable-cell").forEach(cell => {
      if (cell.innerHTML.trim() !== "") {
        let dayIndex = cell.getAttribute("data-day");
        let hour = parseInt(cell.getAttribute("data-hour"), 10);
        let dayLetter = inverseDayMapping[dayIndex];
        if (dayLetter) {
          scheduledSlots[dayLetter].push(hour);
        }
      }
    });
    document.querySelectorAll(`.course-item[data-course-id="${courseId}"]`).forEach(item => {
      item.classList.remove("added");
    });
    filterCourses();
  };
  
  // ---------------------------
  // 시간표 셀 클릭 시 수동 강의 추가 (예시)
  // ---------------------------
  document.querySelectorAll(".timetable-cell").forEach(cell => {
    cell.addEventListener("click", function () {
      let courseName = prompt("강의명을 입력하세요:");
      if (courseName) {
        this.innerHTML = "";
        let lectureDiv = document.createElement("div");
        lectureDiv.classList.add("lecture");
        lectureDiv.textContent = courseName;
        let removeBtn = document.createElement("button");
        removeBtn.classList.add("remove-btn");
        removeBtn.innerHTML = "X";
        removeBtn.onclick = function (event) {
          event.stopPropagation();
          manualRemoveLecture(event, this);
        };
        lectureDiv.appendChild(removeBtn);
        this.appendChild(lectureDiv);
      }
    });
  });

  function manualRemoveLecture(event, button) {
    event.stopPropagation();
    let cell = button.closest("td");
    cell.innerHTML = "";
  }

  // ---------------------------
  // 시간표 생성 관련 (SSE를 통한 실시간 진행 상황 표시)
  // ---------------------------
  const totalCreditsInput = document.getElementById("total-credits");
  const majorCreditsInput = document.getElementById("major-credits");
  const electiveCreditsInput = document.getElementById("elective-credits");
  const generateButton = document.getElementById("generate-btn");
  const prevButton = document.getElementById("prev-timetable");
  const nextButton = document.getElementById("next-timetable");
  const timetableIndex = document.getElementById("timetable-index");
  let timetables = [];
  let currentIndex = 0;

  if (generateButton) {
    generateButton.addEventListener("click", function () {
      progressOverlay.style.display = "block";
      progressText.textContent = "시간표 생성 시작...";
      progressFill.style.width = "0%";
      progressCount.textContent = "";
      
      let totalCredits = totalCreditsInput.value;
      let majorCredits = majorCreditsInput.value;
      let electiveCredits = electiveCreditsInput.value;
      let freeDays = [];
      document.querySelectorAll(".day-options input:checked").forEach(checkbox => {
        freeDays.push(checkbox.value);
      });
      // // Build query params directly - NO, use buildParamsFromConstraints
      // let queryParams = new URLSearchParams({
      //   total_credits: totalCredits,
      //   major_credits: majorCredits,
      //   elective_credits: electiveCredits
      // });
      // freeDays.forEach(day => queryParams.append("free_days[]", day));
      // window.existingCourses.forEach(id => queryParams.append("existing_courses[]", id)); // Use global

      // ① Update constraints from UI inputs
      console.log("[시간표 생성] UI 입력값 확인:");
      console.log("  totalCreditsInput.value:", totalCreditsInput.value);
      console.log("  majorCreditsInput.value:", majorCreditsInput.value);
      console.log("  electiveCreditsInput.value:", electiveCreditsInput.value);
      
      window.constraints.total_credits    = Number(totalCreditsInput.value);
      window.constraints.major_credits    = Number(majorCreditsInput.value);
      window.constraints.elective_credits = Number(electiveCreditsInput.value);
      window.constraints.free_days = Array.from(
        document.querySelectorAll(".day-options input:checked")
      ).map(cb=>cb.value);
      
      console.log("[시간표 생성] window.constraints 업데이트 후:");
      console.log("  window.constraints.total_credits:", window.constraints.total_credits);
      console.log("  window.constraints.major_credits:", window.constraints.major_credits);
      console.log("  window.constraints.elective_credits:", window.constraints.elective_credits);
      // SSE 연결
      const params = buildParamsFromConstraints();
      const evtSource = new EventSource("/generate_timetable_stream/?" + params.toString());
      
      evtSource.onmessage = e => {
          const data = JSON.parse(e.data);
          if (data.progress === "완료") {
              window.timetables   = data.timetables; // Update global timetables
              window.currentIndex = 0;
              
              // 수정 모드 상태는 유지하고, existing_courses만 초기화하지 않음
              // (다음 수정을 위해 현재 시간표 정보 유지)
              if (window.constraints.is_modification) {
                  console.log("수정 모드 완료, 제약조건 유지");
                  // is_modification 플래그만 초기화
                  window.constraints.is_modification = false;
                  // existing_courses는 유지 (다음 수정 시 참조 가능)
              }
              
              setTimeout(() => progressOverlay.style.display = "none", 800);
              applyTimetableToMiddlePanel(); // Display and store the new state
              evtSource.close();
          } else {
              // Update progress text
              let progressMsg = "시간표 생성 중...";
              if (data.processed !== undefined && data.found !== undefined) {
                  progressMsg = `처리된 조합: ${data.processed}, 후보: ${data.found}`;
              }
              progressText.textContent = progressMsg;
          }
      };
      
      evtSource.onerror = function(event) {
        progressText.textContent = "오류 발생";
        evtSource.close();
        setTimeout(() => { progressOverlay.style.display = "none"; }, 2000);
      };
    });
  }

  // ---------------------------
  // 강좌 색상 반환 함수 (수동 추가에도 고유 색상 할당) - Use global existingCourses
  function getCourseColor(courseId) {
    if (lectureColors[courseId]) {
      return lectureColors[courseId];
    }
    var usedColors = [];
    // Check colors used by currently fixed courses
    window.existingCourses.forEach(function(id) {
      if (lectureColors[id]) {
        usedColors.push(lectureColors[id]);
      }
    });
    var availableColors = colorPalette.filter(function(color) {
      return usedColors.indexOf(color) === -1;
    });
    if (availableColors.length > 0) {
      lectureColors[courseId] = availableColors[0];
    } else {
      // Fallback if all palette colors are used (unlikely with few courses)
      var randomIndex = Math.floor(Math.random() * colorPalette.length);
      lectureColors[courseId] = colorPalette[randomIndex];
    }
    return lectureColors[courseId];
  }

  // ---------------------------
  // 중간 패널에 시간표를 적용하는 함수 (생성된 시간표)
  // ---------------------------
  

  // ---------------------------
  // 요일 인덱스 변환 함수
  // ---------------------------

  if (prevButton) {
    prevButton.addEventListener("click", function () {
      if (currentIndex > 0) {
        currentIndex--;
        applyTimetableToMiddlePanel();
      }
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", function () {
      if (currentIndex < timetables.length - 1) {
        currentIndex++;
        applyTimetableToMiddlePanel();
      }
    });
  }

  // ---------------------------
  // 강좌 미리보기 오버레이 (마우스 엔터/리브)
  // ---------------------------
  function showPreview(courseItem) {
    if (courseItem.classList.contains("added")) return;
  
    let schedulesElem = courseItem.querySelector(".course-schedules");
    if (!schedulesElem) return;
    let schedulesStr = schedulesElem.textContent.trim();
    if (!schedulesStr) return;
  
    // 파싱 (형식: "월:07,08@강의실101;화:09@강의실202")
    let scheduleEntries = schedulesStr.split(";").map(entry => {
      let parts = entry.split(":");
      let timeAndLoc = parts[1].split("@");
      return {
        day: parts[0].trim(),
        times: timeAndLoc[0].trim(),
        location: timeAndLoc[1] ? timeAndLoc[1].trim() : ""
      };
    });
  
    let courseId = courseItem.getAttribute("data-course-id");
    let courseColor = getCourseColor(courseId);
    let courseName = courseItem.querySelector(".course-name").textContent.trim();
    let previewColor = lightenColor(courseColor, 30);
  
    scheduleEntries.forEach(schedule => {
      let day = schedule.day;
      let timesStr = schedule.times;
      let location = schedule.location;
      if (!timesStr) return;
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      let dayIndex = convertDayToIndex(day);
      if (dayIndex === -1) return;
      timeSlots.forEach(slot => {
        const cell = document.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
        if (cell) {
          if (getComputedStyle(cell).position === "static") {
            cell.style.position = "relative";
          }
          // 미리보기 중복 방지를 위해 해당 셀에 이미 preview가 있는지 확인
          if (!cell.querySelector(`.preview-lecture[data-preview-for="${courseId}"]`)) {
            let previewDiv = document.createElement("div");
            previewDiv.classList.add("preview-lecture");
            previewDiv.style.backgroundColor = previewColor;
            previewDiv.style.opacity = "0.3";
            previewDiv.style.position = "absolute";
            previewDiv.style.top = "0";
            previewDiv.style.left = "0";
            previewDiv.style.width = "100%";
            previewDiv.style.height = "100%";
            previewDiv.style.pointerEvents = "none";
            previewDiv.style.zIndex = "5";
            previewDiv.style.whiteSpace = "pre-wrap";
            previewDiv.style.color = "#000";
            previewDiv.style.fontSize = "12px";
            previewDiv.style.display = "flex";
            previewDiv.style.alignItems = "center";
            previewDiv.style.justifyContent = "center";
            previewDiv.textContent = `${courseName}\n${location}`;
            previewDiv.setAttribute("data-preview-for", courseId);
            cell.appendChild(previewDiv);
          }
        }
      });
    });
  }
  
  function hidePreview(courseItem) {
    let courseId = courseItem.getAttribute("data-course-id");
    document.querySelectorAll(`.preview-lecture[data-preview-for="${courseId}"]`).forEach(previewDiv => {
      previewDiv.remove();
    });
  }
  
  document.querySelectorAll(".course-item").forEach(courseItem => {
    courseItem.addEventListener("mouseenter", function() {
      showPreview(this);
    });
    courseItem.addEventListener("mouseleave", function() {
      hidePreview(this);
    });
  });

  // ---------------------------
  // 학점 조정 및 시간표 저장 (추후 구현)
  // ---------------------------
  const saveTimetableBtn = document.getElementById("save-timetable-btn");
  
  function adjustCredits(changedInput) {
    let total = parseInt(totalCreditsInput.value) || 0;
    let major = parseInt(majorCreditsInput.value) || 0;
    let elective = parseInt(electiveCreditsInput.value) || 0;
    if (changedInput === "major") {
      elective = total - major;
      if (elective < 0) elective = 0;
      electiveCreditsInput.value = elective;
    } else if (changedInput === "elective") {
      major = total - elective;
      if (major < 0) major = 0;
      majorCreditsInput.value = major;
    }
    
    // window.constraints도 함께 업데이트
    window.constraints.total_credits = total;
    window.constraints.major_credits = parseInt(majorCreditsInput.value) || 0;
    window.constraints.elective_credits = parseInt(electiveCreditsInput.value) || 0;
  }
  
  if (totalCreditsInput) {
    totalCreditsInput.addEventListener("input", function () {
      let total = parseInt(this.value);
      if (total < 1) total = 1;
      if (total > 24) total = 24;
      this.value = total;
      adjustCredits();
      // window.constraints도 업데이트
      window.constraints.total_credits = total;
    });
  }
  
  if (majorCreditsInput) {
    majorCreditsInput.addEventListener("input", function () {
      adjustCredits("major");
      // window.constraints도 업데이트
      window.constraints.major_credits = parseInt(this.value) || 0;
    });
  }
  
  if (electiveCreditsInput) {
    electiveCreditsInput.addEventListener("input", function () {
      adjustCredits("elective");
      // window.constraints도 업데이트
      window.constraints.elective_credits = parseInt(this.value) || 0;
    });
  }
  
  if (saveTimetableBtn) {
    saveTimetableBtn.addEventListener("click", async function () {
      console.log("시간표 저장 버튼 클릭됨");
      console.log("window.lastGeneratedTimetable:", window.lastGeneratedTimetable);
      
      // 현재 표시된 시간표가 있는지 확인
      if (!window.lastGeneratedTimetable || window.lastGeneratedTimetable.length === 0) {
        alert("저장할 시간표가 없습니다. 먼저 시간표를 생성해주세요.");
        return;
      }
      
      console.log("시간표 데이터 검증 통과");
      
      // CSRF 토큰 가져오기
      function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
          const cookies = document.cookie.split(';');
          for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
            }
          }
        }
        return cookieValue;
      }
      
      const csrfToken = getCookie('csrftoken');
      console.log("CSRF 토큰:", csrfToken);
      
      // 저장할 시간표 데이터 준비
              const timetableData = {
          courses: window.lastGeneratedTimetable.map(courses => ({
            course_id: courses.course_id,
            course_name: courses.course_name,
            credit: courses.credits,
            category: courses.category,
            schedules: courses.schedules,
            location: courses.location,
            note: '',
            color: ''
          })),
          title: '' // 서버에서 자동 생성
        };
      
      console.log("저장할 시간표 데이터:", timetableData);
      console.log("첫 번째 과목 상세:", timetableData.courses[0]);
      if (timetableData.courses[0] && timetableData.courses[0].schedules) {
        console.log("첫 번째 과목 스케줄:", timetableData.courses[0].schedules);
      }
      
      console.log("서버로 요청 전송 시작...");
      
      try {
        // 서버에 시간표 저장 요청
        const response = await fetch('/save_timetable/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(timetableData)
        });
        
        console.log("서버 응답 상태:", response.status);
        const result = await response.json();
        console.log("저장 응답:", result);
        
        if (response.ok && result.success) {
          alert("시간표가 성공적으로 저장되었습니다! '내 시간표 관리' 페이지에서 확인할 수 있습니다.");
        } else {
          alert("시간표 저장에 실패했습니다: " + (result.error || "알 수 없는 오류"));
        }
      } catch (error) {
        console.error("시간표 저장 오류:", error);
        console.error("오류 상세:", error.stack);
        alert("시간표 저장 중 오류가 발생했습니다: " + error.message);
      }
    });
  } else {
    console.error("시간표 저장 버튼을 찾을 수 없습니다!");
  }
});
async function generateTimetableFromNL(nlText) {
  return new Promise(async (resolve, reject) => {
    try {
      // 1) 자연어 제약조건 파싱
      const parseRes = await fetch("/parse_constraints/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: nlText })
      });
      if (!parseRes.ok) {
          alert("제약조건 해석에 실패했습니다.");
          reject(new Error("제약조건 해석 실패"));
          return;
      }
      // ← 여기서 JSON을 받고
      const parsed = await parseRes.json();
      Object.keys(parsed).forEach(key => {
        if (parsed[key] !== undefined) window.constraints[key] = parsed[key];
      });
      document.getElementById('major-credits').value    = window.constraints.major_credits;
      document.getElementById('elective-credits').value = window.constraints.elective_credits;

      const prev = window.constraints || {
        major_credits: Number(document.getElementById('major-credits').value),
        elective_credits: Number(document.getElementById('elective-credits').value),
        required_courses: [],
        free_days: [],
        avoid_times: [],
        avoid_time_ranges: [],
        only_time_ranges: [],
        exclude_courses: [],
        is_modification: false
      };
      const major_credits = parsed.major_credits ?? prev.major_credits;
      const elective_credits = parsed.elective_credits ?? prev.elective_credits; // Also update elective credits if parsed
      
      // 수정 모드 감지 로직 개선
      const isModification = (parsed.exclude_courses && parsed.exclude_courses.length > 0) || 
                            window.constraints.is_modification || 
                            (window.constraints.existing_courses && window.constraints.existing_courses.length > 0);
      
      console.log("수정 모드 감지:", {
        "parsed.exclude_courses": parsed.exclude_courses,
        "window.constraints.is_modification": window.constraints.is_modification,
        "window.constraints.existing_courses": window.constraints.existing_courses,
        "isModification": isModification
      });
      
      let idsToPassToBuilder = []; // Variable to hold the IDs to be passed

      // 2) Update constraints and determine fixed courses
      if (isModification) {
          console.log("Modification request detected. Excluding:", parsed.exclude_courses);
          
          // window.constraints.existing_courses가 있으면 우선 사용 (Rasa에서 전달된 경우)
          if (window.constraints.existing_courses && window.constraints.existing_courses.length > 0) {
              console.log("Using existing_courses from constraints:", window.constraints.existing_courses);
              idsToPassToBuilder = window.constraints.existing_courses.map(id => String(id));
          } else if (window.lastGeneratedTimetable && window.lastGeneratedTimetable.length > 0) {
              // 기존 로직: lastGeneratedTimetable에서 제외할 과목 필터링
              console.log("Base timetable for modification:", JSON.stringify(window.lastGeneratedTimetable.map(c => ({id: c.course_id, name: c.course_name}))));

              const coursesToExclude = (parsed.exclude_courses || []).map(name => name.toLowerCase());
              console.log("Courses to exclude (lowercase):", coursesToExclude);

              // Filter the IDs from the last timetable, keeping those NOT excluded
              const filteredTimetable = window.lastGeneratedTimetable.filter(course => {
                  if (!course || typeof course.course_name !== 'string') { // Defensive check
                      console.warn("Skipping course in filter due to missing/invalid name:", course);
                      return false; // Exclude if name is problematic
                  }
                  const courseNameLower = course.course_name.toLowerCase();
                  const shouldExclude = coursesToExclude.some(exName => courseNameLower.includes(exName));
                  return !shouldExclude;
              });
              console.log("Filtered timetable (courses to keep):", JSON.stringify(filteredTimetable.map(c => ({id: c.course_id, name: c.course_name}))));

              idsToPassToBuilder = filteredTimetable.map(course => String(course.course_id));
          } else {
              alert("이전 생성된 시간표 정보가 없습니다. 먼저 시간표를 생성해주세요.");
              console.error("Cannot modify: no previous timetable information available.");
              reject(new Error("이전 시간표 정보 없음"));
              return;
          }
          
          console.log("Fixed course IDs for modification:", JSON.stringify(idsToPassToBuilder));

          // Update constraints specifically for modification
          window.constraints.exclude_courses = parsed.exclude_courses || [];

          // Keep other constraints from the parsed NL if provided, otherwise keep previous
          window.constraints.major_credits = parsed.major_credits ?? prev.major_credits;
          window.constraints.elective_credits = parsed.elective_credits ?? prev.elective_credits;
          window.constraints.required_courses = parsed.required_courses ?? prev.required_courses;
          window.constraints.free_days = parsed.free_days ?? prev.free_days;
          window.constraints.avoid_times = parsed.avoid_times ?? prev.avoid_times;
          window.constraints.avoid_time_ranges = parsed.avoid_time_ranges ?? prev.avoid_time_ranges;
          window.constraints.only_time_ranges = parsed.only_time_ranges ?? prev.only_time_ranges;

      } else {
          console.log("Initial generation request from NL.");
          // For initial requests, use manually added courses
          idsToPassToBuilder = Array.from(
              document.querySelectorAll(".course-item.added")
          ).map(el => el.dataset.courseId);
          console.log("Using manually added courses for initial NL generation:", JSON.stringify(idsToPassToBuilder));

          // Update all constraints from parsed data for initial request
          Object.keys(parsed).forEach(key => {
              if (parsed[key] !== undefined) { // Update all keys from parsed data
                  window.constraints[key] = parsed[key];
              }
          });
           // Ensure exclude is empty if not provided by parser for initial request
          window.constraints.exclude_courses = parsed.exclude_courses || [];

          // Update UI inputs to reflect parsed constraints
          document.getElementById('major-credits').value = window.constraints.major_credits;
          document.getElementById('elective-credits').value = window.constraints.elective_credits;

      }

      // 3) Build query parameters using the updated window.constraints and the determined IDs
      console.log("IDs being passed to buildParamsFromConstraints:", JSON.stringify(idsToPassToBuilder));
      
      // 수정 모드에서 제외할 과목 정보를 buildParamsFromConstraints에서 사용할 수 있도록 설정
      if (isModification && parsed.exclude_courses) {
          window.constraints.exclude_courses = parsed.exclude_courses;
          console.log("수정 모드: 제외할 과목 설정됨:", window.constraints.exclude_courses);
      }
      
      const paramsObject = buildParamsFromConstraints(idsToPassToBuilder); // Pass the correct IDs
      const paramsString = paramsObject.toString();
      console.log("Generated URL Params Object:", paramsObject);
      console.log("Generated URL Params String:", paramsString); // Log the actual params being sent

      // 4) SSE로 시간표 생성 스트림 요청
      // Explicitly decode the URI component for the EventSource URL
      const eventSourceUrl = "/generate_timetable_stream/?" + decodeURIComponent(paramsString);
      console.log("EventSource URL:", eventSourceUrl);
      const evtSource = new EventSource(eventSourceUrl);
      const progressOverlay = document.getElementById("progress-overlay");
      const progressText    = document.getElementById("progress-text");

      progressOverlay.style.display = "block";
      progressText.textContent   = "시간표 생성 중…";

      evtSource.onmessage = e => {
          const data = JSON.parse(e.data);
          if (data.progress === "완료") {
              window.timetables   = data.timetables; // Update global timetables
              window.currentIndex = 0;
              
              // 수정 모드 상태는 유지하고, existing_courses만 초기화하지 않음
              // (다음 수정을 위해 현재 시간표 정보 유지)
              if (window.constraints.is_modification) {
                  console.log("수정 모드 완료, 제약조건 유지");
                  // is_modification 플래그만 초기화
                  window.constraints.is_modification = false;
                  // existing_courses는 유지 (다음 수정 시 참조 가능)
              }
              
              setTimeout(() => progressOverlay.style.display = "none", 800);
              applyTimetableToMiddlePanel(); // Display and store the new state
              evtSource.close();
              resolve(); // Promise 완료
          } else {
              // Update progress text
              let progressMsg = "시간표 생성 중...";
              if (data.processed !== undefined && data.found !== undefined) {
                  progressMsg = `처리된 조합: ${data.processed}, 후보: ${data.found}`;
              }
              progressText.textContent = progressMsg;
          }
      };

      evtSource.onerror = () => {
          progressText.textContent = "시간표 생성 중 오류가 발생했습니다.";
          evtSource.close();
          setTimeout(() => progressOverlay.style.display = "none", 1200);
          reject(new Error("시간표 생성 오류"));
      };
    } catch (error) {
      reject(error);
    }
  });
}
