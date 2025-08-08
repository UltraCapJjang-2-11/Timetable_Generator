// Parse JSON data injected by template
(function initGlobals() {
  try {
    window.timetablesData = JSON.parse(document.getElementById('timetables-json').textContent);
  } catch (e) {
    window.timetablesData = [];
  }
  try {
    window.currentUser = JSON.parse(document.getElementById('current-user-json').textContent);
  } catch (e) {
    window.currentUser = { user_id: 0, username: '익명', is_authenticated: false };
  }
})();

// Optional: simple log
document.addEventListener('DOMContentLoaded', function () {
  if (Array.isArray(window.timetablesData)) {
    // console.log('Loaded timetables:', window.timetablesData.length);
  }
});

// Expose functions used by template and manage.js
window.showTimetableById = function showTimetableById(id) {
  console.log('showTimetableById called with ID:', id);
  const timetableData = (window.timetablesData || []).find(t => Number(t.id) === Number(id));
  if (!timetableData) {
    console.error('Timetable data not found for ID:', id);
    return;
  }

  console.log('Found timetable data:', timetableData.title);
  // sync dropdown to also trigger chat opening
  const sel = document.getElementById('saved-timetable-select');
  if (sel) {
    console.log('Syncing dropdown to value:', String(id));
    sel.value = String(id);
    // Trigger change event to open chats
    const event = new Event('change', { bubbles: true });
    sel.dispatchEvent(event);
  } else {
    console.error('Dropdown select element not found!');
  }

  window.showTimetable(timetableData);
};

window.showTimetable = function showTimetable(timetableData) {
  const overlay = document.getElementById('timetable-overlay');
  const timetableTitle = document.getElementById('timetable-title');
  const timetableBody = document.querySelector('.timetable tbody');

  window.currentTimetable = timetableData;
  window.currentTimetableId = timetableData.id;

  timetableTitle.textContent = timetableData.title;
  timetableBody.innerHTML = '';

  for (let hour = 9; hour <= 20; hour++) {
    const row = document.createElement('tr');
    const timeCell = document.createElement('td');
    timeCell.textContent = `${hour}:00`;
    row.appendChild(timeCell);

    for (let i = 0; i < 5; i++) {
      const cell = document.createElement('td');
      cell.classList.add('timetable-cell');
      cell.setAttribute('data-hour', hour);
      cell.setAttribute('data-day', i);
      row.appendChild(cell);
    }

    timetableBody.appendChild(row);
  }

  const dayMapping = { '월': 0, '화': 1, '수': 2, '목': 3, '금': 4 };
  const colors = ['#FFE5E5', '#E5F3FF', '#E5FFE5', '#FFF5E5', '#F5E5FF', '#FFE5F5'];
  let colorIndex = 0;

  (timetableData.courses || []).forEach(course => {
    const courseColor = colors[colorIndex % colors.length];
    colorIndex++;

    (course.schedules || []).forEach(schedule => {
      const dayIndex = dayMapping[schedule.day];
      if (dayIndex === undefined) return;

      const timeSlots = String(schedule.times || '')
        .split(',')
        .map(t => parseInt(t.trim(), 10) + 8)
        .filter(n => !Number.isNaN(n));

      timeSlots.forEach(hour => {
        const cell = document.querySelector(
          `.timetable-cell[data-hour="${hour}"][data-day="${dayIndex}"]`
        );
        if (cell) {
          cell.style.backgroundColor = courseColor;
          cell.innerHTML = (
            '<div style="font-size: 12px; padding: 2px;">' +
            `<strong>${course.course_name}</strong><br>` +
            `<small>${(schedule.location || '')}</small>` +
            '</div>'
          );
        }
      });
    });
  });

  overlay.classList.remove('hidden');
  overlay.style.display = 'flex';
};

window.hideTimetable = function hideTimetable() {
  const overlay = document.getElementById('timetable-overlay');
  overlay.classList.add('hidden');
  overlay.style.display = 'none';
};

window.editTimetable = function editTimetable() {
  window.location.href = '/timetable/';
};

window.deleteTimetable = async function deleteTimetable() {
  if (!window.currentTimetable) return;
  const ok = confirm(`"${window.currentTimetable.title}"을(를) 삭제하시겠습니까?`);
  if (!ok) return;
  try {
    const response = await fetch(`/delete_timetable/${window.currentTimetableId}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    if (response.ok) {
      alert('시간표가 삭제되었습니다.');
      location.reload();
    } else {
      alert('시간표 삭제에 실패했습니다.');
    }
  } catch (e) {
    console.error('삭제 오류:', e);
    alert('시간표 삭제 중 오류가 발생했습니다.');
  }
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
} 