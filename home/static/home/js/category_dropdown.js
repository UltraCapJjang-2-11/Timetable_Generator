document.addEventListener('DOMContentLoaded', ()=>{

  /* ---------- ① 드롭다운 채우기 ---------- */
  const cats = JSON.parse(
      document.getElementById('categories-data').textContent);

  const $root  = document.getElementById('category_root');
  const $child = document.getElementById('category_child');
  const $grand = document.getElementById('category_grandchild');
  const $childBox  = document.getElementById('child-container');
  const $grandBox  = document.getElementById('grandchild-container');
  const $labChild  = document.getElementById('label_child');
  const $labGrand  = document.getElementById('label_grandchild');

  const $orgContainer = document.getElementById('org-container');
  const $orgCollege   = document.getElementById('college');   // org_dropdowns 안 select
  const $orgDept      = document.getElementById('dept');
  const $courseNameSearch = document.getElementById('course_name_search'); // 강의명 검색 필드 참조 복원


  /* ---------- 대분류 채우기 ---------- */
  cats.filter(c=>c.parent_category_id===null)
      .forEach(c=>$root.add(new Option(c.category_name, c.category_id)));

  /* ---------- 대분류 변경 ---------- */
  $root.onchange = ()=> {
    // 공통 초기화
    resetSelect($child); resetSelect($grand);
    $childBox.style.display = $grandBox.style.display = 'none';
    if ($courseNameSearch) $courseNameSearch.value = ''; // 대분류 변경 시 강의명 검색 초기화 복원

    // --- org dropdown 초기화 & 숨김 ---
    hideOrg();

    if(!$root.value) return;

    const rootText = $root.selectedOptions[0].textContent;

    // 중분류 표시
    $childBox.style.display = '';
    $child.disabled = false;
    cats.filter(c=>c.parent_category_id == $root.value)
        .forEach(c=>$child.add(new Option(c.category_name, c.category_id)));

    if(rootText === '전공'){
      /* ① org 드롭다운 표시 */
      $orgContainer.style.display = '';
      /* 필요 시 초기화만 수행하고(값 ''), $orgDept.disabled = true 는
         org_dropdowns 내부 JS 가 이미 처리하므로 생략 가능 */
    }else if(rootText === '교양'){
      /* 교양: 소분류까지 */
      $grandBox.style.display = '';
    }
  };

  $child.onchange = ()=>{
    resetSelect($grand); $grandBox.style.display='none';
    if($root.selectedOptions[0].text!=='교양') return;
    if(!$child.value) return;

    $grandBox.style.display=''; $grand.disabled=false;
    cats.filter(c=>c.parent_category_id===$child.value*1)
        .forEach(c=>$grand.add(new Option(c.category_name, c.category_id)));
  };

  function reset(sel){ sel.options.length=1; sel.disabled=true; } // 이 함수는 resetSelect와 중복될 수 있으니 확인 필요

  /* ---------- ② 검색 ---------- */
  document.getElementById('search-button').addEventListener('click',()=>{
      const cid = $grand.value || $child.value || $root.value;
      const courseName = $courseNameSearch ? $courseNameSearch.value.trim() : ''; // 강의명 가져오기 복원

      // 카테고리도 없고 강의명도 없으면 검색하지 않음 (조건 복원)
      if (!cid && !courseName) { 
          alert('교과목 분류를 선택하거나 강의명을 입력하세요.'); 
          return; 
      }

      /* 2) 선택된 단과대학·학과 이름 읽기 ── NEW ── */
      const collegeName = document.getElementById('college')?.value.trim();
      const deptName    = document.getElementById('dept')?.value.trim();

      /* 3) GET 파라미터 구성 (강의명 파라미터 추가 복원) */
      const params = new URLSearchParams();
      if (cid) params.append('category_id', cid);
      if (courseName) params.append('course_name', courseName);
      if (collegeName) params.append('college_name', collegeName);   // ← 단과대
      if (deptName)    params.append('dept_name',    deptName);      // ← 학과

      const url = `/course/search/?` + params.toString();
    const tbody = document.getElementById('course-list-body');
    tbody.innerHTML =
      '<tr><td colspan="4" class="text-center py-3">검색 중…</td></tr>';

    fetch(url).then(res=>{
      if(!res.ok) throw new Error(res.status);
      return res.json();
    }).then(data=>{
      if(typeof displaySearchResults==='function'){
        displaySearchResults(data);        // timetable_script.js 재사용
      }else{
        render(data);                       // fallback
      }
    }).catch(err=>{
      tbody.innerHTML =
        `<tr><td colspan="4" class="text-danger text-center py-3">오류: ${err}</td></tr>`;
    });
  });

function displaySearchResults(courses){
  const body = document.getElementById('course-list-body');
  body.innerHTML = '';

  if(!courses.length){
    body.innerHTML =
      '<tr><td colspan="4" class="text-center py-3">검색 결과가 없습니다.</td></tr>';
    return;
  }

  courses.forEach(c=>{
    /* ───── 셀 내용 생성 ───── */
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';           // 클릭 가능 표시
    tr.classList.add('search-row', 'course-block');
    tr.dataset.courseId = c.course_id;     // 중복 방지를 위해 id 저장

    /* 강의명 */
    const tdName = document.createElement('td');
    tdName.classList.add('fw-bold');
    tdName.textContent = c.course_name;

    /* 교수명 */
    const tdInstructor = document.createElement('td');
    tdInstructor.textContent = c.instructor_name || '-'; // 교수 정보가 없을 경우 '-' 표시

    /* 시간표 표시용 문자열 */
    const tdSched = document.createElement('td');
    const schedArr = (c.schedules||[])
        .map(s => `${s.day} ${s.times}`);     // 예: "월 03,04"
    tdSched.innerHTML = schedArr.join('<br>');

    /* 학점 */
    const tdCred = document.createElement('td');
    tdCred.classList.add('text-center');
    tdCred.textContent = c.credits;

    [tdName, tdInstructor, tdSched, tdCred].forEach(td=>tr.appendChild(td));
    body.appendChild(tr);

    // 행 클릭 시 팝업 표시
    tr.addEventListener('click', () => {
      fetch(`/data-manager/course/${c.course_id}/summary/`)
          .then(res => { if (!res.ok) throw new Error(res.status); return res.json(); })
          .then(summ => { showCoursePopup({ ...c, ...summ }); // 수정: 팝업 호출 시 course_id도 전달
          }).catch(err => alert('강의 요약을 불러오지 못했습니다: ' + err));
    });
  });
}

function showCoursePopup(data){
    const modalElement = document.getElementById('course-popup');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

    document.getElementById('popup-title').textContent   = data.course_name;
    document.getElementById('popup-code').textContent    = data.course_code;
    document.getElementById('popup-section').textContent = data.section;
    document.getElementById('popup-year').textContent    = data.target_year;
    document.getElementById('popup-credits').textContent = data.credits;
    document.getElementById('popup-instructor').textContent = data.instructor_name;
    document.getElementById('popup-group').textContent   =  data.group_activity === 'Y' ? '있음' : '없음';

   // schedules 표시 (팝업용)
    const schedStrPopup = (data.schedules || [])
        .map(s => `${s.day} ${s.times} (${s.location || '-'})`)
        .join('<br>');
    document.getElementById('popup-schedules').innerHTML = schedStrPopup;

    document.getElementById('popup-summary').textContent = data.course_summary || '(요약 정보 없음)';


        // --- 시간표에 추가 버튼 로직 ---
    const addTimetableButtonContainer = modalElement.querySelector('.modal-footer');
    let addTimetableButton = document.getElementById('add-to-timetable-btn-popup');

    if (!addTimetableButton) {
        addTimetableButton = document.createElement('button');
        addTimetableButton.id = 'add-to-timetable-btn-popup';
        addTimetableButton.classList.add('btn', 'btn-primary', 'ms-2'); // 간격 추가
        // "닫기" 버튼 앞에 추가
        const closeButton = addTimetableButtonContainer.querySelector('button[data-bs-dismiss="modal"]');
        if (closeButton) {
            addTimetableButtonContainer.insertBefore(addTimetableButton, closeButton);
        } else {
            addTimetableButtonContainer.appendChild(addTimetableButton);
        }
    }
    // 버튼 텍스트 및 상태 초기화 (중요)
    addTimetableButton.textContent = '시간표에 추가';
    addTimetableButton.disabled = false;

    // 기존 이벤트 리스너 제거 (중복 방지)
    const newAddTimetableButton = addTimetableButton.cloneNode(true);
    addTimetableButton.parentNode.replaceChild(newAddTimetableButton, addTimetableButton);
    addTimetableButton = newAddTimetableButton; // 참조 업데이트

    addTimetableButton.onclick = function() {
        // addCourse 함수에 필요한 형태로 데이터를 구성
        const courseDataForTimetable = {
            course_id: String(data.course_id), // 문자열로 통일 (addCourse와 일치)
            course_name: data.course_name,
            credits: data.credits, // addCourse에서 직접 사용하진 않지만, 필요할 수 있음
            // schedules를 객체 배열 그대로 전달
            schedules: data.schedules || [], // schedules가 null일 경우 빈 배열 전달
            // 추가적으로 필요한 정보가 있다면 여기에 포함
            // instructor_name: data.instructor_name,
            // target_year: data.target_year,
        };

        // 'addCourseToTimetable' 커스텀 이벤트 발생
        const addEvent = new CustomEvent('addCourseToTimetable', {
            detail: courseDataForTimetable
        });
        document.dispatchEvent(addEvent);

        // 버튼 상태 변경 (예: "추가됨"으로 표시 후 비활성화)
        this.textContent = '추가됨';
        this.disabled = true;

        // 팝업을 바로 닫지 않고, 사용자가 확인 후 닫도록 둘 수도 있습니다.
        // 또는 modal.hide(); 로 즉시 닫기
    };

    // '강의 평가 보기' 버튼 처리
    const viewReviewsButton = document.getElementById('view-reviews-button');
    // 기존 이벤트 리스너가 있다면 제거 (팝업이 재사용될 경우 중복 방지)
    const newViewReviewsButton = viewReviewsButton.cloneNode(true);
    viewReviewsButton.parentNode.replaceChild(newViewReviewsButton, viewReviewsButton);

    newViewReviewsButton.addEventListener('click', () => {
      const courseCode = data.course_code;
      const instructorName = data.instructor_name;
      if (courseCode && instructorName) {
        const params = new URLSearchParams();
        params.append('course_code', courseCode);
        params.append('instructor_name', instructorName);
        window.location.href = `/reviews/?${params.toString()}`;
      } else {
        alert('강의 코드 또는 교수자 정보가 없어 강의 평가를 볼 수 없습니다.');
      }
    });



    modal.show();
}

 function resetSelect(sel){ sel.options.length = 1; sel.disabled = true; }

  /* org 드롭다운 숨길 때 선택값/활성화 초기화 */
  function hideOrg(){
    $orgContainer.style.display = 'none';
    if($orgCollege){ $orgCollege.value = ''; }
    if($orgDept){
      $orgDept.value = '';
      $orgDept.disabled = true;
    }
    if ($courseNameSearch) $courseNameSearch.value = ''; // hideOrg 시 강의명 검색 초기화 복원
  }

});