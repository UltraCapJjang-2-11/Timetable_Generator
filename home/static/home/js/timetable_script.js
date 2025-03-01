document.addEventListener("DOMContentLoaded", function () {
    /***********************
     * 전역 변수 및 매핑
     ***********************/
    // 검색 input – 팀원 HTML에서는 id "course-search" 사용
    const searchInput = document.getElementById("course-search");
    // 필터 버튼들 (class "filter-btn")
    const filterButtons = document.querySelectorAll(".filter-btn");
    let activeFilter = "all"; // 기본 필터
  
    // 좌측 강의 항목은 .course-item, 추가 버튼은 .add-course-btn
    // 시간표에 추가된 슬롯 기록 (예: { '월': [9,10], ... })
    var scheduledSlots = {
      '월': [],
      '화': [],
      '수': [],
      '목': [],
      '금': []
    };
    // 요일 문자열 → timetable의 data-day(0~4) 매핑
    const dayMapping = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
  
    /***********************
     * 좌측 필터 및 검색 기능
     ***********************/
    // 필터 버튼 클릭 이벤트
    filterButtons.forEach(button => {
      button.addEventListener("click", function () {
        filterButtons.forEach(btn => btn.classList.remove("active"));
        this.classList.add("active");
        activeFilter = this.dataset.type;
        filterCourses();
      });
    });
    // 검색 input 이벤트
    if (searchInput) {
      searchInput.addEventListener("input", filterCourses);
    }
    // 강의 목록 필터링 함수
    function filterCourses() {
      const keyword = searchInput ? searchInput.value.toLowerCase() : "";
      document.querySelectorAll(".course-item").forEach(item => {
        const name = item.querySelector(".course-name").textContent.toLowerCase();
        const instructor = item.querySelector(".instructor") ? item.querySelector(".instructor").textContent.toLowerCase() : "";
        const itemType = item.getAttribute("data-type") || "";
        const textMatch = name.includes(keyword) || instructor.includes(keyword);
        const typeMatch = (activeFilter === "all" || itemType === activeFilter);
        // 필터: 시간표에 추가 가능한지 (추가 버튼 비활성화 여부) – (원하는 경우 추가)
        let available = true;
        const day = item.getAttribute("data-day");
        const timesStr = item.getAttribute("data-times");
        if (day && timesStr) {
          const timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
          for (let slot of timeSlots) {
            if (scheduledSlots[day] && scheduledSlots[day].includes(slot)) {
              available = false;
              break;
            }
          }
        }
        // 표시 결정
        item.style.display = (textMatch && typeMatch && available) ? "flex" : "none";
      });
    }
  
    /***********************
     * 강의 추가/삭제 (병합된 시간 블록)
     ***********************/
    // "추가" 버튼 클릭 시 (각 course-item 내의 버튼)
    document.querySelectorAll(".add-course-btn").forEach(btn => {
      btn.addEventListener("click", function (event) {
        event.stopPropagation();
        const courseItem = this.closest(".course-item");
        addCourse(courseItem);
      });
    });
  
    // 강의 추가 함수
    function addCourse(courseItem) {
      if (courseItem.classList.contains("added")) {
        alert("이 강의는 이미 추가되었습니다.");
        return;
      }
      const day = courseItem.getAttribute("data-day");
      const timesStr = courseItem.getAttribute("data-times");
      if (!day || !timesStr) {
        alert("해당 강의의 스케줄 정보가 없습니다.");
        return;
      }
      // 예: "01,02,03" → [9,10,11] (08시는 "00")
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      timeSlots.sort((a, b) => a - b);
      // 연속된 시간 블록인지 체크
      let contiguous = true;
      for (let i = 0; i < timeSlots.length - 1; i++) {
        if (timeSlots[i+1] !== timeSlots[i] + 1) {
          contiguous = false;
          break;
        }
      }
      // 만약 연속되지 않으면, 각 셀에 개별 추가 (여기서는 단순 처리)
      if (!contiguous) {
        for (let slot of timeSlots) {
          if (scheduledSlots[day].includes(slot)) {
            alert("선택하신 강의의 시간대가 이미 등록되어 있습니다.");
            return;
          }
        }
        timeSlots.forEach(slot => {
          const dayIndex = dayMapping[day];
          const cell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${slot}"]`);
          if (cell) {
            cell.innerHTML = `
              <div class="lecture" data-course="${courseItem.querySelector('.course-name').textContent}">
                ${courseItem.querySelector('.course-name').textContent}
                <button class="remove-btn" onclick="removeLecture(event, this, '${day}', ${slot}, 1)">X</button>
              </div>
            `;
          }
          scheduledSlots[day].push(slot);
        });
        courseItem.classList.add("added");
        filterCourses();
        return;
      }
      // 연속된 시간 블록 처리
      for (let slot of timeSlots) {
        if (scheduledSlots[day].includes(slot)) {
          alert("선택하신 강의의 시간대가 이미 등록되어 있습니다.");
          return;
        }
      }
      const startSlot = timeSlots[0];
      const rowspan = timeSlots.length;
      const dayIndex = dayMapping[day];
      const firstCell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot}"]`);
      if (firstCell) {
        const courseName = courseItem.querySelector('.course-name').textContent;
        firstCell.innerHTML = `
          <div class="lecture" data-course="${courseName}" style="height: 100%; display: flex; align-items: center; justify-content: center;">
            ${courseName}
            <button class="remove-btn" onclick="removeLecture(event, this, '${day}', ${startSlot}, ${rowspan})">X</button>
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
        timeSlots.forEach(slot => scheduledSlots[day].push(slot));
        courseItem.classList.add("added");
        filterCourses();
      }
    }
  
    // 강의 삭제 함수 – 전역으로 노출
    window.removeLecture = function (event, btn, day, startSlot, rowspan) {
      event.stopPropagation();
      const dayIndex = dayMapping[day];
      for (let i = 0; i < rowspan; i++) {
        const cell = document.querySelector(`.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot + i}"]`);
        if (cell) {
          cell.innerHTML = "";
          cell.style.display = "";
          cell.removeAttribute("rowspan");
        }
        scheduledSlots[day] = scheduledSlots[day].filter(slot => slot !== (startSlot + i));
      }
      const removedCourseName = btn.parentElement.getAttribute("data-course");
      document.querySelectorAll(".course-item.added").forEach(item => {
        if (item.querySelector(".course-name").textContent.trim() === removedCourseName) {
          item.classList.remove("added");
        }
      });
      filterCourses();
    };
  
    /***********************
     * 타임테이블 셀 수동 입력 기능
     ***********************/
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
  
    /***********************
     * 랜덤 시간표 생성 및 탐색 기능 (팀원 코드 유지)
     ***********************/
    const generateButton = document.getElementById("generate-btn");
    const prevButton = document.getElementById("prev-timetable");
    const nextButton = document.getElementById("next-timetable");
    const timetableIndex = document.getElementById("timetable-index");
    let timetables = [];
    let currentIndex = 0;
    if (generateButton) {
      generateButton.addEventListener("click", function () {
        fetch("/generate_timetable/")
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              alert(data.error);
              return;
            }
            timetables = data.timetables;
            currentIndex = 0;
            applyTimetableToMiddlePanel();
          })
          .catch(error => console.error("Error:", error));
      });
    }
    function applyTimetableToMiddlePanel() {
      const timetableCells = document.querySelectorAll(".timetable-cell");
      timetableCells.forEach(cell => cell.innerHTML = "");
      if (timetables.length === 0) {
        timetableIndex.textContent = "0 / 0";
        return;
      }
      let timetable = timetables[currentIndex];
      timetable.forEach(entry => {
        const { course_name, day, times, location } = entry;
        let [startTime, endTime] = times.split("-");
        startTime = parseInt(startTime, 10);
        endTime = parseInt(endTime, 10);
        let dayIndex = convertDayToIndex(day);
        if (dayIndex === -1) return;
        for (let hour = startTime; hour < endTime; hour++) {
          const cell = document.querySelector(`.timetable-cell[data-hour="${hour}"][data-day="${dayIndex}"]`);
          if (cell) {
            cell.innerHTML = `<div class="lecture">${course_name}<br>${location}</div>`;
          }
        }
      });
      timetableIndex.textContent = `${currentIndex + 1} / ${timetables.length}`;
    }
    function convertDayToIndex(day) {
      const days = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
      return days[day] !== undefined ? days[day] : -1;
    }
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
  
    /***********************
     * 시간표 저장 및 학점 조정 기능 (팀원 코드 유지)
     ***********************/
    const totalCreditsInput = document.getElementById("total-credits");
    const majorCreditsInput = document.getElementById("major-credits");
    const electiveCreditsInput = document.getElementById("elective-credits");
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
        const totalCredits = totalCreditsInput.value;
        const majorCredits = majorCreditsInput.value;
        const electiveCredits = electiveCreditsInput.value;
        const selectedDays = [];
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
  