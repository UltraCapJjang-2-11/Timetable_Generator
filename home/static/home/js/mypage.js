document.addEventListener('DOMContentLoaded', function () {
  // ------- Utilities -------
  function parseJsonFromScript(id, fallback) {
    try {
      const el = document.getElementById(id);
      if (!el) return fallback;
      const txt = (el.textContent || '').trim();
      if (!txt) return fallback;
      return JSON.parse(txt);
    } catch (e) {
      return fallback;
    }
  }

  const gradeToPoint = {
    'A+': 4.5, 'A0': 4.0,
    'B+': 3.5, 'B0': 3.0,
    'C+': 2.5, 'C0': 2.0,
    'D+': 1.5, 'D0': 1.0,
    'F': 0.0,
  };

  function calculateGpa(courses) {
    if (!Array.isArray(courses) || courses.length === 0) return '0.00';
    let totalPoints = 0;
    let totalCredits = 0;
    for (const c of courses) {
      const pt = gradeToPoint[c?.grade];
      const cr = Number(c?.credit);
      if (pt !== undefined && !Number.isNaN(cr) && cr > 0) {
        totalPoints += pt * cr;
        totalCredits += cr;
      }
    }
    if (totalCredits === 0) return '0.00';
    return (totalPoints / totalCredits).toFixed(2);
  }

  function termOrder(term) {
    if (term === '1학기') return 1;
    if (term === '여름') return 2;
    if (term === '2학기') return 3;
    if (term === '겨울') return 4;
    return 9;
  }

  function groupBySemester(courses) {
    const map = new Map();
    courses.forEach(c => {
      const y = c?.year ?? 0;
      const t = c?.term || '';
      const key = `${y}년 ${t}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(c);
    });
    return map;
  }

  // ------- Data -------
  const courseHistory = parseJsonFromScript('course-history-data', []);
  const requirementsTree = parseJsonFromScript('requirements-tree-data', []);

  const semesterListEl = document.getElementById('mypage-semester-list');
  const courseListEl = document.getElementById('mypage-course-list');
  const semesterTitleEl = document.getElementById('mypage-semester-title');
  const semesterCreditsEl = document.getElementById('mypage-semester-credits');
  const semesterGpaEl = document.getElementById('mypage-semester-gpa');
  const totalCreditsEl = document.getElementById('mypage-total-credits');
  const totalGpaEl = document.getElementById('mypage-total-gpa');

  const bySemester = groupBySemester(courseHistory);
  const semesterKeys = Array.from(bySemester.keys()).sort((a, b) => {
    const [ay, at] = a.split('년 ').map((v, i) => (i === 0 ? parseInt(v, 10) || 0 : v));
    const [by, bt] = b.split('년 ').map((v, i) => (i === 0 ? parseInt(v, 10) || 0 : v));
    if (ay !== by) return ay - by;
    return termOrder(at) - termOrder(bt);
  });

  // ✅ 학점별 색상 클래스 지정
  function getGradeClass(grade) {
    if (!grade) return '';
    const g = grade.toUpperCase();
    if (g === 'A+' || g === 'A0') return 'grade-badge grade-Aplus';
    if (g === 'B+' || g === 'B0') return 'grade-badge grade-Bplus';
    if (g === 'C+' || g === 'C0') return 'grade-badge grade-Cplus';
    if (g === 'D+' || g === 'D0') return 'grade-badge grade-Dplus';
    if (g === 'F') return 'grade-badge grade-F';
    if (g === 'P') return 'grade-badge grade-P';
    return 'grade-badge';
  }

  // ------- Course history UI -------
  function renderCourseListFor(semesterKey) {
    const list = bySemester.get(semesterKey) || [];
    const semCredits = list.reduce((sum, c) => sum + (Number(c.credit) || 0), 0);
    semesterTitleEl.textContent = semesterKey;
    semesterCreditsEl.textContent = semCredits;
    semesterGpaEl.textContent = calculateGpa(list);
    courseListEl.innerHTML = '';
    list.forEach(course => {
      const html = `
        <div class="card mb-2">
          <div class="card-body p-2">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <h6 class="mb-0">${course.course_name}</h6>
                <small class="text-muted">${course.course_code} | ${course.credit}학점</small>
              </div>
              <span class="${getGradeClass(course.grade)}">${course.grade || ''}</span>
            </div>
          </div>
        </div>`;
      courseListEl.insertAdjacentHTML('beforeend', html);
    });
  }

  function renderSemesterList() {
    if (!semesterListEl) return;
    semesterListEl.innerHTML = '';
    semesterKeys.forEach(key => {
      const li = document.createElement('li');
      li.className = 'list-group-item list-group-item-action';
      li.textContent = key;
      li.dataset.semester = key;
      li.addEventListener('click', () => {
        document.querySelectorAll('#mypage-semester-list .list-group-item').forEach(el => el.classList.remove('active'));
        li.classList.add('active');
        renderCourseListFor(key);
      });
      semesterListEl.appendChild(li);
    });
    if (semesterKeys.length > 0) {
      const last = semesterListEl.lastElementChild;
      if (last) last.click();
    }
  }

  const totalCredits = courseHistory.reduce((sum, c) => sum + (Number(c.credit) || 0), 0);
  totalCreditsEl && (totalCreditsEl.textContent = totalCredits);
  totalGpaEl && (totalGpaEl.textContent = calculateGpa(courseHistory));
  renderSemesterList();

  // ------- Requirements table -------
  const reqBody = document.getElementById('requirements-table-body');
  function renderNodeRow(node) {
    const level = node.level || 0;
    const indent = 10 + level * 12; // ✅ 계층별 들여쓰기 계산

    // ✅ 구분 열에 직접 들여쓰기 반영
    const nameCell = `
      <td style="text-align:left; padding-left:${indent}px;">
        ${node.name}
      </td>`;
    const earnedCell = `<td>${(node.earned ?? 0)}</td>`;
    const reqCell = `<td>${node.required != null ? node.required : '-'}</td>`;
    const remain = node.required != null ? Math.max(node.required - (Number(node.earned) || 0), 0) : '-';
    const shortCell = `<td>${remain}</td>`;

    let statusBadge = '-';
    if (node.required != null) {
      const satisfied = (Number(node.earned) || 0) >= Number(node.required);
      statusBadge = satisfied
        ? '<span class="badge bg-success">충족</span>'
        : '<span class="badge bg-warning text-dark">부족</span>';
    }
    const statusCell = `<td class="text-center">${statusBadge}</td>`;

    const tr = document.createElement('tr');
    tr.classList.add(`requirement-level-${level}`);
    tr.innerHTML = `${nameCell}${earnedCell}${reqCell}${shortCell}${statusCell}`;
    reqBody.appendChild(tr);
  }

  function renderRequirements(tree) {
    if (!reqBody) return;
    reqBody.innerHTML = '';
    const dfs = (n) => {
      renderNodeRow(n);
      if (Array.isArray(n.children)) n.children.forEach(child => dfs(child));
    };
    (tree || []).forEach(root => dfs(root));
  }

  renderRequirements(requirementsTree);

  // ========================================
  // ✅ 상단 GPA 차트 (topGpaChart)
  // ========================================
  const topCtx = document.getElementById('topGpaChart')?.getContext('2d');
  if (topCtx && semesterKeys.length > 0) {
    const labels = semesterKeys;
    const data = labels.map(key => {
      const list = bySemester.get(key) || [];
      return Number(calculateGpa(list));
    });

    new Chart(topCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '학기별 GPA',
          data,
          borderColor: '#ecc74eff',
          backgroundColor: 'rgba(232, 235, 105, 0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 4.5, ticks: { stepSize: 0.5 } }
        }
      }
    });
  }

  console.log('✅ MyPage 로드 완료 - 상단 GPA 차트 + 학점 색상 + 계층 들여쓰기 적용 완료');
});
