/* Dialnytics in-app navigation.
 *
 * Sidebar links, Today/Week/Month buttons and other in-app page links load
 * only the page content (#pageMain + #pageScripts) instead of reloading the
 * whole document, so the dialer rail, the Telnyx/Twilio connection and any
 * active call keep running. "Call" links (/dialer?number=...) dial straight
 * from the rail. If anything goes wrong we fall back to a normal page load.
 */
(function () {
    'use strict';

    // ---- Page-scoped listener/interval tracking ---------------------------
    // Listeners that page scripts add to window/document are removed when the
    // user leaves that page, so old pages cannot react to new events.
    let capturing = 0;
    let tracked = [];
    let intervals = [];
    const nativeAdd = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function (type, listener, options) {
        if (capturing > 0 && (this === window || this === document)) {
            tracked.push([this, type, listener, options]);
        }
        return nativeAdd.call(this, type, listener, options);
    };
    const nativeSetInterval = window.setInterval;
    window.setInterval = function () {
        const id = nativeSetInterval.apply(window, arguments);
        if (capturing > 0) intervals.push(id);
        return id;
    };

    window.DialnyticsNav = {
        capture(on) { capturing = Math.max(0, capturing + (on ? 1 : -1)); },
    };

    const PAGE_PREFIXES = ['/dashboard', '/call-logs', '/messages', '/voicemails', '/recordings',
        '/contacts', '/crm', '/power-dialer', '/campaigns', '/follow-ups', '/scripts', '/billing',
        '/customers', '/invoices', '/users', '/settings'];

    function isAppPage(url) {
        if (url.origin !== location.origin) return false;
        const path = url.pathname.replace(/\/+$/, '') || '/';
        if (/\/(pdf|audio)$/.test(path) || url.searchParams.has('download')) return false;
        return PAGE_PREFIXES.some((p) => path === p || path.startsWith(p + '/'));
    }

    function hardNavigate(url) {
        location.assign(url.href || url);
    }

    function leavePage() {
        try { window.dispatchEvent(new CustomEvent('dialnytics:page-leave')); } catch (e) {}
        tracked.forEach(([target, type, listener, options]) => {
            try { target.removeEventListener(type, listener, options); } catch (e) {}
        });
        intervals.forEach((id) => clearInterval(id));
        tracked = [];
        intervals = [];
        document.querySelectorAll('dialog[open]').forEach((d) => { try { d.close(); } catch (e) {} });
        document.body.style.overflow = '';
        const menu = document.getElementById('profileMenu');
        if (menu) menu.hidden = true;
    }

    // Recreate <script> elements so the browser executes them, in order.
    // Same-origin files are fetched and run inline so that listener capture
    // covers exactly the page script and nothing else (e.g. the call SDK).
    function execInline(old, code, label) {
        const script = document.createElement('script');
        for (const attr of old.attributes) if (attr.name !== 'src') script.setAttribute(attr.name, attr.value);
        script.textContent = code + (label ? '\n//# sourceURL=' + label : '');
        capturing += 1;
        try { old.replaceWith(script); } finally { capturing = Math.max(0, capturing - 1); }
    }

    async function runScript(old) {
        if (old.hasAttribute('data-nav-marker')) { old.remove(); return; }
        const type = (old.getAttribute('type') || '').trim().toLowerCase();
        if (type && type !== 'text/javascript') return;  // JSON data blocks stay as they are
        if (!old.src) return execInline(old, old.textContent, '');
        const src = new URL(old.src, location.href);
        if (src.origin === location.origin) {
            const res = await fetch(src.href, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('Could not load ' + src.pathname);
            return execInline(old, await res.text(), src.href);
        }
        await new Promise((resolve) => {   // third-party file: load normally
            const script = document.createElement('script');
            for (const attr of old.attributes) script.setAttribute(attr.name, attr.value);
            script.async = false;
            script.onload = script.onerror = () => resolve();
            old.replaceWith(script);
        });
    }

    async function runScriptsIn(container) {
        for (const s of Array.from(container.querySelectorAll('script'))) {
            try { await runScript(s); } catch (e) { console.error('Page script failed', e); }
        }
    }

    let navSeq = 0;
    let currentKey = location.pathname + location.search;

    async function navigate(url, push) {
        const main = document.getElementById('pageMain');
        const scriptsBox = document.getElementById('pageScripts');
        if (!main || !scriptsBox) return hardNavigate(url);
        const seq = ++navSeq;
        document.body.classList.add('nav-loading');
        main.setAttribute('aria-busy', 'true');
        let doc, finalUrl;
        try {
            const res = await fetch(url.href, { credentials: 'same-origin', cache: 'no-store',
                headers: { 'X-Requested-With': 'dialnytics-nav' } });
            finalUrl = new URL(res.url || url.href);
            const type = res.headers.get('content-type') || '';
            if (!res.ok || !type.includes('text/html') || !isAppPage(finalUrl)) {
                // Login expired, error page or not an app page: load it normally.
                if (seq === navSeq) hardNavigate(res.ok ? finalUrl : url);
                return;
            }
            const html = await res.text();
            doc = new DOMParser().parseFromString(html, 'text/html');
        } catch (err) {
            if (seq === navSeq) hardNavigate(url);
            return;
        }
        if (seq !== navSeq) return;  // a newer click won
        const newMain = doc.getElementById('pageMain');
        const newScripts = doc.getElementById('pageScripts');
        if (!newMain || !newScripts) return hardNavigate(finalUrl);

        leavePage();
        document.title = doc.title || document.title;
        const nav = document.querySelector('.shell-nav nav');
        const newNav = doc.querySelector('.shell-nav nav');
        if (nav && newNav) nav.innerHTML = newNav.innerHTML;
        const settings = document.querySelector('.shell-nav .nav-settings');
        const newSettings = doc.querySelector('.shell-nav .nav-settings');
        if (settings && newSettings) settings.className = newSettings.className;

        if (push) history.pushState({ dnNav: true }, '', finalUrl.href);
        else if (finalUrl.href !== location.href) history.replaceState({ dnNav: true }, '', finalUrl.href);
        currentKey = location.pathname + location.search;

        main.innerHTML = newMain.innerHTML;
        scriptsBox.innerHTML = newScripts.innerHTML;
        main.removeAttribute('aria-busy');
        document.body.classList.remove('nav-loading');
        main.scrollTop = 0;
        window.scrollTo(0, 0);

        await runScriptsIn(main);
        await runScriptsIn(scriptsBox);
        try { window.dispatchEvent(new CustomEvent('dialnytics:page-load')); } catch (e) {}
        const heading = main.querySelector('h1');
        if (heading) { heading.setAttribute('tabindex', '-1'); heading.focus({ preventScroll: true }); }
    }

    // "Call" links: dial from the rail without leaving the page.
    function dialFromLink(url) {
        const number = (url.searchParams.get('number') || '').replace(/[\s().-]/g, '');
        if (!/^\+[1-9]\d{6,14}$/.test(number)) return false;
        const dialer = window.DialnyticsDialer;
        const input = document.getElementById('numberInput');
        const say = (msg, bad) => {
            if (typeof window.setStatus === 'function') window.setStatus(msg, bad ? 'var(--danger)' : undefined);
        };
        if (!dialer || !input) return false;
        if (dialer.busy()) { say('Another call is active. Finish it before calling ' + number + '.', true); return true; }
        input.value = number;
        if (!dialer.ready()) { say('Dialer is still connecting. Press the green button when it shows Ready.', true); return true; }
        dialer.dial(number).catch((err) => say(err.message || 'Call could not be started', true));
        return true;
    }

    document.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0 ||
            event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const link = event.target.closest && event.target.closest('a[href]');
        if (!link || link.hasAttribute('download')) return;
        const target = link.getAttribute('target');
        if (target && target !== '_self') return;
        let url;
        try { url = new URL(link.href, location.href); } catch (e) { return; }
        if (url.origin !== location.origin) return;
        if (url.pathname === '/dialer' && url.searchParams.has('number')) {
            if (dialFromLink(url)) event.preventDefault();
            return;
        }
        if (!isAppPage(url)) return;
        if (url.pathname === location.pathname && url.search === location.search && url.hash) return;
        event.preventDefault();
        navigate(url, true);
    });

    window.addEventListener('popstate', () => {
        const key = location.pathname + location.search;
        if (key === currentKey) return;  // only the #hash changed
        const url = new URL(location.href);
        if (isAppPage(url)) navigate(url, false);
        else hardNavigate(url);
    });

    try { history.replaceState({ dnNav: true }, '', location.href); } catch (e) {}
})();
