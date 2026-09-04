function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); }

function showError(message) { document.getElementById('error-message').textContent = message; }
function clearError() { document.getElementById('error-message').textContent = ''; }

// Renders a structured alert instead of one long run-on sentence -- each section
// gets a bold title and its own bullet list. sections: [{ title, items: [...] }]
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
        li.className = 'list-item booking-item';

        const start = new Date(booking.start_time).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        const end = new Date(booking.end_time).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        // Built with createElement/textContent throughout, never innerHTML with
        // interpolated values -- booking.title is user-supplied and shown to every
        // other user viewing this list, so treating it as HTML would be a stored-XSS hole.
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

        // only the booking's own owner sees a cancel button -- the backend already
        // enforces this with a 403, but hiding the control entirely for other
        // people's bookings is the correct UX rather than showing a button that
        // would just fail.
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

    // Checked once, up front: an end time not after the start time would fail
    // identically for every single day in the range, producing a wall of repeated
    // identical error messages. Catching it here also means we never fall through
    // to the reset-on-failure path with nothing useful to say.
    if (endTime <= startTime) {
        showError('Время окончания должно быть позже времени начала');
        return;
    }

    const allDays = dateRange(startDate, endDate);
    // A single explicitly-chosen day is honored even if it's a weekend (someone doing
    // this deliberately probably has a real event that day). A multi-day RANGE that
    // happens to span a weekend skips Sat/Sun automatically, since those days are
    // very unlikely to be intended just because they fall between two workdays.
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

// on page load, if a token is already stored, try to restore the session instead
// of always dropping back to the login form -- an expired/invalid token just
// falls through to showAuth() as before.
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
