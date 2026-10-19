/* Login page behaviour: submitting the login form sends the user to the home page. */
function toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('collapsed');
    }
    
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', (event) => {
        event.preventDefault();
        window.location.href = '/';
    });
});
