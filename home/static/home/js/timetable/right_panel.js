document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 요소 캐싱 ---
    const courseListContainer = document.getElementById('current-course-list');
    const majorCreditsInput = document.getElementById('major-credits');
    const electiveCreditsInput = document.getElementById('elective-credits');
    const totalCreditsDisplay = document.getElementById('total-credits-display');

    // --- 총 학점 동적 업데이트 함수 ---
    function updateTotalCredits() {
        const majorCredits = parseInt(majorCreditsInput.value, 10) || 0;
        const electiveCredits = parseInt(electiveCreditsInput.value, 10) || 0;
        totalCreditsDisplay.textContent = majorCredits + electiveCredits;
    }

    // --- 이벤트 리스너 할당 ---

    // 전공/교양 학점 변경 시 총 학점 업데이트
    majorCreditsInput.addEventListener('input', updateTotalCredits);
    electiveCreditsInput.addEventListener('input', updateTotalCredits);

    // 현재 시간표 강의 목록 업데이트 (이전과 동일)
    document.addEventListener('timetableRendered', (e) => {
        const timetable = e.detail.timetable;
        courseListContainer.innerHTML = '';

        if (!timetable || !timetable.courses || timetable.courses.length === 0) {
            courseListContainer.innerHTML = '<p class="placeholder">표시할 강의가 없습니다.</p>';
            return;
        }

        timetable.courses.forEach(course => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'current-course-item';

            itemDiv.innerHTML = `
                <button class="remove-from-list-btn" title="${course.name} 삭제">-</button>
                <div>
                    <div class="course-title">${course.name} (${course.code}-${course.section})</div>
                    <div class="course-details">${course.instructor}</div>
                </div>
            `;

            // 삭제 버튼에 이벤트 리스너 추가
            itemDiv.querySelector('.remove-from-list-btn').addEventListener('click', () => {
                // main.js가 수신할 이벤트를 발생시킴
                document.dispatchEvent(new CustomEvent('removeCourseFromView', {
                    detail: { courseId: course.id }
                }));
            });

            courseListContainer.appendChild(itemDiv);
        });
    });

    // 페이지 로드 시 초기 총 학점 계산
    updateTotalCredits();
});