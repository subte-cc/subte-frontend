function getCookie(name) {
    const match = document.cookie.match('(?:^|; )' + name.replace(/([.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)');
    return match ? decodeURIComponent(match[1]) : null;
}

function isAuthenticated() {
    const exp = parseInt(getCookie('auth_status'), 10);
    if (!Number.isFinite(exp)) return false;
    return Math.floor(Date.now() / 1000) < exp;
}

function checkAuth() {
    const navDashboard = document.getElementById('nav-dashboard');
    const navLogin = document.getElementById('nav-login');
    if (!navDashboard || !navLogin) return;

    const authed = isAuthenticated();
    navDashboard.style.display = authed ? 'block' : 'none';
    navLogin.style.display = authed ? 'none' : 'block';
}

document.addEventListener('DOMContentLoaded', checkAuth);
