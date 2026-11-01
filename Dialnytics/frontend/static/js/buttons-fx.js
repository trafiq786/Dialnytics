/* Premium button effects: cursor spotlight on hover, pop animation on click. No dependencies. */
(function(){
  var SEL='button,input[type=button],input[type=submit],input[type=reset],[role=button],.btn,.cm-btn,.cm-btn-alt,.drawer-action,.premium-edit,.refer-btn,.header-icon,.extra-btn,a.button,[class^="btn-"],[class*=" btn-"],.um-save,.um-cancel,.um-del,.um-mini,.um-x,.dn-btn-ghost,.dn-btn-danger,.seg a';
  function find(t){return t&&t.closest?t.closest(SEL):null}
  function ready(el){
    if(el.dataset.fx)return;el.dataset.fx='1';
    if(el.matches('input,select,textarea')||el.classList.contains('dn-no-fx'))return;
    var cs=getComputedStyle(el);
    if(cs.position==='static')el.classList.add('dn-rel');
    var after=getComputedStyle(el,'::after').content;
    if(!after||after==='none'||after==='normal')el.classList.add('dn-spot');
  }
  document.addEventListener('mouseover',function(e){var el=find(e.target);if(el)ready(el)},true);
  document.addEventListener('mousemove',function(e){
    var el=find(e.target);if(!el||!el.classList.contains('dn-spot'))return;
    var r=el.getBoundingClientRect();
    el.style.setProperty('--mx',(e.clientX-r.left)+'px');el.style.setProperty('--my',(e.clientY-r.top)+'px');
  },true);
  document.addEventListener('click',function(e){
    var el=find(e.target);if(!el||el.disabled||el.classList.contains('dn-no-fx'))return;
    el.classList.remove('dn-pop');void el.offsetWidth;el.classList.add('dn-pop');
    setTimeout(function(){el.classList.remove('dn-pop')},520);
  },true);
})();
