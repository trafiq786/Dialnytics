(() => {
  // Keep the existing dialer untouched; report only observed UI/RTC state.
  let last = '';
  async function heartbeat() {
    const rtc = document.getElementById('rtcStatus');
    const dialer = window.DialnyticsDialer;
    const busy = Boolean(dialer && typeof dialer.busy === 'function' && dialer.busy());
    const sub = document.getElementById('activitySub');
    const title = document.getElementById('activityTitle');
    const status = (title?.textContent || '').toLowerCase();
    const onCall = busy && (status.includes('active') || status.includes('connected') || status.includes('on hold'));
    const state = onCall ? 'on_call' : busy ? 'ringing' : 'available';
    if (state !== last) {
      if (state === 'on_call') window.__dialnyticsLiveStart = new Date().toISOString();
      else window.__dialnyticsLiveStart = null;
      last = state;
    }
    const number = document.getElementById('numberInput')?.value || '';
    try { await fetch('/api/live/heartbeat', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({state,number,direction:status.includes('incoming')?'incoming':'outgoing',started_at:window.__dialnyticsLiveStart})}); } catch (_) {}
  }
  heartbeat(); setInterval(heartbeat, 10000);
})();
