/* Listen-only phone for pages without the dialer (super admin, resellers).
   Signs in to Telnyx with the viewer's calling login and only ever answers the
   silent "live call listening" leg that the server sends after Listen is pressed.
   Exposes the same window.DNMonitor API as dialer.js. */
(function () {
    if (window.DNMonitor) return;
    let client = null, ready = null, call = null, expect = null, muted = true;
    const audio = document.createElement('audio');
    audio.id = 'monitorAudio';
    audio.autoplay = true;
    audio.hidden = true;
    document.body.appendChild(audio);

    const digits = (v) => String(v || '').replace(/\D/g, '').slice(-9);
    const emit = (state) => document.dispatchEvent(new CustomEvent('dn-monitor', { detail: { state } }));
    function dead(c) {
        const st = String((c && c.state) || '').toLowerCase();
        return ['hangup', 'destroy', 'purge', 'done'].includes(st);
    }
    function isOffer(c) {
        if (!expect || Date.now() > expect.until) return false;
        const o = c.options || {};
        const hs = o.customHeaders || o.custom_headers || [];
        if (Array.isArray(hs) && hs.some((h) => String(h.name || '').toLowerCase() === 'x-dn-monitor')) return true;
        const from = digits(o.remoteCallerNumber || o.callerNumber || '');
        return !!from && from === digits(expect.from);
    }
    function connect() {
        if (ready) return ready;
        ready = (async () => {
            const Klass = window.TelnyxWebRTC && window.TelnyxWebRTC.TelnyxRTC;
            if (!Klass) throw new Error('Calling service failed to load');
            const res = await fetch('/api/webrtc-token', { cache: 'no-store' });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.token) throw new Error(data.detail || 'Could not sign in the listening phone');
            client = new Klass({ login_token: data.token });
            await new Promise((resolve, reject) => {
                const t = setTimeout(() => reject(new Error('Listening phone did not connect')), 15000);
                client.on('telnyx.ready', () => { clearTimeout(t); resolve(); });
                client.on('telnyx.error', () => { clearTimeout(t); reject(new Error('Listening phone could not sign in')); });
                client.on('telnyx.notification', (n) => {
                    const c = n && (n.call || n);
                    if (!c || !c.state) return;
                    const st = String(c.state).toLowerCase();
                    if (call && c.id === call.id) {
                        if (dead(c)) { call = null; emit('ended'); return; }
                        if (st === 'active') {
                            try { if (muted) c.muteAudio(); } catch (e) {}
                            if (c.remoteStream && audio.srcObject !== c.remoteStream) {
                                audio.srcObject = c.remoteStream;
                                audio.play().catch(() => {});
                            }
                            emit('active');
                        }
                        return;
                    }
                    if (!call && (st === 'ringing' || st === 'new') && isOffer(c)) {
                        expect = null;
                        call = c;
                        try { c.answer(); } catch (e) {}
                        return;
                    }
                    // Anything else ringing this login is not ours: refuse it.
                    if (st === 'ringing' && !isOffer(c)) { try { c.hangup(); } catch (e) {} }
                });
                client.connect();
            });
        })();
        ready.catch(() => { ready = null; });
        return ready;
    }
    window.DNMonitor = {
        standalone: true,
        prepare: connect,
        busy: () => false,
        expect: (from) => { expect = { from: from || '', until: Date.now() + 45000 }; },
        cancel: () => { expect = null; },
        setMuted: (m) => {
            muted = !!m;
            if (!call) return;
            try { if (m) call.muteAudio(); else call.unmuteAudio(); } catch (e) {}
        },
        hangup: () => {
            expect = null;
            const c = call;
            call = null;
            if (c) { try { c.hangup(); } catch (e) {} }
        },
        active: () => !!call
    };
})();
