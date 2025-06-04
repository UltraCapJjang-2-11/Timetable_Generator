document.addEventListener('DOMContentLoaded', () => {
    const courseNameInput = document.getElementById('course_name_search');
    const courseCodeInput = document.getElementById('course_code_search');
    const instructorNameInput = document.getElementById('instructor_name_search');
    const searchButton = document.getElementById('review-search-button');
    const reviewListContainer = document.getElementById('review-list');

    searchButton.addEventListener('click', async () => {
        const courseName = courseNameInput.value.trim();
        const courseCode = courseCodeInput.value.trim();
        const instructorName = instructorNameInput.value.trim();

        const params = new URLSearchParams();
        if (courseName) params.append('course_name', courseName);
        if (courseCode) params.append('course_code', courseCode);
        if (instructorName) params.append('instructor_name', instructorName);

        // 모든 파라미터가 비어있으면 검색하지 않음
        if (Array.from(params).length === 0) {
            reviewListContainer.innerHTML = '<p class="text-danger">검색어를 하나 이상 입력해주세요.</p>';
            return;
        }

        const apiUrl = `/reviews/search/?${params.toString()}`;
        reviewListContainer.innerHTML = '<p class="text-info">검색 중...</p>';

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: '서버 응답 오류' }));
                throw new Error(`HTTP error! status: ${response.status}, Message: ${errorData.detail || '알 수 없는 오류'}`);
            }
            const reviews = await response.json();

            if (reviews.length === 0) {
                reviewListContainer.innerHTML = '<p class="text-muted">검색 결과가 없습니다.</p>';
                return;
            }

            reviewListContainer.innerHTML = ''; // 이전 결과 지우기
            reviews.forEach(review => {
                const reviewItem = document.createElement('a');
                reviewItem.href = `/reviews/${review.summary_id}/`;
                reviewItem.classList.add('list-group-item', 'list-group-item-action');
                
                let content = `<strong>${review.course_name}</strong> (${review.course_code}) - ${review.instructor_name}<br>`;
                content += `<small class="text-muted">평균 평점: ${review.avg_rating} (리뷰 ${review.review_count}개)</small>`;
                
                reviewItem.innerHTML = content;
                reviewListContainer.appendChild(reviewItem);
            });

        } catch (error) {
            console.error('Error fetching reviews:', error);
            reviewListContainer.innerHTML = `<p class="text-danger">리뷰를 가져오는 중 오류가 발생했습니다: ${error.message}</p>`;
        }
    });

    const allUserReviewsModalElement = document.getElementById('allUserReviewsModal');
    let allUserReviewsModalInstance = null;
    if (allUserReviewsModalElement) {
        allUserReviewsModalInstance = new bootstrap.Modal(allUserReviewsModalElement);
    }
    
    const modalBody = document.getElementById('allUserReviewsModalBody');
    // const modalTitle = document.getElementById('allUserReviewsModalLabel'); // 필요시 타이틀 동적 변경

    // '수강생 전체 코멘트 보기' 버튼 이벤트 리스너 설정 함수
    function setupViewAllCommentsButton() {
        const viewAllCommentsBtn = document.getElementById('viewAllCommentsBtn');
        if (viewAllCommentsBtn && allUserReviewsModalInstance) {
            viewAllCommentsBtn.addEventListener('click', function() {
                const summaryId = this.dataset.summaryId;
                if (!summaryId) {
                    if(modalBody) modalBody.innerHTML = '<p class="text-danger">강의 요약 ID를 찾을 수 없습니다.</p>';
                    allUserReviewsModalInstance.show();
                    return;
                }

                if(modalBody) modalBody.innerHTML = '<div class="d-flex justify-content-center align-items-center" style="min-height: 100px;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
                allUserReviewsModalInstance.show();

                // API URL 구성 (프로젝트의 URL 구조에 따라 '/data-manager' prefix가 필요할 수 있음)
                const apiUrl = `/data-manager/reviews/summary/${summaryId}/`; 

                fetch(apiUrl)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(reviews => {
                        if (!modalBody) return;
                        modalBody.innerHTML = ''; // 로딩 메시지 제거
                        if (reviews && reviews.length > 0) {
                            const ul = document.createElement('ul');
                            ul.classList.add('list-group', 'list-group-flush');
                            reviews.forEach(review => {
                                const li = document.createElement('li');
                                li.classList.add('list-group-item');

                                let semesterInfo = '';
                                // UserReviewSerializer가 semester 객체를 어떻게 직렬화하는지에 따라 달라짐
                                // 예: review.semester가 객체이고 name 속성이 있다면 review.semester.name
                                // 예: review.semester_display_name 같은 필드가 있다면 그것 사용
                                if (review.semester_str) { // Serializer에서 semester의 문자열 표현을 제공한다고 가정
                                    semesterInfo = `<small class="text-muted d-block">수강 학기: ${review.semester_str}</small>`;
                                }
                                
                                let ratingInfo = '';
                                if (review.rating !== null && review.rating !== undefined) {
                                    ratingInfo = `<strong>평점: ${parseFloat(review.rating).toFixed(1)}/5.0</strong>`;
                                }


                                li.innerHTML = `
                                    <div class="d-flex flex-column flex-md-row w-100 justify-content-between">
                                        <h6 class="mb-1 me-2">${ratingInfo}</h6>
                                    </div>
                                    <p class="mb-1">${review.comment_text || '(코멘트 없음)'}</p>
                                    ${semesterInfo}
                                `;
                                ul.appendChild(li);
                            });
                            modalBody.appendChild(ul);
                        } else {
                            modalBody.innerHTML = '<p>아직 작성된 코멘트가 없습니다.</p>';
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching user reviews:', error);
                        if (modalBody) modalBody.innerHTML = `<p class="text-danger">코멘트를 불러오는 중 오류가 발생했습니다. <br><small>${error.message}</small></p>`;
                    });
            });
        }
    }

    // 페이지 로드 시 또는 selected_summary가 업데이트될 때 버튼 설정 함수 호출
    setupViewAllCommentsButton();

    // 만약 selected_summary 영역이 AJAX 등으로 동적으로 업데이트되고 
    // viewAllCommentsBtn 버튼이 재생성된다면, 해당 업데이트 콜백 내에서 
    // setupViewAllCommentsButton()를 다시 호출해야 합니다.
    // 현재는 페이지 로드 시 한 번만 설정합니다 (페이지가 summary_id에 따라 리로드되므로).
});
