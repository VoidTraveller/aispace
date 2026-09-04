function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); }

function showError(message) { document.getElementById('error-message').textContent = message; }
function clearError() { document.getElementById('error-message').textContent = ''; }

async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${getToken()}`;
    return fetch(url, options);
}

function showApp(email) {
    document.getElementById('auth-forms').style.display = 'none';
    document.getElementById('user-info').style.display = 'block';
    document.getElementById('app-section').style.display = 'block';
    document.getElementById('user-name').textContent = email;
    loadRooms();
    loadBookings();
}

function showAuth() {
    document.getElementById('auth-forms').style.display = 'block';
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('app-section').style.display = 'none';
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
    });

    if (!response.ok) {
        const err = await response.json();
        showError(err.detail || 'Ошибка входа');
        return;
    }

    const data = await response.json();
    setToken(data.access_token);
    showApp(email);
});

document.getElementById('logout-btn').addEventListener('click', () => {
    clearToken();
    showAuth();
});

async function loadRooms() {
    const response = await fetch('/rooms');
    const rooms = await response.json();

    const list = document.getElementById('rooms-list');
    const select = document.getElementById('booking-room');
    list.innerHTML = '';
    select.innerHTML = '';

    rooms.forEach((room) => {
        const li = document.createElement('li');
        li.textContent = `${room.name} (вместимость: ${room.capacity})` + (room.is_active ? '' : ' — недоступна');
        list.appendChild(li);

        if (room.is_active) {
            const option = document.createElement('option');
            option.value = room.id;
            option.textContent = room.name;
            select.appendChild(option);
        }
    });
}

async function loadBookings() {
    const response = await fetch('/bookings');
    const bookings = await response.json();

    const list = document.getElementById('bookings-list');
    list.innerHTML = '';

    bookings.forEach((booking) => {
        const li = document.createElement('li');
        li.textContent = `${booking.title}: ${booking.start_time} — ${booking.end_time} (комната ${booking.room_id}) `;

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Отменить';
        deleteBtn.addEventListener('click', async () => {
            const res = await authFetch(`/bookings/${booking.id}`, { method: 'DELETE' });
            if (res.ok) {
                loadBookings();
            } else {
                const err = await res.json();
                showError(err.detail || 'Не удалось отменить бронь');
            }
        });
        li.appendChild(deleteBtn);
        list.appendChild(li);
    });
}

document.getElementById('booking-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const payload = {
        room_id: parseInt(document.getElementById('booking-room').value, 10),
        title: document.getElementById('booking-title').value,
        start_time: document.getElementById('booking-start').value,
        end_time: document.getElementById('booking-end').value,
    };

    const response = await authFetch('/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const err = await response.json();
        showError(err.detail || 'Не удалось создать бронь');
        return;
    }

    document.getElementById('booking-form').reset();
    loadBookings();
});

document.getElementById('nl-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    const phrase = document.getElementById('nl-phrase').value;

    const response = await authFetch('/bookings/nl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phrase }),
    });

    if (!response.ok) {
        const err = await response.json();
        showError(err.detail || 'Не удалось создать бронь');
        return;
    }

    document.getElementById('nl-form').reset();
    loadBookings();
});

showAuth();
