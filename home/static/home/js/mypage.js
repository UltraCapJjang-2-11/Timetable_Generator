// home/static/home/js/mypage.js

document.addEventListener('DOMContentLoaded', function() {
  // chart-container의 data-* 속성에서 학점 정보를 가져옴
  const container = document.querySelector('.chart-container');
  if (!container) return;

  const major = parseInt(container.dataset.major || '0', 10);
  const general = parseInt(container.dataset.general || '0', 10);
  const free = parseInt(container.dataset.free || '0', 10);

  // Chart.js 데이터 구성
  const chartData = {
    labels: ["교양", "전공", "일반선택"],
    datasets: [{
      label: "이수 학점",
      data: [general, major, free],
      backgroundColor: ["#f28b82", "#aecbfa", "#ccff90"]
    }]
  };

  // 차트 렌더링
  const ctx = document.getElementById("graduationChart").getContext("2d");
  new Chart(ctx, {
    type: "pie",
    data: chartData,
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom"
        }
      }
    }
  });

  // 알림 데이터 처리 (필요시 추가 기능 구현)
  console.log('MyPage 로드 완료 - 알림 시스템 활성화');
});
