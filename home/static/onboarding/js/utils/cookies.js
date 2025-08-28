/**
 * 지정한 이름의 쿠키 값을 반환합니다.
 * @param {string} name - 조회할 쿠키 이름
 * @returns {string|null} - 존재하면 쿠키 값, 없으면 null
 */
export function getCookie(name) {
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


