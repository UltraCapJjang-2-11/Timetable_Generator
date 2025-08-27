// home/static/home/js/mypage.js

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
    'A+': 4.5,
    'A0': 4.0,
    'B+': 3.5,
    'B0': 3.0,
    'C+': 2.5,
    'C0': 2.0,
    'D+': 1.5,
    'D0': 1.0,
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
  const pageMeta = parseJsonFromScript('page-meta', { total_requirement: 0 });

  // ------- Course history UI -------
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
              <span class="badge bg-primary rounded-pill">${course.grade || ''}</span>
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
      // activate the latest semester by default
      const last = semesterListEl.lastElementChild;
      if (last) last.click();
    }
  }

  const totalCredits = courseHistory.reduce((sum, c) => sum + (Number(c.credit) || 0), 0);
  totalCreditsEl && (totalCreditsEl.textContent = totalCredits);
  totalGpaEl && (totalGpaEl.textContent = calculateGpa(courseHistory));
  renderSemesterList();

  // ------- Requirements table (hierarchical) -------
  const reqBody = document.getElementById('requirements-table-body');

  function renderNodeRow(node) {
    const nameCell = `<td style="text-align:left; padding-left:${(node.level || 0) * 16}px;">${node.name}</td>`;
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
    tr.innerHTML = `${nameCell}${earnedCell}${reqCell}${shortCell}${statusCell}`;
    reqBody.appendChild(tr);
  }

  function renderRequirements(tree) {
    if (!reqBody) return;
    reqBody.innerHTML = '';
    const dfs = (n) => {
      renderNodeRow(n);
      if (Array.isArray(n.children)) {
        n.children.forEach(child => dfs(child));
      }
    };
    (tree || []).forEach(root => dfs(root));
  }

  renderRequirements(requirementsTree);

  // ------- Charts -------
  const gpaCtx = document.getElementById('semesterGpaChart')?.getContext('2d');;

  if (gpaCtx) {
    // Build semester GPA series
    const labels = semesterKeys;
    const data = labels.map(key => {
      const list = bySemester.get(key) || [];
      return Number(calculateGpa(list));
    });
    // Dynamically scale Y-axis to highlight changes
    function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
    const finiteVals = data.filter(v => Number.isFinite(v));
    let yMin = 0, yMax = 4.5;
    if (finiteVals.length > 0) {
      const dMin = Math.min(...finiteVals);
      const dMax = Math.max(...finiteVals);
      if (dMin === dMax) {
        const pad = 0.3; // small pad if flat
        yMin = clamp(dMin - pad, 0, 4.5);
        yMax = clamp(dMax + pad, 0.5, 4.5);
      } else {
        const pad = Math.max(0.15, (dMax - dMin) * 0.2);
        yMin = clamp(dMin - pad, 0, 4.5);
        yMax = clamp(dMax + pad, 0.5, 4.5);
        const span = yMax - yMin;
        if (span < 1.0) {
          const extra = (1.0 - span) / 2;
          yMin = clamp(yMin - extra, 0, 4.5);
          yMax = clamp(yMax + extra, 0.5, 4.5);
        }
      }
    }
    const stepSize = (yMax - yMin) <= 1 ? 0.25 : 0.5;
    new Chart(gpaCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '학기별 GPA',
          data,
          borderColor: '#4e79a7',
          backgroundColor: 'rgba(78, 121, 167, 0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            min: yMin,
            max: yMax,
            ticks: { stepSize }
          }
        },
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  }

  console.log('MyPage 로드 완료 - 이수내역/요건/차트 렌더링 완료');
});
