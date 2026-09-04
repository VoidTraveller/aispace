function formatError(err, fallback) {
    const detail = err && err.detail;
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
    return fallback;
}

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    document.getElementById('error-message').textContent = '';

    const payload = {
        first_name: document.getElementById('register-first-name').value,
        last_name: document.getElementById('register-last-name').value,
        email: document.getElementById('register-email').value,
        password: document.getElementById('register-password').value,
    };

    const response = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const err = await response.json();
        document.getElementById('error-message').textContent = formatError(err, 'Ошибка регистрации');
        return;
    }

    alert('Регистрация успешна! Теперь войдите.');
    window.location.href = '/';
});
