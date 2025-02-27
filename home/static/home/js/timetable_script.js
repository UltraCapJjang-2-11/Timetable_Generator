
// ✅ 시간표 블럭 클릭 시 기능
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".timetable-cell").forEach(cell => {
        cell.addEventListener("click", function () {
            let courseName = prompt("강의명을 입력하세요:");
            if (courseName) {
                this.innerHTML = ""; // ✅ 기존 내용을 지우고 새로 추가

                let lectureDiv = document.createElement("div");
                lectureDiv.classList.add("lecture");
                lectureDiv.textContent = courseName;

                let removeBtn = document.createElement("button");
                removeBtn.classList.add("remove-btn");
                removeBtn.innerHTML = "X"; // ✅ X 버튼 추가
                removeBtn.onclick = function (event) {
                    removeLecture(event, this);
                };

                lectureDiv.appendChild(removeBtn);
                this.appendChild(lectureDiv);
            }
        });
    });
});
/* ✅ 강의 삭제 함수 */
function removeLecture(event, button) {
    event.stopPropagation(); // ✅ 삭제 버튼 클릭 시 상위 `td` 클릭 이벤트 방지
    let cell = button.closest("td"); // ✅ 현재 셀 찾기
    cell.innerHTML = ""; // ✅ 강의 삭제
}


// ✅ 강의 검색, 필터, 추가 기능
document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("course-search");
    const filterButtons = document.querySelectorAll(".filter-btn");
    let activeFilter = "all"; // ✅ 현재 선택된 필터 저장

    // ✅ 필터 기능 (전공필수, 전공선택 등)
    filterButtons.forEach(button => {
        button.addEventListener("click", function() {
            // ✅ 모든 필터 버튼 비활성화 후 현재 버튼 활성화
            filterButtons.forEach(btn => btn.classList.remove("active"));
            this.classList.add("active");

            // ✅ 현재 선택된 필터 저장
            activeFilter = this.dataset.type;
            filterCourses();
        });
    });

    // ✅ 검색 기능 (선택된 필터 내에서만 검색)
    searchInput.addEventListener("input", function() {
        filterCourses();
    });

    // ✅ 강의 필터링 함수
    function filterCourses() {
        const keyword = searchInput.value.toLowerCase();
        document.querySelectorAll(".course-item").forEach(item => {
            const name = item.querySelector(".course-name").textContent.toLowerCase();
            const courseType = item.dataset.type;

            // ✅ 필터 조건 확인 (전체 or 선택된 카테고리 내에서 검색)
            const isMatchingType = (activeFilter === "all" || courseType === activeFilter);
            const isMatchingSearch = name.includes(keyword);

            // ✅ 필터와 검색 조건을 모두 만족하는 경우만 표시
            item.style.display = (isMatchingType && isMatchingSearch) ? "flex" : "none";
        });
    }
});

// ✅ 시간표 생성 관련 입력 기능
document.addEventListener("DOMContentLoaded", function() {
    const totalCreditsInput = document.getElementById("total-credits");
    const majorCreditsInput = document.getElementById("major-credits");
    const electiveCreditsInput = document.getElementById("elective-credits");
    const generateBtn = document.getElementById("generate-btn");

    // ✅ 전공 & 교양 학점 입력 시 합이 자동으로 맞춰짐
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

    // ✅ 목표 학점 변경 시 자동 조정
    totalCreditsInput.addEventListener("input", function() {
        let total = parseInt(this.value);
        if (total < 1) total = 1;
        if (total > 24) total = 24;
        this.value = total;
        adjustCredits();
    });

    // ✅ 전공 학점 입력 시 교양 학점 자동 조정
    majorCreditsInput.addEventListener("input", function() {
        adjustCredits("major");
    });

    // ✅ 교양 학점 입력 시 전공 학점 자동 조정
    electiveCreditsInput.addEventListener("input", function() {
        adjustCredits("elective");
    });

});

// ✅ 시간표 테스트용 랜덤 생성 (여러개 생성 후 선택한 시간표 랜더링)
document.addEventListener("DOMContentLoaded", function () {
    const generateButton = document.getElementById("generate-btn");
    const prevButton = document.getElementById("prev-timetable");
    const nextButton = document.getElementById("next-timetable");
    const timetableIndex = document.getElementById("timetable-index");

    let timetables = [];
    let currentIndex = 0;

    // ✅ 시간표 생성 버튼 클릭 이벤트
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

    // ✅ 가운데 시간표에 적용하는 함수
    function applyTimetableToMiddlePanel() {
        const timetableCells = document.querySelectorAll(".timetable-cell");
        timetableCells.forEach(cell => cell.innerHTML = ""); // ✅ 기존 데이터 초기화

        if (timetables.length === 0) {
            timetableIndex.textContent = "0 / 0";
            return;
        }

        let timetable = timetables[currentIndex];

        timetable.forEach(entry => {
            const { course_name, day, times, location } = entry;

            console.log(`📌 DEBUG: Processing ${course_name}, Day: ${day}, Time: ${times}`);

            // ✅ 시간 범위 파싱 ("07:00-08:00")
            let [startTime, endTime] = times.split("-");
            startTime = parseInt(startTime, 10);
            endTime = parseInt(endTime, 10);

            let dayIndex = convertDayToIndex(day);
            if (dayIndex === -1) return;

            for (let hour = startTime; hour < endTime; hour++) {
                const cell = document.querySelector(`.timetable-cell[data-hour="${hour}"][data-day="${dayIndex}"]`);
                if (cell) {
                    console.log(`✅ DEBUG: Adding ${course_name} to ${hour}:00 on day ${dayIndex}`);
                    cell.innerHTML = `<div class="lecture">${course_name}<br>${location}</div>`;
                } else {
                    console.warn(`⚠️ WARNING: No matching cell found for ${hour}:00 on day ${dayIndex}`);
                }
            }
        });

        timetableIndex.textContent = `${currentIndex + 1} / ${timetables.length}`;
    }

    function convertDayToIndex(day) {
        const days = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 };
        return days[day] !== undefined ? days[day] : -1;
    }

    prevButton.addEventListener("click", function () {
        if (currentIndex > 0) {
            currentIndex--;
            applyTimetableToMiddlePanel();
        }
    });

    nextButton.addEventListener("click", function () {
        if (currentIndex < timetables.length - 1) {
            currentIndex++;
            applyTimetableToMiddlePanel();
        }
    });
});






// ✅ 시간표 저장 관련 기능
document.addEventListener("DOMContentLoaded", function() {
    const totalCreditsInput = document.getElementById("total-credits");
    const majorCreditsInput = document.getElementById("major-credits");
    const electiveCreditsInput = document.getElementById("elective-credits");
    const generateBtn = document.getElementById("generate-btn");
    const saveTimetableBtn = document.getElementById("save-timetable-btn");

    // ✅ 시간표 저장 버튼 클릭 이벤트
    saveTimetableBtn.addEventListener("click", function() {
        const totalCredits = totalCreditsInput.value;
        const majorCredits = majorCreditsInput.value;
        const electiveCredits = electiveCreditsInput.value;

        // ✅ 선택된 공강 요일 확인
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
});


