(() => {
  let status='available', number='', direction='', started_at=null;
  function report(){fetch('/api/live/heartbeat',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({status,number,direction,started_at})}).catch(()=>{});}
  window.DialnyticsPresence={set(next,num,dir){if(next==='on_call'&&status!=='on_call')started_at=new Date().toISOString();if(next!=='on_call')started_at=null;status=next;number=num||'';direction=dir||'';report();}};
  window.addEventListener('dialnytics:call-ended',()=>window.DialnyticsPresence.set('available'));
  report();setInterval(report,5000);
})();