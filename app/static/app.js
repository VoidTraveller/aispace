function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); }

function showError(message) { document.getElementById('error-message').textContent = message; }
function clearError() { document.getElementById('error-message').textContent = ''; }

function formatError(err, fallback) {
    const detail = err && err.detail;
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
    return fallback;
}

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
        showError(formatError(err, 'Ошибка входа'));
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
        li.className = 'list-item';
        const badgeClass = room.is_active ? 'badge-success' : 'badge-muted';
        const badgeText = room.is_active ? 'доступна' : 'недоступна';
        li.innerHTML = `<span>${room.name} · вместимость ${room.capacity}</span><span class="badge ${badgeClass}">${badgeText}</span>`;
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
        li.className = 'list-item';

        const start = new Date(booking.start_time).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        const end = new Date(booking.end_time).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        const info = document.createElement('span');
        info.textContent = `${booking.title} · ${start}–${end}`;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-danger';
        deleteBtn.textContent = 'Отменить';
        deleteBtn.addEventListener('click', async () => {
            const res = await authFetch(`/bookings/${booking.id}`, { method: 'DELETE' });
            if (res.ok) {
                loadBookings();
            } else {
                const err = await res.json();
                showError(formatError(err, 'Не удалось отменить бронь'));
            }
        });
        li.appendChild(info);
        li.appendChild(deleteBtn);
        list.appendChild(li);
    });
}

// most bookings are same-day, so default the end date to match the start date
document.getElementById('booking-start-date').addEventListener('change', () => {
    document.getElementById('booking-end-date').value = document.getElementById('booking-start-date').value;
});

// Formats a Date using its LOCAL year/month/day -- never use toISOString() for this,
// since that converts to UTC first and silently shifts the date by a day in any
// timezone ahead of UTC (exactly the bug that caused 11 Sep to come out as 10 Sep).
function formatLocalDate(date) {
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// list of YYYY-MM-DD strings for every day from startDateStr to endDateStr, inclusive.
// Used to turn "10:00-15:00, 4 Sep - 7 Sep" into 4 separate same-time daily bookings,
// rather than one continuous multi-day block that would (wrongly) occupy the room
// overnight too.
function dateRange(startDateStr, endDateStr) {
    const dates = [];
    const current = new Date(`${startDateStr}T00:00:00`);
    const end = new Date(`${endDateStr}T00:00:00`);
    while (current <= end) {
        dates.push(formatLocalDate(current));
        current.setDate(current.getDate() + 1);
    }
    return dates;
}

document.getElementById('booking-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const startDate = document.getElementById('booking-start-date').value;
    const endDate = document.getElementById('booking-end-date').value;
    const startTime = document.getElementById('booking-start-time').value;
    const endTime = document.getElementById('booking-end-time').value;
    const roomId = parseInt(document.getElementById('booking-room').value, 10);
    const title = document.getElementById('booking-title').value;

    const days = dateRange(startDate, endDate);
    const failures = [];

    for (const day of days) {
        const payload = {
            room_id: roomId,
            title: title,
            start_time: `${day}T${startTime}`,
            end_time: `${day}T${endTime}`,
        };

        const response = await authFetch('/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const err = await response.json();
            failures.push(`${day}: ${formatError(err, 'ошибка')}`);
        }
    }

    if (failures.length > 0) {
        showError(`Забронировано не для всех дней — ${failures.join('; ')}`);
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
        showError(formatError(err, 'Не удалось создать бронь'));
        return;
    }

    document.getElementById('nl-form').reset();
    loadBookings();
});

showAuth();
