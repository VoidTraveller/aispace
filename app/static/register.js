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
        document.getElementById('error-message').textContent = err.detail || 'Ошибка регистрации';
        return;
    }

    alert('Регистрация успешна! Теперь войдите.');
    window.location.href = '/';
});
