const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

registerBtn.addEventListener('click', () => {
    const url = registerBtn.getAttribute('data-onboarding-url') || '/onboarding/';
    window.location.href = url;
});

loginBtn.addEventListener('click', () => {
    if (container.classList.contains('active')) {
        container.classList.remove('active');
    }
});