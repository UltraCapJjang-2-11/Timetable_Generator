// home/js/org_dropdown.js

let $elements;

// 외부에서 사용할 수 있도록 DOM 요소를 반환하는 함수
export function getOrgDOMElements() {
    return $elements;
}


document.addEventListener('DOMContentLoaded', () => {
  // DOM이 준비된 후 요소를 찾아 할당합니다.
  $elements = {
      orgCollege: document.getElementById('college'),
      orgDept: document.getElementById('dept'),
  };

  const colleges    = JSON.parse(document.getElementById('colleges-data').textContent);
  const departments = JSON.parse(document.getElementById('departments-data').textContent);

  const { orgCollege: $college, orgDept: $dept } = $elements;

  // 1) 단과대학 채우기
  colleges.forEach(c => {
    const opt = new Option(c.college_name, c.college_name);
    opt.dataset.id = c.college_id;
    $college.add(opt);
  });

  // 2) 대학 선택 시 학과 필터
  $college.onchange = () => {
    const selected = $college.selectedOptions[0];
    const cid = selected ? selected.dataset.id : null;
    $dept.options.length  = 1;
    $dept.disabled = true;

    if (!cid) return;

    $dept.disabled = false;
    departments
      .filter(d => d.college_id == cid)
      .forEach(d => {
        const opt = new Option(d.dept_name, d.dept_name);
        opt.dataset.id = d.dept_id;
        $dept.add(opt);
      });
  };
});