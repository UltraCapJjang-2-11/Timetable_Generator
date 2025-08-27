// [MODIFIED] 전체 코드를 API 호출 기반으로 재구성합니다.
export function initializeOrgDropdowns() {
    const $college = document.getElementById('college');
    if (!$college || $college.length > 1) return; // 요소가 없거나 이미 초기화되었으면 실행 중단

    const $dept = document.getElementById('dept');
    let departmentsData = []; // 학과 데이터를 저장할 변수

    // 1. API 호출
    fetch('/data-manager/api/org-data/')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            const colleges = data.colleges;
            departmentsData = data.departments; // 학과 데이터 저장

            // 2. 단과대학 드롭다운 채우기
            colleges.forEach(c => {
                const opt = new Option(c.college_name, c.college_name);
                opt.dataset.id = c.college_id;
                $college.add(opt);
            });
        })
        .catch(error => console.error('단과대학/학과 데이터를 불러오는 데 실패했습니다:', error));


    // 3. 이벤트 리스너 설정
    $college.onchange = () => {
        const selected = $college.selectedOptions[0];
        const cid = selected.dataset.id;
        $dept.options.length = 1;

        if (!cid) {
            $dept.disabled = true;
            return;
        }
        $dept.disabled = false;
        departmentsData
            .filter(d => d.college_id == cid)
            .forEach(d => {
                const opt = new Option(d.dept_name, d.dept_name);
                opt.dataset.id = d.dept_id;
                $dept.add(opt);
            });
    };
}

// 공유 컴포넌트에서 필요 시 호출되므로 자동 초기화 제거