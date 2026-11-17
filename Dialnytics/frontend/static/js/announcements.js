// Announcements for users: popup, top banner and the notification bell.
(function () {
    const bell = document.getElementById('dnAnnBell');
    const bannerBox = document.getElementById('dnAnnBanners');
    if (!bell || !bannerBox) return;
    const count = bell.querySelector('.dn-ann-count');
    const drop = document.getElementById('dnAnnDrop');
    const list = document.getElementById('dnAnnList');
    const TAG = { update: '#818cf8', feature: '#a78bfa', maint: '#f59e0b', urgent: '#ef4444' };
    let items = [];
    let popupOpen = false;

    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }
    function when(iso) {
        const d = new Date(iso);
        const today = new Date();
        const t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        return d.toDateString() === today.toDateString() ? 'Today, ' + t : d.toLocaleDateString([], { day: 'numeric', month: 'short' }) + ', ' + t;
    }
    function post(id, action) {
        return fetch('/api/announcements/' + encodeURIComponent(id) + '/' + action, { method: 'POST' }).catch(() => {});
    }
    function textBlock(a) {
        const box = el('div', 'dn-ann-text');
        box.appendChild(el('b', '', a.title));
        if (a.message) box.appendChild(el('span', '', a.message));
        if (a.link) {
            const l = el('a', '', 'Learn more ›');
            l.href = a.link; l.target = '_blank'; l.rel = 'noopener noreferrer';
            box.appendChild(l);
        }
        return box;
    }
    function markRead(a) {
        if (!a.unread) return;
        a.unread = false;
        post(a.id, 'read');
        renderBell();
    }

    function renderBanners() {
        bannerBox.replaceChildren();
        items.filter((a) => a.banner).slice(0, 3).forEach((a) => {
            const b = el('div', 'dn-ann-banner');
            b.dataset.kind = a.kind;
            b.setAttribute('role', a.kind === 'urgent' ? 'alert' : 'status');
            b.appendChild(el('span', 'dn-ann-ico'));
            b.appendChild(textBlock(a));
            if (a.closable) {
                const x = el('button', 'dn-ann-x', '✕');
                x.type = 'button'; x.title = 'Hide'; x.setAttribute('aria-label', 'Hide announcement');
                x.onclick = () => { a.banner = false; a.unread = false; post(a.id, 'close_banner'); renderBanners(); renderBell(); };
                b.appendChild(x);
            }
            bannerBox.appendChild(b);
        });
    }

    function renderBell() {
        const unread = items.filter((a) => a.unread).length;
        count.textContent = unread > 9 ? '9+' : String(unread);
        count.hidden = !unread;
        list.replaceChildren();
        if (!items.length) { list.appendChild(el('div', 'dn-ann-empty', 'No announcements yet.')); return; }
        items.forEach((a) => {
            const row = el('div', 'dn-ann-item' + (a.unread ? ' unread' : ''));
            row.appendChild(el('span', 'dn-ann-udot'));
            const ico = el('span', 'dn-ann-ico'); ico.dataset.kind = a.kind; row.appendChild(ico);
            const body = el('div', '');
            body.appendChild(el('div', 't', a.title));
            if (a.message) body.appendChild(el('div', 'm', a.message));
            body.appendChild(el('div', 'd', when(a.date)));
            row.appendChild(body);
            row.onclick = () => { markRead(a); showPopup(a, true); };
            list.appendChild(row);
        });
    }

    function showPopup(a, fromBell) {
        if (popupOpen) return;
        popupOpen = true;
        const bg = el('div', 'dn-ann-modal-bg');
        const m = el('div', 'dn-ann-modal');
        m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
        const top = el('div', 'top');
        const ico = el('span', 'dn-ann-ico'); ico.dataset.kind = a.kind; top.appendChild(ico);
        const tag = el('span', 'dn-ann-tag', '● ' + a.kind_label); tag.style.color = TAG[a.kind] || TAG.update; top.appendChild(tag);
        m.appendChild(top);
        m.appendChild(el('h3', '', a.title));
        if (a.message) m.appendChild(el('div', 'm', a.message));
        if (a.link) {
            const l = el('a', '', 'Learn more ›'); l.href = a.link; l.target = '_blank'; l.rel = 'noopener noreferrer';
            l.style.color = 'var(--accent)'; l.style.fontWeight = '600'; m.appendChild(l);
        }
        m.appendChild(el('div', 'd', when(a.date)));
        const btns = el('div', 'dn-ann-btns');
        const close = (action) => {
            bg.remove(); popupOpen = false;
            a.popup = false;
            if (action) post(a.id, action);
            if (action === 'popup') { a.unread = false; renderBell(); }
            setTimeout(nextPopup, 300);
        };
        if (!fromBell) {
            const later = el('button', 'dn-btn', 'Remind me later'); later.type = 'button';
            later.onclick = () => close('remind');
            btns.appendChild(later);
        }
        const ok = el('button', 'dn-btn primary', 'Got it'); ok.type = 'button';
        ok.onclick = () => close(fromBell ? null : 'popup');
        btns.appendChild(ok);
        m.appendChild(btns);
        bg.appendChild(m);
        bg.addEventListener('click', (e) => { if (e.target === bg) close(fromBell ? null : 'remind'); });
        document.body.appendChild(bg);
        ok.focus();
    }
    function nextPopup() {
        if (popupOpen) return;
        // Never interrupt a live call: wait until the agent is free.
        if (document.body.classList.contains('on-call') || window.dnOnCall) { setTimeout(nextPopup, 15000); return; }
        const a = items.find((x) => x.popup);
        if (a) showPopup(a, false);
    }

    async function load() {
        try {
            const r = await fetch('/api/announcements', { cache: 'no-store', credentials: 'same-origin' });
            if (!r.ok) return;
            const d = await r.json();
            items = d.items || [];
            renderBanners(); renderBell(); nextPopup();
        } catch (e) {}
    }

    document.getElementById('dnAnnBtn').addEventListener('click', () => { drop.hidden = !drop.hidden; });
    document.getElementById('dnAnnReadAll').addEventListener('click', (e) => {
        e.stopPropagation();
        items.forEach((a) => { a.unread = false; });
        fetch('/api/announcements-read-all', { method: 'POST' }).catch(() => {});
        renderBell();
    });
    document.addEventListener('click', (e) => { if (!e.target.closest('#dnAnnBell')) drop.hidden = true; });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') drop.hidden = true; });
    load();
    setInterval(() => { if (!document.hidden) load(); }, 120000);
})();
