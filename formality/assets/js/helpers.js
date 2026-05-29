async function checkAuth() {
    const navDashboard = document.getElementById('nav-dashboard');
    const navLogin = document.getElementById('nav-login');

    try {
        const response = await fetch('/api/user/me', {
            method: 'GET',
            credentials: 'include'
        });

        if (response.ok) {
            navDashboard.style.display = 'block';
            navLogin.style.display = 'none';

        } else {
            navDashboard.style.display = 'none';
            navLogin.style.display = 'block';
        }

    } catch (error) {
        console.log('auth error:', error);

        navDashboard.style.display = 'none';
        navLogin.style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});