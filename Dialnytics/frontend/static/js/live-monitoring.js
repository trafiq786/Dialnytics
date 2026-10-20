(() => {
  let agents = [];
  const rows = document.getElementById('liveRows');
  const search = document.getElementById('liveSearch');
  const filter = document.getElementById('liveFilter');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function draw() {
    const q=search.value.trim().toLowerCase(), f=filter.value;
    const count = st => agents.filter(a=>a.status===st).length;
    document.getElementById('liveOnline').textContent=agents.length-count('offline');
    document.getElementById('liveCalling').textContent=count('on_call');
    document.getElementById('liveAvailable').textContent=count('available');
    document.getElementById('liveOffline').textContent=count('offline');
    const visible=agents.filter(a=>(f==='all'||a.status===f)&&[a.name,a.email,a.number].some(v=>String(v||'').toLowerCase().includes(q)));
    rows.innerHTML=visible.map(a=>`<tr><td><strong>${esc(a.name)}</strong><small>${esc(a.email)}</small></td><td><span class="module-pill">${esc(a.status.replace('_',' '))}</span></td><td>${esc(a.direction||'—')}</td><td>${esc(a.number||'—')}</td><td class="live-duration" data-start="${esc(a.started_at||'')}">—</td></tr>`).join('') || '<tr><td colspan="5">No matching users</td></tr>';
    tick();
  }
  function tick() {document.querySelectorAll('.live-duration').forEach(el=>{const t=Date.parse(el.dataset.start);if(!Number.isFinite(t)){el.textContent='—';return;}const n=Math.max(0,Math.floor((Date.now()-t)/1000));el.textContent=`${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`;});}
  async function refresh(){try{const r=await fetch('/api/admin/live-monitoring',{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('Unable to load live status');agents=(await r.json()).agents||[];document.getElementById('liveError').textContent='';draw();}catch(e){document.getElementById('liveError').textContent=e.message;}}
  search.addEventListener('input',draw);filter.addEventListener('change',draw);refresh();setInterval(refresh,3000);setInterval(tick,1000);
})();
