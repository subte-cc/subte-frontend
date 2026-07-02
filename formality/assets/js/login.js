

const loginTab = document.getElementById('login-tab');
const signupTab = document.getElementById('signup-tab');
const submitBtn = document.getElementById('submit-btn');
const confirmPasswordGp = document.getElementById('confirm-password-gp');
const termsGp = document.getElementById('terms-gp');
const termsCheckbox = document.getElementById('terms-checkbox');
const passwordInput = document.getElementById('password-input');
const confirmPasswordInput = document.getElementById('confirm-password-input');
const inviteCodeGp = document.getElementById('invite-code-gp');
const inviteCodeInput = document.getElementById('invite-code-input');
const signupPrompt = document.getElementById('signup-prompt');
const authForm = document.getElementById('auth-form');

let route = "/api/auth/login";
let inviteRequired = false;

async function loadConfig() {
    try {
        const response = await fetch('/api/auth/config', { credentials: 'include' });
        if (!response.ok) {
            console.error("Auth config request failed with status:", response.status);
            return;
        }
        const config = await response.json();

        inviteRequired = config.invite_required;

        const oauthCodeberg = document.getElementById('oauth-codeberg');
        const oauthGithub = document.getElementById('oauth-github');
        const oauthGoogle = document.getElementById('oauth-google');
        const oauthContainer = document.getElementById('oauth-container');

        if (oauthCodeberg) oauthCodeberg.style.display = config.oauth_codeberg_enabled ? 'inline-block' : 'none';
        if (oauthGithub) oauthGithub.style.display = config.oauth_github_enabled ? 'inline-block' : 'none';
        if (oauthGoogle) oauthGoogle.style.display = config.oauth_google_enabled ? 'inline-block' : 'none';

        if (!config.oauth_codeberg_enabled && !config.oauth_github_enabled && !config.oauth_google_enabled) {
            if (oauthContainer) oauthContainer.style.display = 'none';
        } else {
            if (oauthContainer) oauthContainer.style.display = 'block';
        }

        if (inviteRequired && signupTab.classList.contains('tab-active')) {
            if (inviteCodeGp) inviteCodeGp.style.display = 'block';
            if (inviteCodeInput) inviteCodeInput.required = true;
        }
    } catch (err) {
        console.error("Failed to load auth config", err);
    }
}

loadConfig();

loginTab.addEventListener('click', () => {
    submitBtn.innerText = 'Login';
    loginTab.className = 'tab-active';
    signupTab.className = 'tab-inactive';
    confirmPasswordGp.style.display = 'none';
    confirmPasswordInput.required = false;
    inviteCodeGp.style.display = 'none';
    inviteCodeInput.required = false;
    termsGp.style.display = 'none';
    termsCheckbox.required = false;
    signupPrompt.style.display = 'block';
    route = "/api/auth/login";
});

signupTab.addEventListener('click', () => {
    submitBtn.innerText = 'Create Account';
    signupTab.className = 'tab-active';
    loginTab.className = 'tab-inactive';
    confirmPasswordGp.style.display = 'block';
    confirmPasswordInput.required = true;

    if (inviteRequired) {
        inviteCodeGp.style.display = 'block';
        inviteCodeInput.required = true;
    }

    termsGp.style.display = 'block';
    termsCheckbox.required = true;
    signupPrompt.style.display = 'none';
    route = "/api/auth/register";
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (route === "/api/auth/register") {
        if (passwordInput.value !== confirmPasswordInput.value) {
            UI.error("Passwords do not match!");
            return;
        }
    }

    const formData = new FormData(authForm);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(route, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            if (route === "/api/auth/register") {
                await UI.alert("Account created successfully! Please check your email to verify your account before logging in.", "Success");
                loginTab.click();
            } else {
                window.location.href = '/dashboard';
            }
        } else {
            UI.error('Error: ' + (result.error || result.message || "Unknown error"));
        }
    } catch (error) {
        console.error('Network error:', error);
        UI.error('Unable to connect to the server.');
    }
});

document.getElementById('signup-switch')?.addEventListener('click', () => {
    signupTab.click();
});

document.addEventListener("DOMContentLoaded", () => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('verified') === 'true') {
        UI.alert("Your account has been successfully verified. You can now log in.", "Success");
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

const altchaWidget = document.querySelector('altcha-widget');
if (altchaWidget) {
    altchaWidget.addEventListener('statechange', (ev) => {
        submitBtn.disabled = ev.detail.state !== 'verified';
    });
}
