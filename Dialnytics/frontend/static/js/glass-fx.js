/* Liquid glass: soft light that follows the cursor inside glass cards. Cheap (one rAF, only the hovered card). */
(function(){
  if(!window.matchMedia||!matchMedia('(pointer:fine)').matches||matchMedia('(prefers-reduced-motion:reduce)').matches)return;
  var SEL='.shell-main .panel,.shell-main .stat-card,.shell-main .center-card,.shell-main .card,.shell-main .chart-card,.shell-main .user-panel,.shell-main .users-hero,.shell-main .revenue-card,.shell-main .row-card,.shell-main .prefs-card,.shell-main .member-card,.shell-main .client-card,.shell-main .cost-panel,.dial-rail,.shell-nav,.shell-top';
  var el=null,x=0,y=0,raf=0;
  function paint(){raf=0;if(!el)return;var r=el.getBoundingClientRect();el.style.setProperty('--gx',(x-r.left)+'px');el.style.setProperty('--gy',(y-r.top)+'px')}
  document.addEventListener('mousemove',function(e){
    var t=e.target&&e.target.closest&&e.target.closest(SEL);
    if(t!==el){if(el){el.style.removeProperty('--gx');el.style.removeProperty('--gy')}el=t}
    if(!el)return;x=e.clientX;y=e.clientY;if(!raf)raf=requestAnimationFrame(paint);
  },{passive:true});
})();
