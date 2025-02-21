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
