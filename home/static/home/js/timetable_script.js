// ------------------------------------------------------------
// 전역 변수: 강좌 색상 관리 및 색상 팔레트
// ------------------------------------------------------------

// lectureColors: 각 강좌(course_id)에 할당된 색상을 저장하는 객체
var lectureColors = {};

// colorPalette: 강의별 할당 가능한 색상 목록 (여기서 하나씩 순차적으로 사용하거나, 부족할 경우 랜덤으로 사용)
var colorPalette = [
  '#f28b82', '#fbbc04', '#fff475', '#ccff90',
  '#a7ffeb', '#cbf0f8', '#aecbfa', '#d7aefb', '#fdcfe8'
];

// convertDayToIndex: 한글 요일("월","화","수","목","금")을 숫자 인덱스(0~4)로 변환하는 함수
function convertDayToIndex(day) {
  const days = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
  // 전달된 day가 days 객체에 있으면 해당 값을 반환, 없으면 -1 반환
  return days[day] !== undefined ? days[day] : -1;
}

// ------------------------------------------------------------
// 전역 상태: 시간표 생성 및 챗봇 양쪽에서 누적 관리할 제약조건
// (DOMContentLoaded 이후 실제 입력 필드 값으로 초기화)
// ------------------------------------------------------------
window.constraints = {
  total_credits:    18,  // 전체 학점 (기본값: 18), DOM 로드 후 입력값으로 덮어쓰기
  major_credits:    9,   // 전공 학점 (기본값: 9), DOM 로드 후 입력값으로 덮어쓰기
  elective_credits: 9,   // 교양 학점 (기본값: 9), DOM 로드 후 입력값으로 덮어쓰기
  required_courses: [],  // 필수 과목 목록 (course_id 배열)
  free_days:        [],  // 공강 요일 목록 (예: ["월","수"])
  avoid_times:      [],  // 특정 시각 공강 (예: [{day:"화",hour:10}, ...])
  avoid_time_ranges:[],  // 특정 시간대 범위 공강 (예: [{day:"목",start_hour:9,end_hour:12}, ...])
  only_time_ranges: [],  // 수강 가능한 특정 시간대 범위 (예: [{day:"금",start_hour:14,end_hour:18}, ...])
  exclude_courses:  [],  // 제외할 과목(course_id 혹은 과목명 등) 목록
  is_modification: false // 수정 모드인지 여부 (이전 생성한 시간표 수정 시 true)
};

// existingCourses: 왼쪽 패널에서 수동으로 추가된 강좌(course_id 문자열)의 배열
// 또는 수정 모드에서 고정(fix)된 과목 ID 목록으로 사용
window.existingCourses = [];

// lastGeneratedTimetable: 마지막으로 화면에 표시된 시간표 전체 데이터를 저장
// (각 원소는 {course_id, course_name, credits, schedules:[{day,times,location}], ...} 형태)
window.lastGeneratedTimetable = null;

// currentTimetableCourseIds: 마지막 생성된 시간표에 포함된 course_id 목록(문자열 배열)
window.currentTimetableCourseIds = [];

// ------------------------------------------------------------
// buildParamsFromConstraints: 제약조건을 URLSearchParams 형태로 변환하여
// 서버에 GET 파라미터로 전달할 수 있도록 만드는 함수
//
// idsToUse: 기존에 고정(fix)된 강좌 ID 목록(문자열 배열). 없으면 window.existingCourses 사용.
// ------------------------------------------------------------
function buildParamsFromConstraints(idsToUse) {
  // 디버그 로그: 전달된 idsToUse 정보 출력
  console.log("[buildParamsFromConstraints] Received idsToUse:", JSON.stringify(idsToUse));

  // URLSearchParams 객체 생성 (key=value&key=value 형태의 쿼리스트링 빌드용)
  let params = new URLSearchParams();

  // 학점 정보: 제약조건 객체에서 가져오기 (값이 없으면 0으로 처리)
  // 우선 total_credits를 사용, 0이면 major_credits + elective_credits로 합산
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

  // total_credits가 0인 경우, major+elective로 재계산
  if (totalCredits === 0) {
    totalCredits = majorCredits + electiveCredits;
    console.log("  total_credits가 0이므로 major + elective로 계산:", totalCredits);
  }

  // URLSearchParams에 학점 정보 추가
  params.append("total_credits", totalCredits);
  params.append("major_credits", majorCredits);
  params.append("elective_credits", electiveCredits);

  console.log("[buildParamsFromConstraints] 최종 전송 학점:");
  console.log("  total_credits:", totalCredits);
  console.log("  major_credits:", majorCredits);
  console.log("  elective_credits:", electiveCredits);

  // ------------------------------------------------------------
  // 기존 등록된 과목(existing courses) 처리
  // ------------------------------------------------------------
  console.log("[buildParamsFromConstraints] Processing idsToUse for existing_courses[]:", JSON.stringify(idsToUse));
  // idsToUse가 주어졌으면 그 배열 사용, 아니면 window.existingCourses 사용
  let existingCoursesToUse = idsToUse || window.existingCourses;
  existingCoursesToUse.forEach(id => {
    // existing_courses[] 파라미터로 course_id를 추가
    params.append("existing_courses[]", id);
  });

  // ------------------------------------------------------------
  // 공강 요일 처리 (free_days[])
  // ------------------------------------------------------------
  if (window.constraints.free_days && window.constraints.free_days.length > 0) {
    window.constraints.free_days.forEach(day => {
      // free_days[] 파라미터로 요일 문자열(예: "월","수")을 추가
      params.append("free_days[]", day);
    });
  }

  // ------------------------------------------------------------
  // 필수 과목 처리 (required_courses[])
  // ------------------------------------------------------------
  if (window.constraints.required_courses && window.constraints.required_courses.length > 0) {
    window.constraints.required_courses.forEach(course => {
      // required_courses[] 파라미터로 필수 과목 ID 혹은 이름을 추가
      params.append("required_courses[]", course);
    });
  }

  // ------------------------------------------------------------
  // 제외할 과목 처리 (exclude_courses[])
  // ------------------------------------------------------------
  console.log("[buildParamsFromConstraints] window.constraints.exclude_courses 확인:", window.constraints.exclude_courses);
  if (window.constraints.exclude_courses && window.constraints.exclude_courses.length > 0) {
    console.log("[buildParamsFromConstraints] 제외할 과목 처리 시작:", window.constraints.exclude_courses);
    window.constraints.exclude_courses.forEach(course => {
      // exclude_courses[] 파라미터로 제외할 과목 ID 또는 이름을 추가
      params.append("exclude_courses[]", course);
      console.log("[buildParamsFromConstraints] 제외할 과목 추가됨:", course);
    });
    console.log("[buildParamsFromConstraints] 제외할 과목 추가 완료");
  } else {
    console.log("[buildParamsFromConstraints] 제외할 과목이 없거나 비어있음");
  }

  // ------------------------------------------------------------
  // 특정 시간대 공강 처리 (specific_avoid_times[])
  // 예: [{day:"화",hour:10}, ...]
  // ------------------------------------------------------------
  if (window.constraints.specific_avoid_times && window.constraints.specific_avoid_times.length > 0) {
    console.log("[buildParamsFromConstraints] 특정 시간 공강 처리:", window.constraints.specific_avoid_times);
    window.constraints.specific_avoid_times.forEach(timeInfo => {
      // timeInfo에 day와 hour 속성이 있으면 JSON 문자열로 인코딩하여 파라미터에 추가
      if (timeInfo.day && timeInfo.hour) {
        params.append("specific_avoid_times[]", JSON.stringify({
          day: timeInfo.day,
          hour: timeInfo.hour
        }));
        console.log("[buildParamsFromConstraints] 특정 시간 추가:", timeInfo.day, timeInfo.hour);
      }
    });
  }

  // ------------------------------------------------------------
  // 특정 시간대 범위 공강 처리 (specific_avoid_time_ranges[])
  // 예: [{day:"목", start_hour:9, end_hour:12}, ...]
  // ------------------------------------------------------------
  if (window.constraints.specific_avoid_time_ranges && window.constraints.specific_avoid_time_ranges.length > 0) {
    console.log("[buildParamsFromConstraints] 특정 시간 범위 공강 처리:", window.constraints.specific_avoid_time_ranges);
    window.constraints.specific_avoid_time_ranges.forEach(rangeInfo => {
      // rangeInfo에 day, start_hour, end_hour 속성이 있으면 JSON 문자열로 인코딩하여 파라미터 추가
      if (rangeInfo.day && rangeInfo.start_hour && rangeInfo.end_hour) {
        params.append("specific_avoid_time_ranges[]", JSON.stringify({
          day: rangeInfo.day,
          start_hour: rangeInfo.start_hour,
          end_hour: rangeInfo.end_hour
        }));
        console.log(
          "[buildParamsFromConstraints] 특정 시간 범위 추가:",
          rangeInfo.day,
          rangeInfo.start_hour + "-" + rangeInfo.end_hour
        );
      }
    });
  }

  // 디버그: 최종적으로 만들어진 URL 쿼리스트링 출력
  console.log("최종 URL 파라미터:", params.toString());

  // URLSearchParams 객체 반환
  return params;
}

// ------------------------------------------------------------
// 전역 변수: 생성된 시간표 목록과 현재 인덱스
// ------------------------------------------------------------
window.timetables   = [];  // 서버로부터 받은 여러 가짓수의 시간표 배열
window.currentIndex = 0;   // 현재 화면에 표시 중인 시간표 인덱스 (0부터 시작)

// ------------------------------------------------------------
// applyTimetableToMiddlePanel: 생성된 시간표를 화면 가운데 패널에 렌더링
// ------------------------------------------------------------
function applyTimetableToMiddlePanel() {
  // 1) 모든 .timetable-cell(테이블 칸) 요소를 가져와서 내부 HTML을 초기화(비우기)
  const timetableCells = document.querySelectorAll(".timetable-cell");
  timetableCells.forEach(cell => cell.innerHTML = "");

  // 2) 시간표 인덱스를 보여주는 DOM 요소
  const timetableIndexElem = document.getElementById("timetable-index");

  // 3) 생성된 시간표가 없으면 "0 / 0" 표시 후 종료
  if (window.timetables.length === 0) {
    timetableIndexElem.textContent = "0 / 0";
    return;
  }

  // 4) 현재 인덱스에 해당하는 시간표 데이터를 lastGeneratedTimetable에 저장
  window.lastGeneratedTimetable = window.timetables[window.currentIndex];
  // 5) currentTimetableCourseIds에는 문자열화한 course_id 목록 저장
  window.currentTimetableCourseIds = window.lastGeneratedTimetable.map(c => String(c.course_id));

  console.log("시간표 적용됨 - window.lastGeneratedTimetable 설정:", window.lastGeneratedTimetable);
  console.log("시간표 과목 수:", window.lastGeneratedTimetable.length);

  // 6) 렌더링할 시간표 데이터 가져오기
  let timetable = window.lastGeneratedTimetable;

  // 7) 각 course_id별로 색상을 할당하기 위한 맵 생성
  let currentColors = {};  // { course_id: colorHex }
  let usedColors = [];     // 이미 사용된 색상 목록

  // 8) timetable 배열을 순회하며 각 강좌(course)마다 고유 색상을 할당
  timetable.forEach(course => {
    // course_id가 아직 색상 맵에 없으면 신규 할당
    if (!currentColors[course.course_id]) {
      // 팔레트에서 사용되지 않은 색상만 골라냄
      let availableColors = colorPalette.filter(c => !usedColors.includes(c));
      // 남은 색상이 있으면 첫 번째, 없으면 랜덤으로 하나 선택
      let color = availableColors.length > 0
        ? availableColors[0]
        : colorPalette[Math.floor(Math.random() * colorPalette.length)];
      // currentColors와 usedColors에 추가
      currentColors[course.course_id] = color;
      usedColors.push(color);
    }
  });

  // 9) 실제 화면에 그리기: timetable 배열을 다시 순회
  timetable.forEach(course => {
    // course 정보
    let courseColor = currentColors[course.course_id]; // 해당 강좌에 할당된 색상
    // schedules: [{day:"월", times:"05,06,07", location:"A동102"}, ...] 형태
    course.schedules.forEach(schedule => {
      let day = schedule.day;          // 요일 문자열
      let timesStr = schedule.times;   // 시간 문자열 (콤마 구분, 숫자 + 2자리)
      let location = schedule.location; // 강의실 정보

      // timesStr이 없으면 해당 일정은 무시
      if (!timesStr) {
        console.warn("No schedule times for course:", course.course_name);
        return;
      }
      // timesStr을 분리하여 숫자로 변환 + 8을 해서 데이터-행 인덱싱(시간표가 8시~ 기준)
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);

      // 요일 문자열(예: "월")을 숫자 인덱스(0~4)로 변환
      let dayIndex = convertDayToIndex(day);
      if (dayIndex === -1) return; // 유효하지 않은 요일이면 건너뛰기

      // 각 timeSlot별로 해당 셀(timetable-cell) 찾아서 강의 정보를 추가
      timeSlots.forEach(slot => {
        // data-hour, data-day 속성 기준 선택
        const cell = document.querySelector(
          `.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`
        );
        if (cell) {
          // cell 내부에 새로운 <div class="lecture"> 추가 (기존 내용 덮어쓰지 않고 append)
          cell.innerHTML += `
            <div class="lecture" style="background-color: ${courseColor} !important;">
              ${course.course_name}<br>${location}
            </div>`;
        }
      });
    });
  });

  // 10) 하단에 "현재 인덱스 + 1 / 총 시간표 개수" 표시
  timetableIndexElem.textContent = `${window.currentIndex + 1} / ${window.timetables.length}`;
}

// ------------------------------------------------------------
// lightenColor: 입력된 hex 색상을 percent 만큼 밝게(하이라이트) 변환하는 함수
// hex: "#aabbcc" 형식, percent: 0~100 (퍼센트 단위)
// ------------------------------------------------------------
function lightenColor(hex, percent) {
  // 1) "#" 제거
  hex = hex.replace(/^#/, '');
  // 2) 정수형으로 변환
  let num = parseInt(hex, 16);
  // 3) RGB 성분 분리
  let r = (num >> 16) & 0xFF;
  let g = (num >> 8) & 0xFF;
  let b = num & 0xFF;
  // 4) percent만큼 밝게 조정 (원래 값과 255 사이의 거리를 percent 비율로 섞음)
  r = Math.min(255, Math.floor(r + (255 - r) * percent / 100));
  g = Math.min(255, Math.floor(g + (255 - g) * percent / 100));
  b = Math.min(255, Math.floor(b + (255 - b) * percent / 100));
  // 5) 다시 hex 문자열로 결합하여 반환
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// ------------------------------------------------------------
// DOMContentLoaded 이벤트: 페이지 DOM이 모두 로드된 후 실행되는 영역
// 초기화 작업, 이벤트 핸들러 등록 등
// ------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM 로드 완료");

  // ------------------------------------------------------------
  // 1) DOM 로드 후 실제 입력 필드 값으로 window.constraints 초기화
  // ------------------------------------------------------------
  const totalCreditsElem = document.getElementById("total-credits");   // 전체 학점 입력 필드
  const majorCreditsElem = document.getElementById("major-credits");   // 전공 학점 입력 필드
  const electiveCreditsElem = document.getElementById("elective-credits"); // 교양 학점 입력 필드

  if (totalCreditsElem) {
    // 입력 필드 값이 숫자면 해당 값으로 덮어쓰고, 없으면 18 유지
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

  // ------------------------------------------------------------
  // 2) 시간표 저장 버튼 유무 확인 (디버그용)
  // ------------------------------------------------------------
  const saveBtnCheck = document.getElementById("save-timetable-btn");
  console.log("시간표 저장 버튼 존재 여부:", saveBtnCheck ? "있음" : "없음");

  // ------------------------------------------------------------
  // 3) 기본 변수 및 DOM 요소 설정
  // ------------------------------------------------------------

  // scheduledSlots: 예약된 시간 슬롯을 요일별로 기록 (이미 추가된 강좌들의 시간을 추적)
  var scheduledSlots = {
    '월': [], '화': [], '수': [], '목': [], '금': []
  };

  // 진행 상황 오버레이 관련 DOM 요소
  const progressOverlay = document.getElementById("progress-overlay"); // 진행 중 오버레이 화면
  const progressText = document.getElementById("progress-text");       // 진행 텍스트
  const progressFill = document.getElementById("progress-fill");       // 진행 바 바디
  const progressCount = document.getElementById("progress-count");     // 진행 카운트 (필요 시)

  // ------------------------------------------------------------
  // 5) 강의 추가/삭제 관련 이벤트 핸들러 등록
  // ------------------------------------------------------------
  // .add-course-btn 버튼 클릭 시 addCourse 호출
  document.querySelectorAll(".add-course-btn").forEach(btn => {
    btn.addEventListener("click", function (event) {
      event.stopPropagation(); // 이벤트 전파 방지
      // 클릭된 버튼과 가장 가까운 .course-item 요소를 가져옴
      const courseItem = this.closest(".course-item");
      addCourse(courseItem);
    });
  });

  // addCourse: courseData(HTMLElement 또는 객체 형태)에서 강좌 정보 추출 후 시간표에 반영
  // 여기서는 courseData를 .course-item 요소 자체로 전달함 (courseData.course_id, schedules, course_name 등이 속성으로 존재해야 함)
  function addCourse(courseData) {
    // courseData.course_id가 문자열이라면, 속성으로 읽어와 문자열로 변환
    const courseId = String(courseData.course_id);

    // 이미 추가된 강좌면 경고 후 종료
    if (window.existingCourses.includes(courseId)) {
      alert("이 강의는 이미 추가되었습니다.");
      return;
    }

    // courseData.schedules: 이미 파싱된 일정 정보 객체 배열 [{day:"월", times:"01,02", location:"강의실A"}, ...]
    const scheduleEntries = courseData.schedules;

    // 일정 정보가 아예 없으면 경고 및 무시 (일반적으로 거의 발생하지 않음)
    if (!scheduleEntries || scheduleEntries.length === 0) {
      console.warn(`강좌 ID ${courseId}: 스케줄 정보가 없습니다.`);
      // 필요하다면 alert("스케줄 정보가 없습니다"); 후 return
    }

    const courseName = courseData.course_name;  // 과목명 문자열
    let courseColor = getCourseColor(courseId); // getCourseColor 함수 호출로 강좌별 색상 얻기

    // scheduleEntries 배열을 순회하며 각 일정(요일, 시간, 강의실)을 시간표 셀에 표시
    scheduleEntries.forEach(schedule => {
      let day = schedule.day;           // "월" 등
      let timesStr = schedule.times;    // "05,06,07,08" 등
      let location = schedule.location || ""; // 강의실 정보, 없으면 빈 문자열

      // timesStr이 없으면 무시
      if (!timesStr) {
        console.warn(`Course ID ${courseId}, Day ${day}: 시간 정보가 없습니다.`);
        return;
      }

      // timesStr을 콤마로 분리하여 ["05","06","07","08"] → 숫자 배열로 변환 → +8 (시간표 행 인덱스 기준)
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      // 숫자 배열을 오름차순 정렬 (연속성 판단을 위해)
      timeSlots.sort((a, b) => a - b);

      // 요일 문자열을 숫자 인덱스(0~4)로 변환
      let dayIndex = convertDayToIndex(day);
      if (dayIndex === -1) {
        console.warn(`Invalid day: ${day} for course ${courseName}`);
        return; // 유효하지 않은 요일이면 건너뛰기
      }

      // 연속된 시간대인지 판단하기 위한 변수 (rowspan 적용용)
      let contiguous = true;
      for (let i = 0; i < timeSlots.length - 1; i++) {
        if (timeSlots[i + 1] !== timeSlots[i] + 1) {
          contiguous = false;
          break;
        }
      }

      if (contiguous && timeSlots.length > 0) {
        // 연속된 블록으로 표시해야 할 경우 (rowspan 사용)
        const startSlot = timeSlots[0];         // 시작 시간(인덱스)
        const rowspan = timeSlots.length;       // row 개수(연속된 개수)
        // 해당 칸(.timetable-cell[data-day][data-hour])을 찾아 첫 번째 셀에만 lecture div 삽입
        const firstCell = document.querySelector(
          `.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot}"]`
        );
        if (firstCell) {
          // 첫 번째 셀에 lecture 정보를 innerHTML로 설정 (기존 내용 덮어쓰기)
          firstCell.innerHTML = `
            <div class="lecture" 
                 data-course-id="${courseId}" 
                 data-course-name="${courseName}" 
                 style="
                   background-color: ${courseColor} !important;
                   height: 100%;
                   display: flex;
                   flex-direction: column;
                   align-items: center;
                   justify-content: center;
                   text-align: center;
                   font-size: 0.8em;
                   padding: 2px;
                 ">
              <span style="font-weight: bold;">${courseName}</span>
              <span style="font-size: 0.9em;">${location}</span>
              <button class="remove-btn" 
                      style="
                        position: absolute; top: 0; right: 0;
                        background: rgba(0,0,0,0.3);
                        color: white;
                        border: none;
                        cursor: pointer;
                        padding: 0 3px;
                        font-size: 0.7em;
                      "
                      onclick="event.stopPropagation(); removeLecture('${courseId}');"
              >X</button>
            </div>
          `;
          // rowspan 속성 추가 (해당 칸이 몇 개의 행을 차지할지)
          firstCell.setAttribute("rowspan", rowspan);
          // rowspan으로 인해 숨겨져야 할 나머지 셀들 처리
          for (let i = 1; i < rowspan; i++) {
            const cellToHide = document.querySelector(
              `.timetable-cell[data-day="${dayIndex}"][data-hour="${startSlot + i}"]`
            );
            if (cellToHide) {
              cellToHide.style.display = "none";  // 숨기기
              cellToHide.innerHTML = "";         // 내용 비우기
            }
          }
        }
      } else {
        // 비연속이거나 single slot인 경우: 각 slot마다 별도로 div 삽입
        timeSlots.forEach(slot => {
          const cell = document.querySelector(
            `.timetable-cell[data-day="${dayIndex}"][data-hour="${slot}"]`
          );
          if (cell) {
            // 혹시 이전에 rowspan으로 숨겨졌다가 복구되어야 할 경우를 대비
            cell.style.display = "";           // table-cell로 표시
            cell.removeAttribute("rowspan");   // rowspan 속성 제거
            // lecture div 삽입
            cell.innerHTML = `
              <div class="lecture" 
                   data-course-id="${courseId}" 
                   data-course-name="${courseName}" 
                   style="
                     background-color: ${courseColor} !important;
                     font-size: 0.8em;
                     padding: 2px;
                     text-align: center;
                   ">
                <span style="font-weight: bold;">${courseName}</span><br>
                <span style="font-size: 0.9em;">${location}</span>
                <button class="remove-btn" 
                        style="
                          position: absolute; top: 0; right: 0;
                          background: rgba(0,0,0,0.3);
                          color: white;
                          border: none;
                          cursor: pointer;
                          padding: 0 3px;
                          font-size: 0.7em;
                        "
                        onclick="event.stopPropagation(); removeLecture('${courseId}');"
                >X</button>
              </div>
            `;
          }
        });
      }

      // ------------------------------------------------------------
      // 6) scheduledSlots 상태 업데이트: 예약된 시간 슬롯 배열에 추가
      // ------------------------------------------------------------
      // scheduledSlots 변수가 전역 또는 함수 스코프에 존재해야 함
      if (typeof scheduledSlots !== 'undefined') {
        timeSlots.forEach(slot => {
          if (scheduledSlots[day]) {
            // 이미 포함되지 않은 시간만 추가하여 중복 방지
            if (!scheduledSlots[day].includes(slot)) {
              scheduledSlots[day].push(slot);
            }
          } else {
            // 해당 요일이 없으면 새 배열로 초기화 후 추가
            scheduledSlots[day] = [slot];
          }
        });
      } else {
        console.warn("scheduledSlots is not defined. Cannot update scheduled time slots.");
      }
    }); // End of scheduleEntries.forEach

    // ------------------------------------------------------------
    // 7) 왼쪽 패널(category_dropdown.js)으로 강좌 추가 완료 이벤트 전파
    // ------------------------------------------------------------
    // left panel에서 강좌를 비활성화하거나, '추가됨' 표시 등을 처리하기 위하여 커스텀 이벤트 발생
    const courseAddedEvent = new CustomEvent('courseSuccessfullyAdded', {
      detail: { courseId: courseId }
    });
    document.dispatchEvent(courseAddedEvent);

    // 8) 전역 existingCourses 배열에도 추가
    window.existingCourses.push(courseId);

    // 9) 시간표 UI에 변화가 있었으므로 (학점 요약 등 다른 UI 업데이트 필요 시 여기서 호출)
    // 예: updateCreditSummary();
  }

  // ------------------------------------------------------------
  // 왼쪽 패널(category_dropdown.js)에서 강좌 추가 요청 이벤트 리스닝
  // ------------------------------------------------------------
  document.addEventListener('addCourseToTimetable', function(event) {
    const courseData = event.detail; // category_dropdown.js에서 보낸 객체 ({course_id, course_name, schedules: [...]})
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
    // addCourse 함수에 해당 객체 그대로 전달
    addCourse(courseData);
  });

  // ------------------------------------------------------------
  // 강좌 삭제 이벤트 리스너: 왼쪽 패널 또는 다른 모듈에서 removeCourseFromTimetable 이벤트 발생 시 호출
  // ------------------------------------------------------------
  document.addEventListener('removeCourseFromTimetable', function(event) {
    const { courseId } = event.detail;
    if (courseId) {
      // 전역 removeLecture 함수 호출
      window.removeLecture(courseId);
    }
  });

  // ------------------------------------------------------------
  // removeLecture: courseId에 해당하는 강의를 시간표에서 제거하는 전역 함수
  // ------------------------------------------------------------
  window.removeLecture = function(courseId) {
    // 1) 타임테이블 UI에서 해당 lecture div 모두 찾아 제거
    document.querySelectorAll(`.lecture[data-course-id="${courseId}"]`).forEach(lecture => {
      let cell = lecture.closest("td"); // lecture div가 있는 td 요소
      if (cell) {
        let rowspan = parseInt(cell.getAttribute("rowspan"), 10); // 해당 셀의 rowspan 값
        cell.innerHTML = "";      // 내용 비우기
        cell.style.display = "";  // 혹시 none인 경우 다시 보이도록 설정
        cell.removeAttribute("rowspan"); // rowspan 속성 제거
        // rowspan이 2 이상이면, 숨겨진 셀들 복원
        if (!isNaN(rowspan) && rowspan > 1) {
          const day = cell.getAttribute("data-day");
          const startHour = parseInt(cell.getAttribute("data-hour"), 10);
          for (let i = 1; i < rowspan; i++) {
            const nextCell = document.querySelector(
              `.timetable-cell[data-hour="${startHour + i}"][data-day="${day}"]`
            );
            if (nextCell) {
              nextCell.style.display = "table-cell"; // 숨겨진 셀 복원
            }
          }
        }
      }
    });

    // 2) 전역 상태 existingCourses에서 해당 courseId 제거
    window.existingCourses = window.existingCourses.filter(id => id !== courseId);

    // 3) scheduledSlots를 초기화 후, 남은 lecture들을 기준으로 재계산
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

    // 4) 왼쪽 패널 .course-item 요소에서 “added” 클래스 제거 (UI 변경)
    document.querySelectorAll(`.course-item[data-course-id="${courseId}"]`).forEach(item => {
      item.classList.remove("added");
    });
    // 5) 필터 조건이 바뀔 수 있으므로 filterCourses 다시 호출하여 목록 갱신
    filterCourses();
  };

  // ------------------------------------------------------------
  // 6) 시간표 셀(.timetable-cell) 클릭 시 수동으로 강의명 입력받아 추가하는 예시 코드
  // ------------------------------------------------------------
  document.querySelectorAll(".timetable-cell").forEach(cell => {
    cell.addEventListener("click", function () {
      let courseName = prompt("강의명을 입력하세요:");
      if (courseName) {
        // 클릭한 셀 내용 비우고 새로운 lecture div 생성 후 추가
        this.innerHTML = "";
        let lectureDiv = document.createElement("div");
        lectureDiv.classList.add("lecture");
        lectureDiv.textContent = courseName;
        // 삭제 버튼 추가
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

  // manualRemoveLecture: 수동으로 추가한 lecture를 제거하는 함수
  function manualRemoveLecture(event, button) {
    event.stopPropagation();        // 이벤트 전파 방지
    let cell = button.closest("td");
    cell.innerHTML = "";            // 클릭된 lecture를 포함한 셀 내용 비우기
  }

  // ------------------------------------------------------------
  // 7) 시간표 생성 관련: SSE를 통해 서버에서 실시간 진행 상황 표시
  // ------------------------------------------------------------
  const totalCreditsInput = document.getElementById("total-credits");     // 전체 학점 입력 필드
  const majorCreditsInput = document.getElementById("major-credits");     // 전공 학점 입력 필드
  const electiveCreditsInput = document.getElementById("elective-credits"); // 교양 학점 입력 필드
  const generateButton = document.getElementById("generate-btn");         // 시간표 생성 버튼
  const prevButton = document.getElementById("prev-timetable");           // 이전 시간표 보기 버튼
  const nextButton = document.getElementById("next-timetable");           // 다음 시간표 보기 버튼
  const timetableIndex = document.getElementById("timetable-index");      // 인덱스 표시 영역
  let timetables = [];    // 로컬 복사본: 서버로부터 받은 시간표 목록 (window.timetables와 동일할 수도 있음)
  let currentIndex = 0;   // 현재 timetables 배열 내 인덱스 (0부터)

  if (generateButton) {
    // 클릭 이벤트 등록
    generateButton.addEventListener("click", function () {
      // ① 진행 오버레이 띄우기 및 초기 텍스트 설정
      progressOverlay.style.display = "block";
      progressText.textContent = "시간표 생성 시작...";
      progressFill.style.width = "0%";
      progressCount.textContent = "";

      // ② UI 입력값 가져오기 (문자열 상태)
      let totalCredits = totalCreditsInput.value;
      let majorCredits = majorCreditsInput.value;
      let electiveCredits = electiveCreditsInput.value;
      // freeDays: 체크된 요일 목록 (input[type=checkbox])
      let freeDays = [];
      document.querySelectorAll(".day-options input:checked").forEach(checkbox => {
        freeDays.push(checkbox.value);
      });

      // ------------------------------------------------------------
      // ③ 콘솔에 UI 입력값 디버그 출력
      // ------------------------------------------------------------
      console.log("[시간표 생성] UI 입력값 확인:");
      console.log("  totalCreditsInput.value:", totalCreditsInput.value);
      console.log("  majorCreditsInput.value:", majorCreditsInput.value);
      console.log("  electiveCreditsInput.value:", electiveCreditsInput.value);

      // ④ window.constraints 객체를 입력값으로 업데이트
      window.constraints.total_credits    = Number(totalCreditsInput.value);
      window.constraints.major_credits    = Number(majorCreditsInput.value);
      window.constraints.elective_credits = Number(electiveCreditsInput.value);
      window.constraints.free_days = Array.from(
        document.querySelectorAll(".day-options input:checked")
      ).map(cb => cb.value);

      console.log("[시간표 생성] window.constraints 업데이트 후:");
      console.log("  window.constraints.total_credits:", window.constraints.total_credits);
      console.log("  window.constraints.major_credits:", window.constraints.major_credits);
      console.log("  window.constraints.elective_credits:", window.constraints.elective_credits);

      // ------------------------------------------------------------
      // ⑤ SSE 연결을 위해 buildParamsFromConstraints 호출 (쿼리파라미터 생성)
      // ------------------------------------------------------------
      const params = buildParamsFromConstraints();
      // "/generate_timetable_stream/?" 뒤에 params.toString()으로 붙여서 EventSource URL 완성
      const evtSource = new EventSource("/generate_timetable_stream/?" + params.toString());

      // ------------------------------------------------------------
      // ⑥ EventSource.onmessage: 서버에서 보낸 데이터에 따라 진행 표시 또는 최종 시간표 수신 처리
      // ------------------------------------------------------------
      evtSource.onmessage = e => {
        const data = JSON.parse(e.data);
        // 서버에서 data.progress === "완료"를 보내면, 최종 데이터(data.timetables) 처리
        if (data.progress === "완료") {
          // 1) 전역 window.timetables 업데이트
          window.timetables = data.timetables;
          window.currentIndex = 0;

          // 2) 수정 모드(is_modification)인 경우, 플래그만 리셋, 기존 existing_courses는 유지
          if (window.constraints.is_modification) {
            console.log("수정 모드 완료, 제약조건 유지");
            window.constraints.is_modification = false;
          }

          // 3) 0.8초 뒤에 진행 오버레이 사라짐
          setTimeout(() => progressOverlay.style.display = "none", 800);
          // 4) 화면 가운데 시간표 렌더링 호출
          applyTimetadbleToMiddlePanel();
          // 5) EventSource 연결 종료
          evtSource.close();
        } else {
          // 진행 중 메시지가 올 때마다 화면 텍스트 갱신
          let progressMsg = "시간표 생성 중...";
          if (data.processed !== undefined && data.found !== undefined) {
            progressMsg = `처리된 조합: ${data.processed}, 후보: ${data.found}`;
          }
          progressText.textContent = progressMsg;
        }
      };

      // ------------------------------------------------------------
      // ⑦ EventSource.onerror: 에러 발생 시 처리
      // ------------------------------------------------------------
      evtSource.onerror = function(event) {
        progressText.textContent = "오류 발생";
        evtSource.close();
        // 2초 후 오버레이 숨김
        setTimeout(() => { progressOverlay.style.display = "none"; }, 2000);
      };
    });
  }

  // ------------------------------------------------------------
  // 8) getCourseColor: 강좌 ID별 고유 색상을 반환하는 함수
  // ------------------------------------------------------------
  function getCourseColor(courseId) {
    // 이미 lectureColors에 해당 ID가 있으면 그대로 반환
    if (lectureColors[courseId]) {
      return lectureColors[courseId];
    }
    // 사용 중인 색상을 existingCourses 배열에서 모으기
    var usedColors = [];
    window.existingCourses.forEach(function(id) {
      if (lectureColors[id]) {
        usedColors.push(lectureColors[id]);
      }
    });
    // 팔레트에서 사용되지 않은 색상만 필터링
    var availableColors = colorPalette.filter(function(color) {
      return usedColors.indexOf(color) === -1;
    });
    if (availableColors.length > 0) {
      // 남은 색상이 있으면 그중 첫 번째를 사용
      lectureColors[courseId] = availableColors[0];
    } else {
      // 팔레트가 모두 사용된 경우 랜덤으로 색상 선택
      var randomIndex = Math.floor(Math.random() * colorPalette.length);
      lectureColors[courseId] = colorPalette[randomIndex];
    }
    return lectureColors[courseId];
  }

  // ------------------------------------------------------------
  // 9) 중간 패널에 시간표를 적용하는 함수 (생성된 시간표 렌더링)
  // (applyTimetableToMiddlePanel 함수와 유사하지만, courseId 문자열 사용)
  // ------------------------------------------------------------

  // ------------------------------------------------------------
  // 10) 요일 인덱스 변환 함수
  // (convertDayToIndex 함수와 동일. 필요 시 참조.)
  // ------------------------------------------------------------

  // ------------------------------------------------------------
  // 11) 이전/다음 버튼 이벤트 핸들러
  // ------------------------------------------------------------
  if (prevButton) {
    prevButton.addEventListener("click", function () {
      if (currentIndex > 0) {
        currentIndex--;
        applyTimetableToMiddlePanel(); // 인덱스 감소 후 다시 렌더링
      }
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", function () {
      if (currentIndex < timetables.length - 1) {
        currentIndex++;
        applyTimetableToMiddlePanel(); // 인덱스 증가 후 다시 렌더링
      }
    });
  }

  // ------------------------------------------------------------
  // 12) 강좌 미리보기 오버레이 (course-item 마우스 엔터/리브 이벤트)
  // ------------------------------------------------------------
  function showPreview(courseItem) {
    // 이미 added 클래스가 있으면 미리보기 생략
    if (courseItem.classList.contains("added")) return;

    let schedulesElem = courseItem.querySelector(".course-schedules");
    if (!schedulesElem) return;
    let schedulesStr = schedulesElem.textContent.trim();
    if (!schedulesStr) return;

    // "월:07,08@강의실101;화:09@강의실202" 형식 파싱
    let scheduleEntries = schedulesStr.split(";").map(entry => {
      let parts = entry.split(":");
      let timeAndLoc = parts[1].split("@");
      return {
        day: parts[0].trim(),
        times: timeAndLoc[0].trim(),
        location: timeAndLoc[1] ? timeAndLoc[1].trim() : ""
      };
    });

    let courseId = courseItem.getAttribute("data-course-id");           // 강좌 ID
    let courseColor = getCourseColor(courseId);                          // 강좌별 색상
    let courseName = courseItem.querySelector(".course-name").textContent.trim(); // 과목명
    let previewColor = lightenColor(courseColor, 30);                    // 원색 대비 30% 밝게 한 색상

    // 각 일정 항목마다 미리보기 div 생성
    scheduleEntries.forEach(schedule => {
      let day = schedule.day;
      let timesStr = schedule.times;
      let location = schedule.location;
      if (!timesStr) return;
      // timesStr을 숫자 배열로 변환(+8 인덱스)
      let timeSlots = timesStr.split(",").map(str => parseInt(str, 10) + 8);
      // 요일을 숫자 인덱스(0~4)로 변환
      let dayIndex = convertDayToIndex(day);
      if (dayIndex === -1) return;
      // 각 시간 슬롯마다 셀을 찾아 preview 추가
      timeSlots.forEach(slot => {
        const cell = document.querySelector(`.timetable-cell[data-hour="${slot}"][data-day="${dayIndex}"]`);
        if (cell) {
          // 셀의 position이 static이면 relative로 변경 (absolute 요소 배치 용이)
          if (getComputedStyle(cell).position === "static") {
            cell.style.position = "relative";
          }
          // 중복 방지를 위해 이미 같은 courseId에 대한 preview가 있는지 확인
          if (!cell.querySelector(`.preview-lecture[data-preview-for="${courseId}"]`)) {
            let previewDiv = document.createElement("div");
            previewDiv.classList.add("preview-lecture");
            // 스타일 설정: 반투명 배경, 절대 위치, 전체 셀 크기 덮기, 텍스트 중앙 정렬 등
            previewDiv.style.backgroundColor = previewColor;
            previewDiv.style.opacity = "0.3";
            previewDiv.style.position = "absolute";
            previewDiv.style.top = "0";
            previewDiv.style.left = "0";
            previewDiv.style.width = "100%";
            previewDiv.style.height = "100%";
            previewDiv.style.pointerEvents = "none"; // 클릭 등 이벤트 통과
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

  // hidePreview: courseItem 마우스가 떠날 때 호출, 해당 과목의 preview 모두 제거
  function hidePreview(courseItem) {
    let courseId = courseItem.getAttribute("data-course-id");
    document.querySelectorAll(`.preview-lecture[data-preview-for="${courseId}"]`).forEach(previewDiv => {
      previewDiv.remove();
    });
  }

  // .course-item 요소마다 마우스 엔터/리브 이벤트 리스너 추가
  document.querySelectorAll(".course-item").forEach(courseItem => {
    courseItem.addEventListener("mouseenter", function() {
      showPreview(this);
    });
    courseItem.addEventListener("mouseleave", function() {
      hidePreview(this);
    });
  });

  // ------------------------------------------------------------
  // 13) 학점 조정 및 시간표 저장 (추후 구현)
  // ------------------------------------------------------------
  const saveTimetableBtn = document.getElementById("save-timetable-btn");

  // adjustCredits: total/major/elective 입력값 변화 시 상대적 값을 계산하여 업데이트
  function adjustCredits(changedInput) {
    let total = parseInt(totalCreditsInput.value) || 0;
    let major = parseInt(majorCreditsInput.value) || 0;
    let elective = parseInt(electiveCreditsInput.value) || 0;
    if (changedInput === "major") {
      // 전공 학점을 변경하면 교양 학점은 total - major 로 설정
      elective = total - major;
      if (elective < 0) elective = 0;
      electiveCreditsInput.value = elective;
    } else if (changedInput === "elective") {
      // 교양 학점을 변경하면 전공 학점은 total - elective 로 설정
      major = total - elective;
      if (major < 0) major = 0;
      majorCreditsInput.value = major;
    }

    // window.constraints에도 동기화
    window.constraints.total_credits = total;
    window.constraints.major_credits = parseInt(majorCreditsInput.value) || 0;
    window.constraints.elective_credits = parseInt(electiveCreditsInput.value) || 0;
  }

  // totalCreditsInput: 입력값이 바뀔 때 유효 범위(1~24)로 제한 후 adjustCredits 호출
  if (totalCreditsInput) {
    totalCreditsInput.addEventListener("input", function () {
      let total = parseInt(this.value);
      if (total < 1) total = 1;
      if (total > 24) total = 24;
      this.value = total;
      adjustCredits();
      window.constraints.total_credits = total;
    });
  }

  // majorCreditsInput: 전공 학점 입력 시 adjustCredits("major") 호출
  if (majorCreditsInput) {
    majorCreditsInput.addEventListener("input", function () {
      adjustCredits("major");
      window.constraints.major_credits = parseInt(this.value) || 0;
    });
  }

  // electiveCreditsInput: 교양 학점 입력 시 adjustCredits("elective") 호출
  if (electiveCreditsInput) {
    electiveCreditsInput.addEventListener("input", function () {
      adjustCredits("elective");
      window.constraints.elective_credits = parseInt(this.value) || 0;
    });
  }

  // ------------------------------------------------------------
  // saveTimetableBtn 클릭 이벤트: 서버에 시간표 저장 요청
  // ------------------------------------------------------------
  if (saveTimetableBtn) {
    saveTimetableBtn.addEventListener("click", async function () {
      console.log("시간표 저장 버튼 클릭됨");
      console.log("window.lastGeneratedTimetable:", window.lastGeneratedTimetable);

      // 1) 현재 표시된 시간표 데이터가 있는지 확인
      if (!window.lastGeneratedTimetable || window.lastGeneratedTimetable.length === 0) {
        alert("저장할 시간표가 없습니다. 먼저 시간표를 생성해주세요.");
        return;
      }

      console.log("시간표 데이터 검증 통과");

      // 2) CSRF 토큰 가져오기 함수 정의 (Django CSRF 쿠키에서 읽음)
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

      // 3) 서버로 보낼 시간표 데이터(timetableData) 준비
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
        title: '' // 서버에서 자동 생성하도록 비워둠
      };

      console.log("저장할 시간표 데이터:", timetableData);
      console.log("첫 번째 과목 상세:", timetableData.courses[0]);
      if (timetableData.courses[0] && timetableData.courses[0].schedules) {
        console.log("첫 번째 과목 스케줄:", timetableData.courses[0].schedules);
      }

      console.log("서버로 요청 전송 시작...");

      try {
        // 4) fetch로 '/save_timetable/' 엔드포인트에 POST 요청
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

// ------------------------------------------------------------
// generateTimetableFromNL: 자연어 제약조건(nlText)을 서버에 파싱 요청하고,
// 수정 모드 감지 및 적절한 시간표 생성(params 빌드 후 SSE 연결) 로직
// ------------------------------------------------------------
async function generateTimetableFromNL(nlText) {
  return new Promise(async (resolve, reject) => {
    try {
      // 1) parse_constraints API에 자연어 텍스트 전송하여 JSON 결과 수신
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
      // 파싱된 JSON 객체 (major_credits, free_days, exclude_courses 등 포함)
      const parsed = await parseRes.json();
      // 2) parsed 결과를 window.constraints에 동기화
      Object.keys(parsed).forEach(key => {
        if (parsed[key] !== undefined) window.constraints[key] = parsed[key];
      });
      // 학점 입력 필드 값도 업데이트
      document.getElementById('major-credits').value    = window.constraints.major_credits;
      document.getElementById('elective-credits').value = window.constraints.elective_credits;

      // 3) 이전 상태 저장
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
      const elective_credits = parsed.elective_credits ?? prev.elective_credits;

      // 4) 수정 모드 감지 로직: exclude_courses가 있거나, 기존 constraints.is_modification 또는 existing_courses에 값이 있으면 수정 모드
      const isModification = (
        (parsed.exclude_courses && parsed.exclude_courses.length > 0) ||
        window.constraints.is_modification ||
        (window.constraints.existing_courses && window.constraints.existing_courses.length > 0)
      );

      console.log("수정 모드 감지:", {
        "parsed.exclude_courses": parsed.exclude_courses,
        "window.constraints.is_modification": window.constraints.is_modification,
        "window.constraints.existing_courses": window.constraints.existing_courses,
        "isModification": isModification
      });

      let idsToPassToBuilder = []; // 최종적으로 생성기(buildParamsFromConstraints)에 넘길 course_id 배열

      // ------------------------------------------------------------
      // 5) 수정 모드일 때: 제외할 과목 처리 및 고정(fix)된 course_id 추출
      // ------------------------------------------------------------
      if (isModification) {
        console.log("Modification request detected. Excluding:", parsed.exclude_courses);

        // 5-1) constraints.existing_courses가 이미 있으면 우선 사용 (Rasa에서 넘어온 경우)
        if (window.constraints.existing_courses && window.constraints.existing_courses.length > 0) {
          console.log("Using existing_courses from constraints:", window.constraints.existing_courses);
          idsToPassToBuilder = window.constraints.existing_courses.map(id => String(id));
        }
        // 5-2) 그렇지 않고 lastGeneratedTimetable이 있으면, exclude_courses를 기준으로 필터링
        else if (window.lastGeneratedTimetable && window.lastGeneratedTimetable.length > 0) {
          console.log("Base timetable for modification:", JSON.stringify(
            window.lastGeneratedTimetable.map(c => ({id: c.course_id, name: c.course_name}))
          ));

          // 제외할 과목명 배열을 소문자로 변환
          const coursesToExclude = (parsed.exclude_courses || []).map(name => name.toLowerCase());
          console.log("Courses to exclude (lowercase):", coursesToExclude);

          // lastGeneratedTimetable에서, course_name 소문자가 제외할 과목명 배열에 포함되지 않는 강좌들만 필터링
          const filteredTimetable = window.lastGeneratedTimetable.filter(course => {
            if (!course || typeof course.course_name !== 'string') {
              console.warn("Skipping course in filter due to missing/invalid name:", course);
              return false;
            }
            const courseNameLower = course.course_name.toLowerCase();
            const shouldExclude = coursesToExclude.some(exName => courseNameLower.includes(exName));
            return !shouldExclude;
          });
          console.log("Filtered timetable (courses to keep):", JSON.stringify(
            filteredTimetable.map(c => ({id: c.course_id, name: c.course_name}))
          ));
          // 필터링된 강좌의 course_id만 추출
          idsToPassToBuilder = filteredTimetable.map(course => String(course.course_id));
        }
        // 5-3) 수정 모드인데 이전 생성된 시간표 정보가 없으면 오류 처리
        else {
          alert("이전 생성된 시간표 정보가 없습니다. 먼저 시간표를 생성해주세요.");
          console.error("Cannot modify: no previous timetable information available.");
          reject(new Error("이전 시간표 정보 없음"));
          return;
        }

        console.log("Fixed course IDs for modification:", JSON.stringify(idsToPassToBuilder));

        // 5-4) parsed.exclude_courses를 constraints.exclude_courses로 저장
        window.constraints.exclude_courses = parsed.exclude_courses || [];

        // 5-5) 다른 제약조건도 parsed 결과로 업데이트 (값이 undefined면 이전 값 유지)
        window.constraints.major_credits = parsed.major_credits ?? prev.major_credits;
        window.constraints.elective_credits = parsed.elective_credits ?? prev.elective_credits;
        window.constraints.required_courses = parsed.required_courses ?? prev.required_courses;
        window.constraints.free_days = parsed.free_days ?? prev.free_days;
        window.constraints.avoid_times = parsed.avoid_times ?? prev.avoid_times;
        window.constraints.avoid_time_ranges = parsed.avoid_time_ranges ?? prev.avoid_time_ranges;
        window.constraints.only_time_ranges = parsed.only_time_ranges ?? prev.only_time_ranges;

      } else {
        // ------------------------------------------------------------
        // 6) 수정 모드가 아닐 때: 첫 생성 요청 (수동으로 추가된 강좌 사용)
        // ------------------------------------------------------------
        console.log("Initial generation request from NL.");
        // .course-item.added 클래스를 가진 요소의 data-course-id 속성 배열 추출
        idsToPassToBuilder = Array.from(
          document.querySelectorAll(".course-item.added")
        ).map(el => el.dataset.courseId);
        console.log("Using manually added courses for initial NL generation:", JSON.stringify(idsToPassToBuilder));

        // parsed 결과를 모두 window.constraints에 업데이트 (필수값만 덮어쓰기)
        Object.keys(parsed).forEach(key => {
          if (parsed[key] !== undefined) {
            window.constraints[key] = parsed[key];
          }
        });
        // exclude_courses가 제공되지 않았으면 빈 배열로 설정
        window.constraints.exclude_courses = parsed.exclude_courses || [];

        // UI 입력 필드에도 parsed된 학점 반영
        document.getElementById('major-credits').value = window.constraints.major_credits;
        document.getElementById('elective-credits').value = window.constraints.elective_credits;
      }

      // ------------------------------------------------------------
      // 7) buildParamsFromConstraints 호출하여 URLSearchParams 생성
      // ------------------------------------------------------------
      console.log("IDs being passed to buildParamsFromConstraints:", JSON.stringify(idsToPassToBuilder));
      // 수정 모드인 경우 exclude_courses가 반영되도록 constraints를 이미 설정했음
      const paramsObject = buildParamsFromConstraints(idsToPassToBuilder);
      const paramsString = paramsObject.toString(); // 디버그용 문자열 버전
      console.log("Generated URL Params Object:", paramsObject);
      console.log("Generated URL Params String:", paramsString);

      // ------------------------------------------------------------
      // 8) SSE를 통해 시간표 생성 스트림 요청 (EventSource 생성)
      // ------------------------------------------------------------
      // 쿼리스트링이 URI 인코딩된 경우 디코딩하여 EventSource에 전달
      const eventSourceUrl = "/generate_timetable_stream/?" + decodeURIComponent(paramsString);
      console.log("EventSource URL:", eventSourceUrl);
      const evtSource = new EventSource(eventSourceUrl);
      const progressOverlay = document.getElementById("progress-overlay");
      const progressText    = document.getElementById("progress-text");

      progressOverlay.style.display = "block";       // 진행 오버레이 보이기
      progressText.textContent   = "시간표 생성 중…"; // 초기 텍스트

      // ------------------------------------------------------------
      // 9) EventSource onmessage: 서버에서 보낸 진행 상황/완료 메시지 처리
      // ------------------------------------------------------------
      evtSource.onmessage = e => {
        const data = JSON.parse(e.data);
        if (data.progress === "완료") {
          // 완료 시 window.timetables 업데이트, 인덱스 초기화
          window.timetables   = data.timetables;
          window.currentIndex = 0;

          // 수정 모드 처리: constraints.is_modification 플래그만 false로 리셋 (existing_courses 유지)
          if (window.constraints.is_modification) {
            console.log("수정 모드 완료, 제약조건 유지");
            window.constraints.is_modification = false;
          }

          // 오버레이 숨기기 (약간 지연)
          setTimeout(() => progressOverlay.style.display = "none", 800);
          // 시간표 렌더
          applyTimetableToMiddlePanel();
          // EventSource 연결 닫기
          evtSource.close();
          resolve(); // Promise 완료
        } else {
          // 진행 중이면 processed/found 정보 기반 진행 메시지 설정
          let progressMsg = "시간표 생성 중...";
          if (data.processed !== undefined && data.found !== undefined) {
            progressMsg = `처리된 조합: ${data.processed}, 후보: ${data.found}`;
          }
          progressText.textContent = progressMsg;
        }
      };

      // ------------------------------------------------------------
      // 10) EventSource onerror: 에러 발생 시 처리
      // ------------------------------------------------------------
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
