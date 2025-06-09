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
                    <div class="course-details">${course.instructor} / ${course.credits}학점 / ${course.categoryName}</div>
                </div>
                <input id="inpLock-${course.id}" type="checkbox" class="pin-toggle-checkbox" ${course.isPinned ? 'checked' : ''}>
                <label class="btn-lock" for="inpLock-${course.id}">
                    <svg width="36" height="40" viewBox="0 0 36 40">
                        <path class="lockb" d="M27 27C27 34.1797 21.1797 40 14 40C6.8203 40 1 34.1797 1 27C1 19.8203 6.8203 14 14 14C21.1797 14 27 19.8203 27 27ZM15.6298 26.5191C16.4544 25.9845 17 25.056 17 24C17 22.3431 15.6569 21 14 21C12.3431 21 11 22.3431 11 24C11 25.056 11.5456 25.9845 12.3702 26.5191L11 32H17L15.6298 26.5191Z"></path>
                        <path class="lock" d="M6 21V10C6 5.58172 9.58172 2 14 2V2C18.4183 2 22 5.58172 22 10V21"></path>
                        <path class="bling" d="M29 20L31 22"></path>
                        <path class="bling" d="M31.5 15H34.5"></path>
                        <path class="bling" d="M29 10L31 8"></path>
                    </svg>
                </label>
            `;

            // 자물쇠 토글에 이벤트 리스너 추가
            itemDiv.querySelector('.pin-toggle-checkbox').addEventListener('change', () => {
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