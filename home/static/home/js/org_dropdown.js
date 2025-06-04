  document.addEventListener('DOMContentLoaded', () => {
    const colleges    = JSON.parse(document.getElementById('colleges-data').textContent);
    const departments = JSON.parse(document.getElementById('departments-data').textContent);
    const majors      = JSON.parse(document.getElementById('majors-data').textContent);

    const $college = document.getElementById('college');
    const $dept    = document.getElementById('dept');
    //const $major   = document.getElementById('major');

    // 1) 단과대학 채우기 (value=name, data-id=id)
    colleges.forEach(c => {
      const opt = new Option(c.college_name, c.college_name);
      opt.dataset.id = c.college_id;
      $college.add(opt);
    });

    // 2) 대학 선택 시 학과 필터
    $college.onchange = () => {
      const selected = $college.selectedOptions[0];
      const cid = selected.dataset.id;      // 내부 필터링용 id
      $dept.options.length  = 1;
      //$major.options.length = 1;
      //$major.disabled = true;

      if (!cid) {
        $dept.disabled = true;
        return;
      }
      $dept.disabled = false;
      departments
        .filter(d => d.college_id == cid)
        .forEach(d => {
          const opt = new Option(d.dept_name, d.dept_name);
          opt.dataset.id = d.dept_id;
          $dept.add(opt);
        });
    };

    // {#// 3) 학과 선택 시 전공 필터#}
    // {#$dept.onchange = () => {#}
    // {#  const selected = $dept.selectedOptions[0];#}
    // {#  const did = selected.dataset.id;      // 내부 필터링용 id#}
    // {#  $major.options.length = 1;#}
    // {#  if (!did) {#}
    // {#    $major.disabled = true;#}
    // {#    return;#}
    // {#  }#}
    // {#  $major.disabled = false;#}
    // {#  majors#}
    // {#    .filter(m => m.dept_id == did)#}
    // {#    .forEach(m => {#}
    // {#      const opt = new Option(m.major_name, m.major_name);#}
    // {#      opt.dataset.id = m.major_id;#}
    // {#      $major.add(opt);#}
    // {#    });#}
  });