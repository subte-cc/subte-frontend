/**
* Subte super cool custom alerts library
*/

window.UI = (() => {
    let toastContainer = null;

    function createToastContainer() {
        if (toastContainer) return;
        toastContainer = document.createElement('div');
        toastContainer.className = 'ui-toast-container';
        document.body.appendChild(toastContainer);
    }

    /**
     * Shows a non-blocking toast notification.
     * @param {string} message 
     * @param {'info'|'success'|'error'} type 
     * @param {number} duration 
     */
    function notify(message, type = 'info', duration = 5000) {
        createToastContainer();
        const toast = document.createElement('div');
        toast.className = `ui-toast ${type}`;
        toast.innerHTML = `<span>${message}</span>`;

        toastContainer.appendChild(toast);

        const removeToast = () => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        };

        const timer = setTimeout(removeToast, duration);
        toast.onclick = () => {
            clearTimeout(timer);
            removeToast();
        }
    }

    /**
     * Shows a blocking modal dialog.
     * @param {string} title 
     * @param {string} message 
     * @param {boolean} isConfirm 
     * @param {string} confirmText
     * @param {string} cancelText
     * @returns {Promise<boolean>}
     */
    function showModal(title, message, isConfirm = false, confirmText = 'OK', cancelText = 'Cancel') {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'ui-modal-overlay';

            overlay.innerHTML = `
                <div class="ui-modal">
                    <div class="ui-modal-title">${title}</div>
                    <div class="ui-modal-body">${message}</div>
                    <div class="ui-modal-actions">
                        ${isConfirm ? `<button class="ui-modal-btn ui-modal-btn-cancel" id="ui-modal-cancel">${cancelText}</button>` : ''}
                        <button class="ui-modal-btn ui-modal-btn-confirm" id="ui-modal-ok">${confirmText}</button>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);

            setTimeout(() => overlay.classList.add('active'), 10);

            const close = (result) => {
                overlay.classList.remove('active');
                setTimeout(() => {
                    overlay.remove();
                    resolve(result);
                }, 300);
            };

            overlay.querySelector('#ui-modal-ok').onclick = () => close(true);
            if (isConfirm) {
                overlay.querySelector('#ui-modal-cancel').onclick = () => close(false);
            }

            if (!isConfirm) {
                overlay.onclick = (e) => {
                    if (e.target === overlay) close(true);
                };
            }
        });
    }

    const nativeAlert = window.alert;
    window.alert = (message) => {
        return showModal('Notification', message, false);
    };

    const nativeConfirm = window.confirm;
    window.confirm = (message) => {
        return showModal('Confirmation', message, true);
    };

    return {
        alert: (msg, title = 'Notification') => showModal(title, msg, false),
        confirm: (msg, title = 'Confirmation', confirmText = 'OK', cancelText = 'Cancel') => showModal(title, msg, true, confirmText, cancelText),
        notify,
        success: (msg) => notify(msg, 'success'),
        error: (msg) => notify(msg, 'error'),
        info: (msg) => notify(msg, 'info')
    };
})();