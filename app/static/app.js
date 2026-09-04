function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); }

function showError(message) { document.getElementById('error-message').textContent = message; }
function clearError() { document.getElementById('error-message').textContent = ''; }

// sections: [{ title, items: [...] }] -- renders as titled bullet lists, not one run-on sentence
function showErrorSections(sections) {
    const container = document.getElementById('error-message');
    container.textContent = '';
    sections.forEach((section) => {
        const block = document.createElement('div');
        block.className = 'alert-block';

        const title = document.createElement('div');
        title.className = 'alert-title';
        title.textContent = section.title;
        block.appendChild(title);

        const ul = document.createElement('ul');
        ul.className = 'alert-list';
        section.items.forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            ul.appendChild(li);
        });
        block.appendChild(ul);
        container.appendChild(block);
    });
}

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

let currentUser = null;

async function fetchCurrentUser() {
    const response = await authFetch('/auth/me');
    if (!response.ok) return null;
    return response.json();
}

function showApp() {
    document.getElementById('auth-forms').style.display = 'none';
    document.getElementById('user-info').style.display = 'block';
    document.getElementById('app-section').style.display = 'block';
    document.getElementById('user-name').textContent = `${currentUser.first_name} ${currentUser.last_name}`;
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
    currentUser = await fetchCurrentUser();
    showApp();
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

        // textContent, not innerHTML -- room names are now user-created, same reasoning as booking titles
        const info = document.createElement('span');
        info.textContent = `${room.name} · вместимость ${room.capacity}`;

        const badge = document.createElement('span');
        badge.className = `badge ${room.is_active ? 'badge-success' : 'badge-muted'}`;
        badge.textContent = room.is_active ? 'доступна' : 'недоступна';

        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'btn-secondary';
        toggleBtn.textContent = room.is_active ? 'Деактивировать' : 'Активировать';
        toggleBtn.addEventListener('click', async () => {
            const res = await authFetch(`/rooms/${room.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !room.is_active }),
            });
            if (res.ok) {
                loadRooms();
            } else {
                const err = await res.json();
                showError(formatError(err, 'Не удалось изменить статус комнаты'));
            }
        });

        li.appendChild(info);
        li.appendChild(badge);
        li.appendChild(toggleBtn);
        list.appendChild(li);

        if (room.is_active) {
            const option = document.createElement('option');
            option.value = room.id;
            option.textContent = room.name;
            select.appendChild(option);
        }
    });
}

document.getElementById('room-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const payload = {
        name: document.getElementById('room-name').value,
        capacity: parseInt(document.getElementById('room-capacity').value, 10),
    };

    const response = await authFetch('/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const err = await response.json();
        showError(formatError(err, 'Не удалось добавить комнату'));
        return;
    }

    document.getElementById('room-form').reset();
    loadRooms();
});

async function loadBookings() {
    const response = await fetch('/bookings');
    const bookings = await response.json();

    const list = document.getElementById('bookings-list');
    list.innerHTML = '';

    bookings.forEach((booking) => {
        const li = document.createElement('li');
        li.className = 'list-item booking-item';

        const start = new Date(booking.start_time).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        const end = new Date(booking.end_time).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        // textContent, not innerHTML -- booking.title is user-supplied and shown to everyone
        const info = document.createElement('div');
        info.className = 'booking-info';

        const titleDiv = document.createElement('div');
        titleDiv.className = 'booking-title';
        titleDiv.textContent = booking.title;

        const metaDiv = document.createElement('div');
        metaDiv.className = 'booking-meta';

        const roomBadge = document.createElement('span');
        roomBadge.className = 'badge badge-muted';
        roomBadge.textContent = booking.room_name;

        const userSpan = document.createElement('span');
        userSpan.textContent = booking.user_name;

        const timeSpan = document.createElement('span');
        timeSpan.textContent = `${start}–${end}`;

        metaDiv.appendChild(roomBadge);
        metaDiv.appendChild(userSpan);
        metaDiv.appendChild(timeSpan);
        info.appendChild(titleDiv);
        info.appendChild(metaDiv);
        li.appendChild(info);

        // hide the cancel button for others' bookings rather than showing one that'd 403
        const isOwn = currentUser && booking.user_id === currentUser.id;
        if (isOwn) {
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
            li.appendChild(deleteBtn);
        }

        list.appendChild(li);
    });
}

// most bookings are same-day, so default the end date to match the start date
document.getElementById('booking-start-date').addEventListener('change', () => {
    document.getElementById('booking-end-date').value = document.getElementById('booking-start-date').value;
});

// local y/m/d, never toISOString() -- that converts to UTC and shifts the date in timezones ahead of it
function formatLocalDate(date) {
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// every day from startDateStr to endDateStr inclusive -- one same-time booking per day, not one multi-day block
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

function isWeekend(dateStr) {
    const day = new Date(`${dateStr}T00:00:00`).getDay();
    return day === 0 || day === 6; // Sunday=0, Saturday=6
}

function populateTimeSelect(selectId, values, defaultValue) {
    const select = document.getElementById(selectId);
    values.forEach((v) => {
        const option = document.createElement('option');
        option.value = v;
        option.textContent = v;
        if (v === defaultValue) option.selected = true;
        select.appendChild(option);
    });
}

const HOURS = Array.from({ length: 24 }, (_, h) => h.toString().padStart(2, '0'));
const MINUTES = ['00', '15', '30', '45'];

populateTimeSelect('booking-start-hour', HOURS, '09');
populateTimeSelect('booking-start-minute', MINUTES, '00');
populateTimeSelect('booking-end-hour', HOURS, '10');
populateTimeSelect('booking-end-minute', MINUTES, '00');

document.getElementById('booking-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const startDate = document.getElementById('booking-start-date').value;
    const endDate = document.getElementById('booking-end-date').value;
    const startTime = `${document.getElementById('booking-start-hour').value}:${document.getElementById('booking-start-minute').value}`;
    const endTime = `${document.getElementById('booking-end-hour').value}:${document.getElementById('booking-end-minute').value}`;
    const roomId = parseInt(document.getElementById('booking-room').value, 10);
    const title = document.getElementById('booking-title').value;

    // check once, up front -- otherwise this fails identically for every day in the range
    if (endTime <= startTime) {
        showError('Время окончания должно быть позже времени начала');
        return;
    }

    const allDays = dateRange(startDate, endDate);
    // a single chosen day is honored even if it's a weekend; a multi-day range skips Sat/Sun
    const days = allDays.length > 1 ? allDays.filter((d) => !isWeekend(d)) : allDays;
    const skipped = allDays.length > 1 ? allDays.filter((d) => isWeekend(d)) : [];

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

    const sections = [];
    if (skipped.length > 0) {
        sections.push({ title: 'Пропущены выходные дни:', items: skipped });
    }
    if (failures.length > 0) {
        sections.push({ title: 'Не удалось забронировать:', items: failures });
    }

    if (failures.length > 0) {
        // leave the form filled in on failure -- the user shouldn't have to
        // re-enter everything to fix and retry
        showErrorSections(sections);
        loadBookings();
        return;
    }

    if (sections.length > 0) {
        showErrorSections(sections);
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

// restore session on page load if a token is stored; falls through to showAuth() if invalid
(async () => {
    if (getToken()) {
        currentUser = await fetchCurrentUser();
        if (currentUser) {
            showApp();
            return;
        }
        clearToken();
    }
    showAuth();
})();
