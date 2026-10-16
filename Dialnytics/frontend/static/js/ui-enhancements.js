(function(){
 const body=document.body, theme=document.getElementById('themeToggle'), profile=document.getElementById('profileToggle'), menu=document.getElementById('profileMenu');
 const apply=()=>{const light=localStorage.getItem('dialnytics-theme')==='light';body.classList.toggle('light-theme',light);if(theme)theme.textContent=light?'☀':'☾'};apply();
 theme?.addEventListener('click',()=>{localStorage.setItem('dialnytics-theme',body.classList.contains('light-theme')?'dark':'light');apply()});
 profile?.addEventListener('click',()=>{menu.hidden=!menu.hidden;profile.setAttribute('aria-expanded',String(!menu.hidden))});
 document.addEventListener('click',e=>{if(menu&&!menu.hidden&&!menu.contains(e.target)&&!profile.contains(e.target)){menu.hidden=true;profile.setAttribute('aria-expanded','false')}});
 document.getElementById('shortcutHelp')?.addEventListener('click',()=>alert('Keyboard shortcuts: Ctrl+L to focus browser address bar; Tab to navigate controls; Enter to activate buttons.'));
 document.getElementById('tourHelp')?.addEventListener('click',()=>alert('Welcome to Dialnytics! Use Dashboard for call stats, Users to manage accounts, and Billing for subscription details.'));
 const dnd=document.getElementById('dndToggle');if(dnd){dnd.checked=localStorage.getItem('dialnytics-dnd')==='true';dnd.addEventListener('change',()=>{localStorage.setItem('dialnytics-dnd',String(dnd.checked));window.dialnyticsDnd=dnd.checked});window.dialnyticsDnd=dnd.checked}
})();