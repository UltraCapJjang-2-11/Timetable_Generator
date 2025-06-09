document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 요소 캐싱 ---
    const courseListContainer = document.getElementById('current-course-list');
    const majorCreditsInput = document.getElementById('major-credits');
    const electiveCreditsInput = document.getElementById('elective-credits');
    const totalCreditsDisplay = document.getElementById('total-credits-display');

    // 고정 학점 표시를 위한 버튼 요소 추가
    const pinnedMajorDisplay = document.getElementById('pinned-major-credits');
    const pinnedElectiveDisplay = document.getElementById('pinned-elective-credits');

    // 총 학점 동적 업데이트 함수
    function updateTotalCredits() {
        const majorCredits = parseInt(majorCreditsInput.value, 10) || 0;
        const electiveCredits = parseInt(electiveCreditsInput.value, 10) || 0;
        totalCreditsDisplay.textContent = majorCredits + electiveCredits;
    }

    /**
     * 고정된 강의의 학점을 계산하고 UI에 업데이트하는 함수
     * @param {Timetable | null} timetable
     */
    function updatePinnedCreditsDisplay(timetable) {
        let pinnedMajorCredits = 0;
        let pinnedElectiveCredits = 0;

        if (timetable && timetable.courses) {
            timetable.courses.forEach(course => {
                if (course.isPinned) { // 고정된 강의인지 확인
                    if (course.categoryName.includes('전공')) {
                        pinnedMajorCredits += course.credits;
                    } else {
                        pinnedElectiveCredits += course.credits;
                    }
                }
            });
        }

        // 계산된 값으로 버튼 텍스트 업데이트
        pinnedMajorDisplay.textContent = `${pinnedMajorCredits}`;
        pinnedElectiveDisplay.textContent = `${pinnedElectiveCredits}`;
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
            let text = '고정';
            if(course.isPinned) text = '고정됨'

            itemDiv.className = 'current-course-item';
            itemDiv.innerHTML = `
                <button class="remove-from-list-btn" title="${course.name} 삭제">-</button>
                <div class="course-content">
                    <div class="course-title">${course.name}</div>
                    <div class="course-details">${course.instructor}</div>
                </div>
                <button id="course-credits" class="btn btn-sm btn-outline-info" style="font-size:1.1rem">
                    ${course.credits}학점
                </button>
                <button id="course-credits" class="btn btn-sm btn-outline-info" style="font-size:1.1rem">
                    ${course.categoryName}
                </button>
                <button type="button" class="pin-toggle-btn btn btn-outline-danger ${course.isPinned ? 'active': ''}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-pin" viewBox="0 0 16 16">
                        <path d="M4.146.146A.5.5 0 0 1 4.5 0h7a.5.5 0 0 1 .5.5c0 .68-.342 1.174-.646 1.479-.126.125-.25.224-.354.298v4.431l.078.048c.203.127.476.314.751.555C12.36 7.775 13 8.527 13 9.5a.5.5 0 0 1-.5.5h-4v4.5c0 .276-.224 1.5-.5 1.5s-.5-1.224-.5-1.5V10h-4a.5.5 0 0 1-.5-.5c0-.973.64-1.725 1.17-2.189A6 6 0 0 1 5 6.708V2.277a3 3 0 0 1-.354-.298C4.342 1.674 4 1.179 4 .5a.5.5 0 0 1 .146-.354m1.58 1.408-.002-.001zm-.002-.001.002.001A.5.5 0 0 1 6 2v5a.5.5 0 0 1-.276.447h-.002l-.012.007-.054.03a5 5 0 0 0-.827.58c-.318.278-.585.596-.725.936h7.792c-.14-.34-.407-.658-.725-.936a5 5 0 0 0-.881-.61l-.012-.006h-.002A.5.5 0 0 1 10 7V2a.5.5 0 0 1 .295-.458 1.8 1.8 0 0 0 .351-.271c.08-.08.155-.17.214-.271H5.14q.091.15.214.271a1.8 1.8 0 0 0 .37.282"></path>
                    </svg>
                    ${course.isPinned ? '고정됨': '고정'}
                </button>
            `;

            // 압정 버튼에 이벤트 리스너 추가
            itemDiv.querySelector('.pin-toggle-btn').addEventListener('click', () => {
                document.dispatchEvent(new CustomEvent('togglePinCourse', {
                    detail: { courseId: course.id }
                }));
            });

            // 삭제 버튼에 이벤트 리스너 추가
            itemDiv.querySelector('.remove-from-list-btn').addEventListener('click', () => {
                // main.js가 수신할 이벤트를 발생시킴
                document.dispatchEvent(new CustomEvent('removeCourseFromView', {
                    detail: { courseId: course.id }
                }));
            });

            courseListContainer.appendChild(itemDiv);
        });

         updatePinnedCreditsDisplay(timetable);
    });

    // 페이지 로드 시 초기 총 학점 계산
    updateTotalCredits();

});