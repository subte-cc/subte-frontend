

function esc(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = '/api/domains';

    async function fetchDomains(retryCount = 0) {
        try {
            const res = await fetch(API_BASE, { credentials: 'include' });
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            if (!res.ok) {
                throw new Error(`HTTP Error: ${res.status}`);
            }
            const data = await res.json();
            const domains = Array.isArray(data) ? data : [];
            renderDomains(domains);
        } catch (e) {
            if (retryCount < 2) {
                setTimeout(() => fetchDomains(retryCount + 1), 500);
            } else {
                UI.error("Failed to load domains.");
            }
        }
    }

    function timeSince(dateString) {
        if (!dateString) return "never";
        const date = new Date(dateString);
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " years ago";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " months ago";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " days ago";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " hours ago";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " minutes ago";
        return Math.floor(seconds) + " seconds ago";
    }

    function renderDomains(domains) {
        const tbody = document.getElementById('domains-body');
        tbody.innerHTML = '';

        const count = domains ? domains.length : 0;
        document.getElementById('domain-count').innerText = `${count}/5`;

        const addBtn = document.getElementById('add-domain-btn');
        const addInput = document.getElementById('new-domain-input');
        if (count >= 5) {
            addBtn.disabled = true;
            addBtn.style.backgroundColor = '#999';
            addBtn.style.cursor = 'not-allowed';
            addInput.disabled = true;
            addInput.placeholder = 'limit reached';
        } else {
            addBtn.disabled = false;
            addBtn.style.backgroundColor = '';
            addBtn.style.cursor = 'pointer';
            addInput.disabled = false;
            addInput.placeholder = 'sub domain';
        }

        if (!domains) return;

        domains.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${esc(d.subdomain)}</td>
                <td>
                    <div class="ip-row">
                        <input type="text" class="ip-input" id="ip-${esc(d.id)}" value="${esc(d.ip || '0.0.0.0')}">
                        <button class="update-btn" data-id="${esc(d.id)}">update ip</button>
                    </div>
                </td>
                <td>${esc(timeSince(d.updated_at || d.created_at))}</td>
                <td>
                    <button class="delete-btn" data-id="${esc(d.id)}">delete domain</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.update-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                const newIP = document.getElementById(`ip-${id}`).value;
                await updateDomain(id, newIP);
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                if (await UI.confirm("Are you sure you want to delete this domain?")) {
                    await deleteDomain(id);
                }
            });
        });
    }

    async function fetchUserSummary() {
        try {
            const res = await fetch('/api/user/me', { credentials: 'include' });
            if (!res.ok) return;
            const data = await res.json();

            document.getElementById('info-account').innerText = data.email || 'Unknown';
            document.getElementById('info-created').innerText = new Date(data.created_at).toLocaleString();

            if (data.token_generated_at) {
                document.getElementById('info-token-gen').innerText = timeSince(data.token_generated_at);
                document.getElementById('generate-token-btn').innerText = 'Refresh Token';
            } else {
                document.getElementById('info-token-gen').innerText = 'No API Token generated';
                document.getElementById('generate-token-btn').innerText = 'Generate Token';
            }
        } catch (e) {
        }
    }

    document.getElementById('generate-token-btn').addEventListener('click', async () => {
        const hasToken = document.getElementById('info-token-gen').innerText !== 'No API Token generated';

        if (hasToken) {
            const confirmed = await UI.confirm(
                "Are you sure you want to refresh your api key? Clicking continue will cause previous api key to stop working",
                "Refresh API Key",
                "Continue"
            );
            if (!confirmed) return;
        }

        try {
            const res = await fetch('/api/user/key', {
                method: 'POST',
                credentials: 'include'
            });
            if (!res.ok) throw new Error("Failed to generate token");
            const data = await res.json();

            document.getElementById('token-display').innerText = data.token;
            document.getElementById('generate-token-btn').style.display = 'none';
            await UI.alert("This is your API Token. It is only shown once, save it securely now.", "API Token");
            fetchUserSummary();
        } catch (e) {
            UI.error(e.message);
        }
    });

    async function addDomain() {
        const sub = document.getElementById('new-domain-input').value.trim().toLowerCase();
        if (!sub) return;

        try {
            const res = await fetch(API_BASE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ subdomain: sub, ip: '0.0.0.0' })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed");
            document.getElementById('new-domain-input').value = '';
            fetchDomains();
            UI.success("Domain added successfully!");
        } catch (e) {
            UI.error(e.message);
        }
    }

    async function updateDomain(id, ip) {
        try {
            const res = await fetch(`${API_BASE}/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ ip: ip })
            });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || "Failed to update");
            }
            fetchDomains();
            UI.success("IP updated successfully!");
        } catch (e) {
            UI.error(e.message);
        }
    }

    async function deleteDomain(id) {
        try {
            const res = await fetch(`${API_BASE}/${id}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            if (!res.ok) throw new Error("Failed to delete");
            fetchDomains();
            UI.success("Domain deleted successfully!");
        } catch (e) {
            UI.error(e.message);
        }
    }

    document.getElementById('add-domain-btn').addEventListener('click', addDomain);

    document.getElementById('logout-btn').addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
        } catch (_) { }
        window.location.href = '/login';
    });

    const accountMenuBtn = document.getElementById('account-menu-btn');
    const accountMenuDropdown = document.getElementById('account-menu-dropdown');
    const deleteAccountMenuBtn = document.getElementById('delete-account-menu-btn');
    const changePasswordMenuBtn = document.getElementById('change-password-menu-btn');
    let menuOpen = false;

    accountMenuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        menuOpen = !menuOpen;
        accountMenuDropdown.style.display = menuOpen ? 'block' : 'none';
    });

    document.addEventListener('click', (e) => {
        if (!accountMenuDropdown.contains(e.target) && e.target !== accountMenuBtn) {
            accountMenuDropdown.style.display = 'none';
            menuOpen = false;
        }
    });

    const deleteModal = document.getElementById('delete-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const confirmStep1Btn = document.getElementById('confirm-step-1-btn');
    const timerCountdown = document.getElementById('timer-countdown');
    const deleteStep1 = document.getElementById('delete-step-1');
    const deleteStep2 = document.getElementById('delete-step-2');
    const deleteConfirmationInput = document.getElementById('delete-confirmation-input');
    const finalDeleteBtn = document.getElementById('final-delete-btn');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');

    let timerInterval = null;

    deleteAccountMenuBtn.addEventListener('click', () => {
        accountMenuDropdown.style.display = 'none';
        menuOpen = false;
        deleteModal.style.display = 'flex';
        resetModal();
        startTimer();
    });

    modalCloseBtn.addEventListener('click', () => {
        deleteModal.style.display = 'none';
        resetModal();
    });

    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) {
            deleteModal.style.display = 'none';
            resetModal();
        }
    });

    function resetModal() {
        deleteStep1.style.display = 'block';
        deleteStep2.style.display = 'none';
        confirmStep1Btn.disabled = true;
        finalDeleteBtn.disabled = true;
        deleteConfirmationInput.value = '';
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function startTimer() {
        let seconds = 5;
        timerCountdown.textContent = seconds;
        confirmStep1Btn.disabled = true;

        timerInterval = setInterval(() => {
            seconds--;
            if (seconds <= 0) {
                clearInterval(timerInterval);
                timerCountdown.textContent = '0';
                confirmStep1Btn.disabled = false;
                document.getElementById('timer-display').innerHTML = 'You may now proceed.';
            } else {
                timerCountdown.textContent = seconds;
            }
        }, 1000);
    }

    confirmStep1Btn.addEventListener('click', () => {
        deleteStep1.style.display = 'none';
        deleteStep2.style.display = 'block';
        deleteConfirmationInput.focus();
    });

    deleteConfirmationInput.addEventListener('input', (e) => {
        const inputValue = e.target.value.toLowerCase().trim();
        finalDeleteBtn.disabled = inputValue !== 'yes, i know what i am doing';
    });

    cancelDeleteBtn.addEventListener('click', () => {
        deleteModal.style.display = 'none';
        resetModal();
    });

    finalDeleteBtn.addEventListener('click', async () => {
        try {
            finalDeleteBtn.disabled = true;
            finalDeleteBtn.textContent = 'Deleting...';

            const res = await fetch('/api/user/delete', {
                method: 'DELETE',
                credentials: 'include'
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || 'Failed to delete account');
            }

            await UI.alert('Your account has been successfully deleted.', 'Account Deleted');
            window.location.href = '/';
        } catch (e) {
            UI.error(e.message);
            finalDeleteBtn.disabled = false;
            finalDeleteBtn.textContent = 'Delete My Account';
        }
    });

    const changePwdModal = document.getElementById('change-password-modal');
    const changePwdModalCloseBtn = document.getElementById('change-pwd-modal-close-btn');
    const cancelChangePwdBtn = document.getElementById('cancel-change-pwd-btn');
    const submitChangePwdBtn = document.getElementById('submit-change-pwd-btn');

    const currentPwdInput = document.getElementById('current-password-input');
    const newPwdInput = document.getElementById('new-password-input');
    const confirmNewPwdInput = document.getElementById('confirm-new-password-input');

    function resetChangePwdModal() {
        currentPwdInput.value = '';
        newPwdInput.value = '';
        confirmNewPwdInput.value = '';
        submitChangePwdBtn.disabled = false;
        submitChangePwdBtn.textContent = 'Update Password';
    }

    changePasswordMenuBtn.addEventListener('click', () => {
        accountMenuDropdown.style.display = 'none';
        menuOpen = false;
        changePwdModal.style.display = 'flex';
        resetChangePwdModal();
    });

    changePwdModalCloseBtn.addEventListener('click', () => {
        changePwdModal.style.display = 'none';
        resetChangePwdModal();
    });

    cancelChangePwdBtn.addEventListener('click', () => {
        changePwdModal.style.display = 'none';
        resetChangePwdModal();
    });

    changePwdModal.addEventListener('click', (e) => {
        if (e.target === changePwdModal) {
            changePwdModal.style.display = 'none';
            resetChangePwdModal();
        }
    });

    submitChangePwdBtn.addEventListener('click', async () => {
        const curPwd = currentPwdInput.value;
        const newPwd = newPwdInput.value;
        const confirmPwd = confirmNewPwdInput.value;

        if (!curPwd || !newPwd || !confirmPwd) {
            UI.error('All fields are required.');
            return;
        }

        if (newPwd !== confirmPwd) {
            UI.error('New passwords do not match.');
            return;
        }

        if (newPwd.length < 6) {
            UI.error('New password must be at least 6 characters long.');
            return;
        }

        try {
            submitChangePwdBtn.disabled = true;
            submitChangePwdBtn.textContent = 'Updating...';

            const res = await fetch('/api/user/password', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    current_password: curPwd,
                    new_password: newPwd
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || 'Failed to update password');
            }

            changePwdModal.style.display = 'none';
            resetChangePwdModal();

            await UI.alert('Password updated successfully! Please log in again.', 'Success');
            window.location.href = '/login';
        } catch (e) {
            UI.error(e.message);
            submitChangePwdBtn.disabled = false;
            submitChangePwdBtn.textContent = 'Update Password';
        }
    });

    fetchDomains();
    fetchUserSummary();
});