// 전역 변수: 강좌 색상 관리 및 색상 팔레트
var lectureColors = {};
var colorPalette = ['#f28b82', '#fbbc04', '#fff475', '#ccff90', '#a7ffeb', '#cbf0f8', '#aecbfa', '#d7aefb', '#fdcfe8'];
function convertDayToIndex(day) {
  const days = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
  return days[day] !== undefined ? days[day] : -1;
}

// 채팅·버튼 양쪽에서 누적 관리할 제약조건
window.constraints = {
  major_credits:    Number(document.getElementById('major-credits')?.value || 9),
  elective_credits: Number(document.getElementById('elective-credits')?.value || 9),
  required_courses: [],
  free_days:        [],
  avoid_times:      [],
  avoid_time_ranges:[],
  only_time_ranges: [],
  exclude_courses:  []
};
window.existingCourses = []; // Manually added courses from left panel OR courses to fix for modification
window.lastGeneratedTimetable = null; // Store the full data of the last displayed timetable
window.currentTimetableCourseIds = []; // Store IDs of the last displayed timetable

// Modified: Accepts an optional array of course IDs to use for the 'existing_courses' parameter.
// If not provided, defaults to the global window.existingCourses (manually added).
function buildParamsFromConstraints(idsToUse = window.existingCourses) {
  console.log("[buildParamsFromConstraints] Received idsToUse:", JSON.stringify(idsToUse)); // Log received IDs
  const c = window.constraints;
  const total = c.major_credits + c.elective_credits;
  const params = new URLSearchParams({
    total_credits: total,
    major_credits: c.major_credits,
    elective_credits: c.elective_credits
  });
  c.free_days        .forEach(d => params.append("free_days[]", d));
  c.required_courses .forEach(r => params.append("required_courses[]", r));
  c.exclude_courses  .forEach(e => params.append("exclude_courses[]", e));
  c.avoid_times      .forEach(o => params.append("avoid_times[]",        JSON.stringify(o)));
  c.avoid_time_ranges.forEach(o => params.append("avoid_time_ranges[]", JSON.stringify(o)));
  c.only_time_ranges .forEach(o => params.append("only_time_ranges[]",  JSON.stringify(o)));

  // Use the provided idsToUse array for the 'existing_courses' parameter
  console.log("[buildParamsFromConstraints] Processing idsToUse for existing_courses[]:", JSON.stringify(idsToUse));
  (idsToUse || []).forEach(id =>
    params.append("existing_courses[]", String(id)) // Ensure it's string
  );
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
  function addCourse(courseItem) {
    const courseId = courseItem.getAttribute("data-course-id");
    // Use global window.existingCourses
    if (window.existingCourses.includes(courseId)) {
      alert("이 강의는 이미 추가되었습니다.");
      return;
    }
    const schedulesElem = courseItem.querySelector(".course-schedules");
    const schedulesStr = schedulesElem ? schedulesElem.textContent.trim() : "";
    if (!schedulesStr) {
      alert("해당 강의의 스케줄 정보가 없습니다.");
      return;
    }
    // 파싱: "월:07,08@강의실101;화:09@강의실202" 형식
    let scheduleEntries = schedulesStr.split(";").map(entry => {
      let parts = entry.split(":");
      let timeAndLoc = parts[1].split("@");
      return { 
        day: parts[0].trim(), 
        times: timeAndLoc[0].trim(),
        location: timeAndLoc[1] ? timeAndLoc[1].trim() : ""
      };
    });
    const courseName = courseItem.querySelector('.course-name').textContent.trim();
    let courseColor = getCourseColor(courseId);
  
    scheduleEntries.forEach(schedule => {
      let day = schedule.day;
      let timesStr = schedule.times;
      let location = schedule.location;
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      timeSlots.sort((a, b) => a - b);
      for (let slot of timeSlots) {
        if (scheduledSlots[day] && scheduledSlots[day].includes(slot)) {
          alert(`선택하신 강의(${courseName})의 ${day} ${slot}:00 시간대가 이미 등록되어 있습니다.`);
          return;
        }
      }
      let contiguous = true;
      for (let i = 0; i < timeSlots.length - 1; i++) {
        if (timeSlots[i+1] !== timeSlots[i] + 1) {
          contiguous = false;
          break;
        }
      }
      let dayIndex = dayMapping[day];
      if (contiguous) {
        const startSlot = timeSlots[0];
        const rowspan = timeSlots.length;
        const firstCell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot}"]`);
        if (firstCell) {
          firstCell.innerHTML = `
            <div class="lecture" data-course-id="${courseId}" data-course="${courseName}" style="background-color: ${courseColor} !important; height: 100%; display: flex; align-items: center; justify-content: center;">
              ${courseName}<br>${location}
              <button class="remove-btn" onclick="event.stopPropagation(); removeLecture('${courseId}');">X</button>
            </div>
          `;
          firstCell.setAttribute("rowspan", rowspan);
          for (let i = 1; i < rowspan; i++) {
            const cellToHide = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot + i}"]`);
            if (cellToHide) {
              cellToHide.style.display = "none";
              cellToHide.innerHTML = "";
            }
          }
        }
      } else {
        for (let slot of timeSlots) {
          const cell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${slot}"]`);
          if (cell) {
            cell.innerHTML = `
              <div class="lecture" data-course-id="${courseId}" data-course="${courseName}" style="background-color: ${courseColor} !important;">
                ${courseName}<br>${location}
                <button class="remove-btn" onclick="event.stopPropagation(); removeLecture('${courseId}');">X</button>
              </div>
            `;
          }
        }
      }
      // 업데이트: 등록된 시간 슬롯 저장
      timeSlots.forEach(slot => {
        if (scheduledSlots[day]) {
          scheduledSlots[day].push(slot);
        } else {
          scheduledSlots[day] = [slot];
        }
      });
    });
    courseItem.classList.add("added");
    // Use global window.existingCourses
    window.existingCourses.push(courseId);
    filterCourses(); // Re-filter left panel based on availability
  }

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
      window.constraints.major_credits    = Number(totalCreditsInput.value);
      window.constraints.elective_credits = Number(electiveCreditsInput.value);
      window.constraints.free_days = Array.from(
        document.querySelectorAll(".day-options input:checked")
      ).map(cb=>cb.value);
      // SSE 연결
      const params = buildParamsFromConstraints();
      const evtSource = new EventSource("/generate_timetable_stream/?" + params.toString());
      
      evtSource.onmessage = function(event) {
        let data = JSON.parse(event.data);
        if (data.progress === "완료") {
          progressText.textContent = "총 " + data.found + "개의 시간표를 찾았습니다.";
          window.timetables = data.timetables; // Update global timetables
          window.currentIndex = 0;
          setTimeout(() => { progressOverlay.style.display = "none"; }, 1000);
          applyTimetableToMiddlePanel(); // This will update lastGeneratedTimetable and currentTimetableCourseIds
          evtSource.close();
        } else {
          // Update progress text (assuming backend sends processed/found counts)
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
  }
  
  if (totalCreditsInput) {
    totalCreditsInput.addEventListener("input", function () {
      let total = parseInt(this.value);
      if (total < 1) total = 1;
      if (total > 24) total = 24;
      this.value = total;
      adjustCredits();
    });
  }
  
  if (majorCreditsInput) {
    majorCreditsInput.addEventListener("input", function () {
      adjustCredits("major");
    });
  }
  
  if (electiveCreditsInput) {
    electiveCreditsInput.addEventListener("input", function () {
      adjustCredits("elective");
    });
  }
  
  if (saveTimetableBtn) {
    saveTimetableBtn.addEventListener("click", function () {
      let totalCredits = totalCreditsInput.value;
      let majorCredits = majorCreditsInput.value;
      let electiveCredits = electiveCreditsInput.value;
      let selectedDays = [];
      document.querySelectorAll(".day-options input:checked").forEach(checkbox => {
          selectedDays.push(checkbox.value);
      });
      console.log("현재 시간표 저장:");
      console.log("총 학점:", totalCredits);
      console.log("전공 학점:", majorCredits);
      console.log("교양 학점:", electiveCredits);
      console.log("공강 요일:", selectedDays);
      alert("현재 시간표가 저장되었습니다! (나중에 마이페이지와 연동)");
    });
  }
});
async function generateTimetableFromNL(nlText) {
  // 1) 자연어 제약조건 파싱
  const parseRes = await fetch("/parse_constraints/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: nlText })
  });
  if (!parseRes.ok) {
      alert("제약조건 해석에 실패했습니다.");
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
    exclude_courses: []
  };
  const major_credits = parsed.major_credits ?? prev.major_credits;
  const elective_credits = parsed.elective_credits ?? prev.elective_credits; // Also update elective credits if parsed
  const isModification = parsed.exclude_courses && parsed.exclude_courses.length > 0;
  let idsToPassToBuilder = []; // Variable to hold the IDs to be passed

  // 2) Update constraints and determine fixed courses
  if (isModification) {
      console.log("Modification request detected. Excluding:", parsed.exclude_courses);
      if (!window.lastGeneratedTimetable || window.lastGeneratedTimetable.length === 0) {
          alert("이전 생성된 시간표 정보가 없습니다. 먼저 시간표를 생성해주세요.");
          console.error("Cannot modify: window.lastGeneratedTimetable is empty or null.");
          return;
      }
      console.log("Base timetable for modification:", JSON.stringify(window.lastGeneratedTimetable.map(c => ({id: c.course_id, name: c.course_name}))));

      const coursesToExclude = parsed.exclude_courses.map(name => name.toLowerCase());
      console.log("Courses to exclude (lowercase):", coursesToExclude);

      // Filter the IDs from the last timetable, keeping those NOT excluded
      const filteredTimetable = window.lastGeneratedTimetable.filter(course => {
          if (!course || typeof course.course_name !== 'string') { // Defensive check
              console.warn("Skipping course in filter due to missing/invalid name:", course);
              return false; // Exclude if name is problematic
          }
          const courseNameLower = course.course_name.toLowerCase();
          const shouldExclude = coursesToExclude.some(exName => courseNameLower.includes(exName));
          // console.log(`Checking ${courseNameLower} against ${coursesToExclude}. Exclude: ${shouldExclude}`);
          return !shouldExclude;
      });
      console.log("Filtered timetable (courses to keep):", JSON.stringify(filteredTimetable.map(c => ({id: c.course_id, name: c.course_name}))));

      const fixedCourseIds = filteredTimetable.map(course => String(course.course_id)); // Ensure IDs are strings
      console.log("Calculated fixedCourseIds for modification:", JSON.stringify(fixedCourseIds));

      idsToPassToBuilder = fixedCourseIds; // Use these IDs for the builder

      // Update constraints specifically for modification
      window.constraints.exclude_courses = parsed.exclude_courses;

      // Keep other constraints from the parsed NL if provided, otherwise keep previous
      // Keep other constraints from the parsed NL if provided, otherwise use previous state
      window.constraints.major_credits = parsed.major_credits ?? prev.major_credits;
      window.constraints.elective_credits = parsed.elective_credits ?? prev.elective_credits;
      window.constraints.required_courses = parsed.required_courses ?? prev.required_courses;
      window.constraints.free_days = parsed.free_days ?? prev.free_days;
      window.constraints.avoid_times = parsed.avoid_times ?? prev.avoid_times;
      window.constraints.avoid_time_ranges = parsed.avoid_time_ranges ?? prev.avoid_time_ranges;
      window.constraints.only_time_ranges = parsed.only_time_ranges ?? prev.only_time_ranges;

      // DO NOT assign fixedCourseIds to window.existingCourses here, keep them separate
      // console.log("Fixed courses for modification (assigned to window.existingCourses):", window.existingCourses); // Removed this confusing assignment

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
      // TODO: Potentially update free day checkboxes too if needed based on parsed.free_days
  }

  // 3) Build query parameters using the updated window.constraints and the determined IDs
  console.log("IDs being passed to buildParamsFromConstraints:", JSON.stringify(idsToPassToBuilder));
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

  evtSource.onerror = () => {
      progressText.textContent = "시간표 생성 중 오류가 발생했습니다.";
      evtSource.close();
      setTimeout(() => progressOverlay.style.display = "none", 1200);
  };
}
