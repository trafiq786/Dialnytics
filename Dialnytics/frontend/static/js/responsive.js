/* Responsive helper: gives every data-table cell a label taken from its column
   heading, so phones can show each row as a card (see responsive.css). Also
   marks side-by-side panels so they stack on small screens. */
(function () {
    const SKIP = '.inv-paper, .no-cards, #dialRail, .dn-dialog-preview';
    function label(table) {
        if (table.closest(SKIP)) return;
        let head = table.tHead && table.tHead.rows[table.tHead.rows.length - 1];
        if (!head) {
            // tables without <thead>: a first row made only of <th> is the heading
            const first = table.rows[0];
            if (!first || !first.cells.length || Array.from(first.cells).some(c => c.tagName !== 'TH')) return;
            head = first;
            first.classList.add('rt-head');
        }
        const names = [];
        for (const th of head.cells) {
            const n = (th.innerText || th.textContent || '').trim().replace(/\s+/g, ' ');
            for (let i = 0; i < (th.colSpan || 1); i++) names.push(n);
        }
        if (names.length < 3) return;
        table.classList.add('rt-cards');
        const wrap = table.parentElement;
        if (wrap && wrap !== document.body && getComputedStyle(wrap).overflowX !== 'visible') wrap.classList.add('rt-wrap');
        for (const body of table.tBodies) {
            for (const row of body.rows) {
                if (row === head) continue;
                let col = 0;
                for (const td of row.cells) {
                    if (td.colSpan >= names.length) { col += td.colSpan; continue; }
                    const n = names[col] || '';
                    if (td.getAttribute('data-label') !== n) td.setAttribute('data-label', n);
                    wrapCell(td);
                    col += td.colSpan || 1;
                }
            }
        }
    }
    // A cell with several pieces (name + email, a list...) keeps them together
    // in one block, so on a phone they sit under each other next to the label.
    function wrapCell(td) {
        const kids = Array.from(td.childNodes).filter(n => n.nodeType === 1 || (n.nodeType === 3 && n.textContent.trim()));
        if (kids.length < 2) return;
        if (kids.length === 1 && kids[0].classList && kids[0].classList.contains('rt-v')) return;
        const box = document.createElement('div');
        box.className = 'rt-v';
        // a cell of only buttons / links / small forms keeps them in one row
        if (kids.every(n => n.nodeType === 1 && /^(A|BUTTON|FORM|SELECT|INPUT|LABEL)$/.test(n.tagName))) box.classList.add('rt-act');
        while (td.firstChild) box.appendChild(td.firstChild);
        td.appendChild(box);
    }
    function stackPanels(root) {
        // inline two-column grids (e.g. billing) stack on phones
        root.querySelectorAll('[style*="grid-template-columns"]').forEach(el => {
            if (el.closest(SKIP) || el.classList.contains('rsp-stack')) return;
            const cols = (el.style.gridTemplateColumns || '').trim();
            if (/^(1fr\s+1fr|minmax\(0,\s*\dfr\)\s+minmax\(0,\s*\dfr\))$/.test(cols)) el.classList.add('rsp-stack');
        });
    }
    let queued = false;
    function run() {
        queued = false;
        const main = document.querySelector('.shell-main') || document.body;
        main.querySelectorAll('table').forEach(label);
        stackPanels(main);
    }
    function queue() { if (!queued) { queued = true; requestAnimationFrame(run); } }
    function start() {
        run();
        const main = document.querySelector('.shell-main');
        // lists filled in later by scripts (CRM, orders, team...) get labels too
        if (main && window.MutationObserver) new MutationObserver(queue).observe(main, { childList: true, subtree: true });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
