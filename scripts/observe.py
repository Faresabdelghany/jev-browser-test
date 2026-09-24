"""Turn the live page into a numbered element table Jev can choose from.

Every step produces a *fresh* table (indices are not stable across steps). Each
included element is tagged with `data-jev-idx="<n>"` so the runner can act on it
with a plain Playwright locator. Only the main frame is observed.

The observation also records a *fingerprint* (url, title, text head, one identity/meaning
tuple per tagged node). Right before acting, `fingerprint()` re-reads the same tuples and
`compare_fingerprint()` decides whether the page still means what Jev decided on.
"""
from __future__ import annotations

import hashlib

# Shared by OBSERVE_JS and FINGERPRINT_JS so the freshness guard compares tuples produced by the very same
# functions at observe time and at act time. Identity and meaning only: no geometry, because animations
# move boxes without changing what an element means, and Playwright re-resolves geometry at click time.
JS_HELPERS = r"""
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  // FNV-1a over UTF-16 code units, as 8 hex chars: small, deterministic, good enough to spot a changed row/form.
  const strHash = s => {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
    return (h >>> 0).toString(16).padStart(8, '0');
  };
  const scopeOf = el => el.closest('form, dialog, [role="dialog"], tr, [role="row"], li, label') || el.parentElement || el;
  const BUTTON_INPUTS = ['submit', 'button', 'reset', 'image'];  // their .value is a caption, not content
  // The current content of a field, for the table and the fingerprint alike: text-like inputs (password
  // shown as "(filled)"), textareas, the selected option of a select, the text of a contenteditable.
  // Buttons, checkboxes, radios and file inputs have no content.
  const valueOf = el => {
    const tag = (el.tagName || '').toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input') {
      if (type === 'checkbox' || type === 'radio' || type === 'file' || BUTTON_INPUTS.includes(type)) return '';
      return type === 'password' ? (el.value ? '(filled)' : '') : String(el.value || '').slice(0, 40);
    }
    if (tag === 'textarea') return String(el.value || '').slice(0, 40);
    if (tag === 'select') { const o = el.options[el.selectedIndex]; return o ? clean(o.text).slice(0, 40) : ''; }
    if (el.isContentEditable) return clean(el.innerText || '').slice(0, 40);
    return '';
  };
  const checkedOf = el => {
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (type === 'checkbox' || type === 'radio') return !!el.checked;
    if (el.hasAttribute('aria-checked')) return el.getAttribute('aria-checked') === 'true';
    return null;
  };
  const disabledOf = el => !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
  // Visible in the sense of "still the thing Jev saw": rendered, with a box, and able to take a pointer
  // (pointer-events: none is how apps park a control while busy; the observer never offers such a node).
  const visibleOf = el => {
    if (!el.isConnected) return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden' && cs.pointerEvents !== 'none';
  };
  // Is `el` (with box r) under another layer? What is on top must be unrelated to it: not the control's own <label>
  // (a styled checkbox) and not a sibling box in its wrapper (a hidden input under its painted box). Returns the
  // element on top (the layer: a loading overlay, a backdrop, an open list) or null.
  const coveredAt = (el, r) => {
    const cx = Math.min(window.innerWidth - 1, Math.max(0, r.left + r.width / 2));
    const cy = Math.min(window.innerHeight - 1, Math.max(0, r.top + r.height / 2));
    const top = document.elementFromPoint(cx, cy);
    if (!top || top === el || el.contains(top) || top.contains(el)) return null;
    const tag = el.tagName.toLowerCase();
    const formControl = tag === 'input' || tag === 'select' || tag === 'textarea';
    const lbl = top.closest('label');
    const sibling = el.parentElement && (top.parentElement === el.parentElement || el.parentElement.contains(top));
    return ((lbl && lbl.control === el) || (formControl && sibling)) ? null : top;
  };
  // How many of the controls the observation found covered (tagged data-jev-covered) are still covered: a loading
  // overlay lifting off a form changes no tagged node and no text, but it is the change a WAIT on such a page waits for.
  // An option that is a loading placeholder ('Searching....', 'Loading...'): a server-side autocomplete's row while
  // its suggestions are on their way. Not a choice: counted (loading_options), not offered, and a busy signal for the
  // loop (run_test.page_loading). Live: Jev clicked Search over a 'Searching....' row at 0.66-0.70, two runs of nine.
  const LOADING_OPTION = /^(searching|loading|please wait|fetching|one moment)\b[\s.…]*$/i;
  const loadingOption = (el) => (el.getAttribute('role') === 'option' || el.tagName.toLowerCase() === 'option')
    && LOADING_OPTION.test(clean(el.innerText || el.textContent).slice(0, 40));
  const loadingNow = () => {
    let n = 0;
    for (const el of document.querySelectorAll('[role="option"]')) {
      if (!el.isConnected || !loadingOption(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width >= 2 && r.height >= 2) n++;
    }
    return n;
  };
  const coveredNow = () => {
    let n = 0;
    for (const el of document.querySelectorAll('[data-jev-covered]')) {
      if (!el.isConnected) continue;
      const r = el.getBoundingClientRect();
      if (r.width >= 2 && r.height >= 2 && coveredAt(el, r)) n++;
    }
    return n;
  };
  // [connected, visible, value, checked, disabled, hash of the surrounding form/dialog/row/item text].
  // A <label> offered for its offscreen checkbox stands for the control: value/checked/disabled are read
  // from the control, so the box being checked or disabled during the decision makes the label stale.
  const nodeTuple = el => {
    const c = (el.tagName === 'LABEL' && el.control) ? el.control : el;
    return [el.isConnected, visibleOf(el), valueOf(c), checkedOf(c), disabledOf(c),
            strHash(clean(scopeOf(el).innerText || '').slice(0, 2000))];
  };
  // Viewport-first visible text: text nodes that intersect the viewport in document order, then the rest,
  // cut to maxChars. body.innerText from the top let 2,000 chars of header and navigation crowd out the
  // toast the checks were looking for. visibleText(n) is a prefix of visibleText(m) for n <= m: inLen is
  // the exact length of the joined in-view text, so the walk stops only once the head alone fills the cut.
  const visibleText = maxChars => {
    if (!document.body) return '';
    const inView = [], rest = [];
    let inLen = 0;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    let node;
    while (inLen < maxChars && (node = walker.nextNode())) {
      const raw = node.textContent;
      if (!raw || !raw.trim()) continue;
      const parent = node.parentElement;
      if (!parent || parent.closest('script, style, noscript, template')) continue;
      if (parent.checkVisibility && !parent.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
      // Text directly inside a closed <details> (outside its <summary>) is not shown, although its parent is.
      const details = parent.closest('details');
      if (details && !details.open) { const s = parent.closest('summary'); if (!s || s.parentElement !== details) continue; }
      range.selectNodeContents(node);
      const r = range.getBoundingClientRect();
      if (r.width <= 0 && r.height <= 0) continue;
      const value = clean(raw);
      if (r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth) {
        inLen += value.length + (inView.length ? 1 : 0);
        inView.push(value);
      } else rest.push(value);
    }
    const head = inView.join(' ');
    if (head.length >= maxChars) return head.slice(0, maxChars);
    return (head + ' ' + rest.join(' ')).trim().slice(0, maxChars);
  };
"""

OBSERVE_JS = "(args) => {\n" + JS_HELPERS + r"""
  // wholeDocument: the assertion oracle (run_test.check_assertions). Every rendered control on the page,
  // wherever it sits, with no viewport or hit-test gates and no cursor:pointer scan, and without touching
  // the numbering Jev saw. The default is the table Jev chooses from: viewport, hit-tested, cursor scan.
  const { maxElements, maxTextChars, wholeDocument } = args;
  if (!wholeDocument) document.querySelectorAll('[data-jev-idx], [data-jev-covered]').forEach(e => {
    e.removeAttribute('data-jev-idx'); e.removeAttribute('data-jev-covered'); });
  const SEL = [
    'a[href]', 'button', 'input', 'select', 'textarea', 'summary',
    '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[role="menuitemcheckbox"]',
    '[role="menuitemradio"]', '[role="option"]', '[role="checkbox"]', '[role="radio"]', '[role="switch"]',
    '[role="combobox"]', '[role="textbox"]', '[role="searchbox"]', '[contenteditable="true"]', '[onclick]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');
  const vw = window.innerWidth, vh = window.innerHeight;
  const candidates = [];
  const seen = new Set();
  let covered = 0;  // controls on screen but under another layer (overlay, dialog, banner): counted, not offered
  const coveredEls = [];  // those controls, tagged data-jev-covered so the fingerprint can tell when they come free
  const coverers = [];  // the layers found on top of them (a loading overlay, a backdrop, an open list), each once
  let loadingOptions = 0;  // autocomplete rows that only say the suggestions are loading: counted, not offered
  const BELOW_MAX = 12;  // form controls and buttons below the first screen that are offered all the same (marked below)
  let below = 0;

  // A field with no accessible name whose <label> sits beside it in a wrapper, with no for/id linking the two
  // (OrangeHRM's oxd-input-group, many React form kits): the nearest ancestor holding exactly this one control
  // and a <label> names it. Live, a filter box reached Jev as `textbox ""` next to a named sidebar Search box,
  // and the username went into the sidebar. One label over two controls (a date range) names neither, and the
  // climb stops at a form, fieldset, table, list or dialog, which hold many fields.
  const FIELDS = 'input:not([type="hidden"]), select, textarea, [contenteditable="true"], [role="textbox"], [role="combobox"], [role="searchbox"]';
  const groupLabel = el => {
    let g = el.parentElement;
    for (let depth = 0; g && g !== document.body && depth < 5; depth++, g = g.parentElement) {
      if (g.matches('form, fieldset, table, ul, ol, dialog, [role="dialog"]')) return '';
      const n = g.querySelectorAll(FIELDS).length;
      if (n > 1) return '';
      const lab = g.querySelector('label');
      if (lab && n === 1) return clean(lab.innerText).slice(0, 80);
    }
    return '';
  };

  // An icon-only control (a calendar glyph beside a date field, a magnifier) has no text and no label; its class names
  // say what it is: bi-calendar, fa-search, mdi-close, oxd-date-input-icon -> "calendar icon", "date input icon". The
  // first class token, on the element or its first children, that yields a word. Live: an unnamed `clickable ""` beside
  // Date of Application took the click meant for a Save that was not on screen, and the trace alone said what it was.
  const ICON_SKIP = new Set(['icon', 'icons', 'svg', 'inline', 'fw', 'lg', 'sm', 'xs', 'xl', '2x', 'solid', 'regular', 'light', 'brands', 'outlined', 'round', 'sharp']);
  const ICON_RE = /^(?:bi|fa[srlbd]?|mdi|ri|pi|ti|icon|oxd|lucide|glyphicon|material-icons)-(.+)$/;
  const iconName = el => {
    for (const n of [el, ...Array.from(el.children).slice(0, 2)]) {
      const cls = typeof n.className === 'string' ? n.className : (n.getAttribute('class') || '');
      for (const tok of cls.split(/\s+/)) {
        const m = ICON_RE.exec(tok);
        if (!m) continue;
        const w = m[1].replace(/-?icon$/, '').replace(/^icon-?/, '').replace(/-/g, ' ').trim();
        if (w && !ICON_SKIP.has(w)) return (w + ' icon').slice(0, 40);
      }
    }
    return '';
  };

  // Returns true if the element was accepted into the table.
  const describe = (el, via) => {
    if (seen.has(el)) return false;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && type === 'hidden') return false;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (!wholeDocument && (r.bottom < 0 || r.right < 0 || r.left > vw)) return false;  // above or beside the screen: not offered
    const cs = getComputedStyle(el);
    const formControl = tag === 'input' || tag === 'select' || tag === 'textarea';
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.pointerEvents === 'none') return false;
    // Below the first screen: a form control or a button is offered all the same, marked `below`, with no hit test (nothing
    // can cover what is not on screen; the click scrolls it into view). Links and plain clickables stay out: a long
    // article's links would flood the table. Live: an Add Candidate form's Save sat at y=849 of an 800 px viewport and was
    // never offered, so Jev clicked the calendar icon beside the date field instead and stalled in its popup.
    let isBelow = false;
    if (!wholeDocument && r.top >= vh) {
      const buttonLike = tag === 'button' || el.getAttribute('role') === 'button';
      if (via !== 'semantic' || !(formControl || buttonLike) || below >= BELOW_MAX) return false;
      isBelow = true; below++;
    }
    // opacity:0 on a form control with a real box is the "hidden input behind a styled box" pattern
    // (antd/MUI/Bootstrap checkboxes, file inputs under an Upload button) -> still the thing to click.
    if (cs.opacity === '0' && !formControl) return false;
    const top = (wholeDocument || isBelow) ? null : coveredAt(el, r);
    if (top) {
      // covered by something else (modal, banner, overlay) -> a human could not click it either
      if (via !== 'cursor') { covered++; coveredEls.push(el); if (!coverers.includes(top)) coverers.push(top); }
      return false;
    }
    let role = el.getAttribute('role');
    if (!role) {
      if (tag === 'a') role = 'link';
      else if (tag === 'button') role = 'button';
      else if (tag === 'select') role = 'select';
      else if (tag === 'textarea') role = 'textbox';
      else if (tag === 'summary') role = 'button';
      else if (tag === 'input') {
        if (['checkbox','radio','submit','button','file','range','reset','image'].includes(type)) role = type;
        else if (type === 'search') role = 'searchbox';        // the implicit ARIA role of <input type=search>
        else if (el.hasAttribute('list')) role = 'combobox';    // <input list=...>: datalist suggestions
        else role = 'textbox';
      }
      else if (el.isContentEditable) role = 'textbox';
      else role = 'clickable';
    }
    // A field's content is its value, never its caption: text is read only from non-editable elements, so a
    // typed value cannot become a field's label, and a textarea's initial markup is not a second value.
    const editable = formControl || el.isContentEditable;
    const text = editable ? '' : clean(el.innerText || el.textContent).slice(0, 80);
    if (role === 'option' && LOADING_OPTION.test(text.slice(0, 40))) { loadingOptions++; seen.add(el); return false; }
    let labelText = '';
    if (el.labels && el.labels.length) labelText = clean(el.labels[0].innerText);
    if (!labelText) {  // aria-labelledby: the named elements' text, in order
      const by = el.getAttribute('aria-labelledby');
      if (by) labelText = clean(by.split(/\s+/).map(id => (document.getElementById(id) || {}).innerText || '').join(' '));
    }
    const caption = tag === 'input' && BUTTON_INPUTS.includes(type) ? el.value : '';
    let name = clean(
      el.getAttribute('aria-label') || labelText || el.getAttribute('placeholder') ||
      el.getAttribute('title') || el.getAttribute('alt') || caption || text || ''
    ).slice(0, 80);
    if (!name && editable) name = groupLabel(el);  // a label beside the field beats its machine identifiers
    if (!name) name = iconName(el);  // an icon-only control, named from its icon class
    if (!name) name = clean(el.getAttribute('name') || el.id || '').slice(0, 80);
    let context;
    if (!name || (role === 'checkbox' || role === 'radio' || role === 'switch')) {
      let h = el.parentElement;
      while (h && h !== document.body) {
        if (h.matches('tr, [role="row"], li, [role="listitem"], label, [role="option"]')) {
          const ctx = clean(h.innerText).slice(0, 70);
          if (ctx && ctx !== name) { context = ctx; break; }
        }
        h = h.parentElement;
      }
    }
    const value = valueOf(el) || undefined;  // the same function the fingerprint uses
    let options;
    if (tag === 'select') {
      // an option inside a disabled <optgroup> is not selectable although its own .disabled is false
      options = Array.from(el.options).slice(0, 40).map((o, i) => ({
        i, text: clean(o.text).slice(0, 50), disabled: !!(o.disabled || o.closest('optgroup[disabled]')) }));
    }
    let checked;
    if (type === 'checkbox' || type === 'radio') checked = !!el.checked;
    else if (el.hasAttribute('aria-checked')) checked = el.getAttribute('aria-checked') === 'true';
    const disabled = !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
    seen.add(el);
    candidates.push({
      el, role, tag, type: type || undefined, name, text: text && text !== name ? text : undefined,
      value, options, checked, via, context,
      href: tag === 'a' ? (el.getAttribute('href') || '').slice(0, 80) : undefined,
      // a native <datalist> shows its suggestions in browser UI, never as [role=option] nodes, so the
      // settle must not wait for one (run_test.settle)
      datalist: tag === 'input' && el.hasAttribute('list') ? true : undefined,
      disabled, below: isBelow || undefined,
      x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)
    });
    return true;
  };

  // Pass 1: semantic controls (tags, ARIA roles, explicit handlers). The assertion oracle also takes every
  // element with an explicit role (alert, status, dialog, heading, ...): not actionable, but assertable.
  for (const el of document.querySelectorAll(wholeDocument ? SEL + ',[role]' : SEL)) describe(el, 'semantic');

  // Pass 2: a <label> whose checkbox/radio is parked offscreen (clip/left:-9999px) is the only thing
  // a human can click for it. Offer the label, described as the control.
  for (const lbl of document.querySelectorAll('label')) {
    const c = lbl.control;
    if (!c || seen.has(c) || seen.has(lbl)) continue;
    const t = (c.getAttribute('type') || '').toLowerCase();
    if (!(t === 'checkbox' || t === 'radio')) continue;
    if (describe(lbl, 'label')) {
      const d = candidates[candidates.length - 1];
      d.role = t; d.checked = !!c.checked; d.disabled = !!c.disabled;
    }
  }

  // Pass 3: non-semantic clickables. Frameworks like React attach handlers by delegation, so a
  // clickable <div> (an avatar menu, a card, a table row) has no role, no tabindex and no onclick
  // attribute -- the only visible hint is `cursor: pointer`. Because `cursor` is inherited, keep the
  // OUTERMOST element of each pointer chain, and skip anything nested inside a pass-1 control.
  if (document.body && !wholeDocument) {
    let scanned = 0;
    for (const el of document.body.querySelectorAll('*')) {
      if (++scanned > 8000) break;
      if (el.ownerSVGElement) continue;                 // svg internals: the <svg> root is enough
      const tag = el.tagName.toLowerCase();
      if (tag === 'script' || tag === 'style' || tag === 'template' || tag === 'noscript') continue;
      if (el.matches(SEL)) continue;                    // already considered in pass 1
      // A <label> whose control is already in the table adds nothing but a tempting no-op click
      // (measured: Jev clicked "Username" before typing into it). Pass 2 keeps labels of hidden controls.
      if (tag === 'label' && el.control && seen.has(el.control)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
      if (getComputedStyle(el).cursor !== 'pointer') continue;
      const p = el.parentElement;
      if (p && p !== document.body && getComputedStyle(p).cursor === 'pointer') continue;  // not outermost
      if (p && p.closest(SEL)) continue;                // inside a real control (span inside button)
      // A pointer wrapper around exactly one offered control with no text of its own (OrangeHRM's topbar tabs: an <li>
      // with cursor:pointer around an <a> of the same caption) is that control twice; a click on the control bubbles
      // to the wrapper anyway. Live, every tab reached Jev as `clickable` and as `link` and split its choice 0.57 / 0.25.
      const inner = el.querySelectorAll(SEL);
      if (inner.length === 1 && seen.has(inner[0]) && clean(el.innerText || '') === clean(inner[0].innerText || '')) continue;
      describe(el, 'cursor');
    }
  }
  candidates.sort((a, b) => (a.y - b.y) || (a.x - b.x));
  // the below-the-fold controls ride on top of the table's budget (at most BELOW_MAX of them), so a long page's cap
  // cuts the elements Jev cannot see anyway rather than the Save at the bottom of its form
  const inView = candidates.filter(c => !c.below), belowFold = candidates.filter(c => c.below);
  const kept = inView.slice(0, maxElements).concat(belowFold.slice(0, BELOW_MAX));

  // Pass 4: identical labels. A product grid has one "Add to cart" per card, a list one "Edit" per entry,
  // and when the cards are plain <div>s no row/list-item context is attached above, so Jev sees the same
  // label N times and can only guess from the order (measured on a six-card grid: 0.47 / 0.21 / 0.18 over
  // three of the six, refused three times, low_confidence). For each group of elements sharing role + name
  // without a context, climb the ancestors level by level, strictly below the group's lowest common
  // ancestor (the grid itself, or the card when the group is one product's image and title buttons), and
  // keep the HIGHEST level whose texts are non-empty and tell every member apart: a price bar is distinct
  // but says nothing, the card with its title does. A group that nothing distinguishes gets no context.
  const groups = new Map();
  for (const c of kept) {
    if (!c.name || c.context) continue;
    const k = c.role + '\u0000' + c.name;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(c);
  }
  for (const group of groups.values()) {
    if (group.length < 2) continue;
    let lca = group[0].el.parentElement;
    for (const c of group) while (lca && !lca.contains(c.el)) lca = lca.parentElement;
    let best = null;
    let anc = group.map(c => c.el.parentElement);
    for (let level = 0; level < 8; level++) {
      if (anc.some(a => !a || a === lca || a === document.body)) break;   // at the common container nothing tells them apart
      if (new Set(anc).size === anc.length) {
        const texts = anc.map((a, i) => { const t = clean(a.innerText).slice(0, 70); return t === group[i].name ? '' : t; });
        if (texts.every(t => t) && new Set(texts).size === texts.length) best = texts;
      }
      anc = anc.map(a => a.parentElement);
    }
    if (best) group.forEach((c, i) => { c.context = best[i]; });
  }
  // The layers' own controls among the offered ones: inside a layer, around it, or within its box (a dialog's buttons
  // over a backdrop, an open list's options, a banner's Accept over a page shade). A layer with none is blank: a
  // loading or saving overlay, and the page is on its way (run_test.blank_layer). Live: a form's loader left the
  // sidebar's filter as the one free field, and a dialog's Ok was the one thing to click; the count tells them apart.
  const within = (el, layer) => {
    const b = layer.getBoundingClientRect(), r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    return cx >= b.left && cx <= b.right && cy >= b.top && cy <= b.bottom;
  };
  // A control that only shares a layer's box is the layer's own when it lies over the covered region (a dialog's Ok over
  // the form it blocks); one that does not is the app's shell around a loading page (a fixed top bar painted above a
  // full-page loader), and the layer stays blank. Live: a post-Save shell read COVERED:13(layer:5), the five being the
  // top bar's links, so no deferral applied and the next tab was clicked while the save was in flight.
  const coveredBox = coveredEls.reduce((b, el) => { const q = el.getBoundingClientRect();
    return { left: Math.min(b.left, q.left), top: Math.min(b.top, q.top), right: Math.max(b.right, q.right), bottom: Math.max(b.bottom, q.bottom) }; },
    { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity });
  const overCovered = el => { const q = el.getBoundingClientRect();
    return q.right >= coveredBox.left && q.left <= coveredBox.right && q.bottom >= coveredBox.top && q.top <= coveredBox.bottom; };
  const layerControls = coverers.length
    ? kept.filter(c => coverers.some(t => t === c.el || t.contains(c.el))
                    || (coverers.some(t => c.el.contains(t) || within(c.el, t)) && overCovered(c.el))).length : 0;
  const nodes = {};
  kept.forEach((c, i) => {
    if (!wholeDocument) { c.el.setAttribute('data-jev-idx', String(i)); nodes[String(i)] = nodeTuple(c.el); }
    c.idx = i;
    delete c.el;
  });
  if (!wholeDocument) coveredEls.forEach((el, i) => el.setAttribute('data-jev-covered', String(i)));
  return {
    url: location.href,
    title: document.title,
    now: Date.now(),  // the page's clock at this observation: announcements carry the same clock (ms_before_observation)
    elements: kept,
    truncated: candidates.length - kept.length,
    covered,
    layer_controls: layerControls,  // offered controls that belong to the covering layers; 0 with covered > 0 is a blank layer
    loading_options: loadingOptions,  // autocomplete rows that only say 'Searching....' / 'Loading...': not offered, the suggestions are on their way
    visible_text: visibleText(maxTextChars),
    fingerprint: { url: location.href, title: document.title, text_head: visibleText(500), nodes, covered, loading: loadingOptions },
    scroll: {
      y: Math.round(window.scrollY),
      viewport: vh,
      height: Math.round(Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0))
    }
  };
}
"""

# The terminal page as the lines a human would quote from, for the adjudication request (spec §5.4): the
# visible text, grouped by block (a paragraph, a cell, a list item, a toast), with the lines that intersect the
# viewport FIRST, then the rest, the same visibility rules as visibleText, cut to maxLines. body.innerText from
# the top would let 200 lines of navigation and table rows crowd out the flash message at the bottom.
LINES_JS = "(maxLines) => {\n" + JS_HELPERS + r"""
  if (!document.body) return [];
  const INLINE = new Set(['inline', 'inline-block', 'inline-flex', 'inline-grid', 'contents', 'ruby']);
  const blockOf = el => {
    let e = el;
    while (e && e !== document.body) { if (!INLINE.has(getComputedStyle(e).display)) return e; e = e.parentElement; }
    return document.body;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  const inView = [], rest = [];
  let node, cur = null, parts = [], seenInView = false;
  const flush = () => {
    const t = parts.join(' ').trim();
    if (t) (seenInView ? inView : rest).push(t);
    parts = []; seenInView = false;
  };
  while ((node = walker.nextNode())) {
    const raw = node.textContent;
    if (!raw || !raw.trim()) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('script, style, noscript, template')) continue;
    if (parent.checkVisibility && !parent.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const details = parent.closest('details');
    if (details && !details.open) { const s = parent.closest('summary'); if (!s || s.parentElement !== details) continue; }
    range.selectNodeContents(node);
    const r = range.getBoundingClientRect();
    if (r.width <= 0 && r.height <= 0) continue;
    const b = blockOf(parent);
    if (b !== cur) { flush(); cur = b; }
    parts.push(clean(raw));
    if (r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth) seenInView = true;
  }
  flush();
  return inView.concat(rest).slice(0, maxLines);
}
"""

# Announcements: toasts and ARIA live messages that appear between two observations. A toast that fades before the
# next observation is otherwise lost, and Jev then guesses from history; live, a Leave flow's decisive facts
# ("Successfully Saved", "Failed to Submit: No Working Days Selected") were such toasts. This init script (installed
# on the browser context, so it runs in every document before the page's own scripts, and survives navigations) watches
# the DOM and reports each new message once to the runner through the function the runner exposes as ANNOUNCE_FUNCTION.
# A message is the text of the nearest live region around an added or changed node: [role=alert|status|log] or
# aria-live polite|assertive (kind = the role, or "live"), else the nearest element whose class names a toast, snackbar,
# growl or flash (kind "toast"; OrangeHRM's .oxd-toast carries aria-live=assertive and reads as "live"). A hidden
# alert that is shown (an attribute change on the region) is reported too. `tone` is the success / error / warning /
# info word in the region's class names when there is one ("oxd-toast--success", "alert-danger"). The same text within
# 3 s is one message (a toast mutates as it animates). Nothing here reaches Jev directly: the runner masks secrets,
# attaches the messages to the step, the state and the history, and quotes them in the evidence lines.
ANNOUNCE_FUNCTION = "__jevAnnounce"
ANNOUNCE_INIT_JS = r"""
(() => {
  if (window.__jevAnnounceInstalled) return;
  window.__jevAnnounceInstalled = true;
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const LIVE = '[role="alert"], [role="status"], [role="log"], [aria-live="polite"], [aria-live="assertive"]';
  const TOASTY = '[class*="toast" i], [class*="snackbar" i], [class*="growl" i], [class*="flash" i]';
  const recent = new Map();  // text -> when it was last reported
  const kindOf = el => {
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (role === 'alert' || role === 'status' || role === 'log') return role;
    const live = (el.getAttribute('aria-live') || '').toLowerCase();
    return (live === 'polite' || live === 'assertive') ? 'live' : 'toast';
  };
  const toneOf = el => {
    const m = /(success|error|danger|warning|warn|info)/i.exec(String(el.className || ''));
    if (!m) return undefined;
    const w = m[1].toLowerCase();
    return w === 'danger' ? 'error' : w === 'warn' ? 'warning' : w;
  };
  const shown = el => !el.checkVisibility || el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
  const regionOf = node => {
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el || !el.closest) return null;
    return el.closest(LIVE) || el.closest(TOASTY);
  };
  const report = region => {
    if (!region.isConnected || !shown(region)) return false;
    const text = clean(region.innerText || region.textContent).replace(/\s*[×✕✖⨯]+\s*$/, '').slice(0, 300);  // minus the close button
    if (!text) return false;
    const now = Date.now();
    const last = recent.get(text);
    if (last !== undefined && now - last < 3000) return true;
    recent.set(text, now);
    if (recent.size > 50) recent.delete(recent.keys().next().value);
    const entry = { t: now, kind: kindOf(region), text };
    const tone = toneOf(region);
    if (tone) entry.tone = tone;
    try { window.__ANNOUNCE__(JSON.stringify(entry)); } catch (e) { /* the runner is not listening (a page outside a run) */ }
    return true;
  };
  const consider = node => {
    const region = regionOf(node);
    if (region) { if (!report(region)) setTimeout(() => report(region), 120); return; }  // text may be filled in after insertion
    if (node.nodeType === 1 && node.querySelectorAll) for (const r of node.querySelectorAll(LIVE + ', ' + TOASTY)) consider(r);
  };
  const mo = new MutationObserver(muts => {
    for (const m of muts) {
      if (m.type === 'childList') { for (const n of m.addedNodes) consider(n); }
      else if (m.type === 'characterData') consider(m.target);
      else if (m.target.nodeType === 1 && m.target.matches(LIVE + ', ' + TOASTY)) consider(m.target);  // a hidden alert shown
    }
  });
  mo.observe(document, { subtree: true, childList: true, characterData: true, attributes: true,
                         attributeFilter: ['hidden', 'style', 'class', 'aria-hidden', 'open'] });
})();
""".replace("__ANNOUNCE__", ANNOUNCE_FUNCTION)

# Cheap re-read of what the observation recorded, without re-tagging: the nodes still carry data-jev-idx.
FINGERPRINT_JS = "() => {\n" + JS_HELPERS + r"""
  const nodes = {};
  for (const el of document.querySelectorAll('[data-jev-idx]')) nodes[el.getAttribute('data-jev-idx')] = nodeTuple(el);
  return { url: location.href, title: document.title, text_head: visibleText(500), nodes, covered: coveredNow(), loading: loadingNow() };
}
"""

TUPLE_FIELDS = ("connected", "visible", "value", "checked", "disabled", "context")
GUARD_SKIPPED = {"SCROLL_DOWN", "SCROLL_UP", "WAIT"}
TARGET_OPERATIONS = {"CLICK", "TYPE_TEXT", "SELECT"}


def observe(page, max_elements: int = 200, max_text_chars: int = 4000, whole_document: bool = False) -> dict:
    """Run the observation script on the current page and return the observation dict.

    Besides the element table it carries `fingerprint`: url, title, the first 500 chars of visible text and
    one identity/meaning tuple per tagged node, which `fingerprint()` + `compare_fingerprint()` check again
    right before acting. `whole_document=True` is the assertion oracle (run_test.check_assertions): every
    rendered control on the page, not only what is in the viewport and under the pointer, and the nodes
    Jev saw keep their numbering.
    """
    obs = page.evaluate(OBSERVE_JS, {"maxElements": max_elements, "maxTextChars": max_text_chars,
                                     "wholeDocument": whole_document})
    s = obs["scroll"]
    obs["can_scroll_down"] = s["y"] + s["viewport"] < s["height"] - 8
    obs["can_scroll_up"] = s["y"] > 8
    return obs


MASK = "<secret>"
OBSERVED_CUTS = (40, 50, 70, 80)  # the observer cuts value / option text / context / name+text at these lengths
MASK_TAIL_MIN = 8  # a string ending in at least this many leading chars of a secret was cut mid-secret


def make_scrubber(values: list[str]):
    """The masking function for one run, or None when there is nothing to mask.

    `scrub(s)` replaces every secret in `values`, and every observer-truncated prefix of it, with MASK. A
    string that ENDS in at least MASK_TAIL_MIN leading chars of a secret was cut mid-secret by some other
    truncation (visible_text at max_text_chars, a context or option cut at an offset); that tail is masked
    too. Empty values are ignored."""
    secrets = [v for v in values if v]
    if not secrets:
        return None
    needles: list[str] = []
    for v in secrets:
        needles.append(v)
        needles.extend(v[:cut] for cut in OBSERVED_CUTS if len(v) > cut)
    needles.sort(key=len, reverse=True)  # longest first, so a prefix never pre-empts the full value

    def scrub(s):
        if not isinstance(s, str) or not s:
            return s
        for v in secrets:  # a cut tail first: once a prefix needle has eaten its head, the rest is unrecognisable
            for k in range(min(len(s), len(v) - 1), MASK_TAIL_MIN - 1, -1):
                if s.endswith(v[:k]):
                    s = s[:-k] + MASK
                    break
        for n in needles:
            if n in s:
                s = s.replace(n, MASK)
        return s

    return scrub


def mask_text(s, values: list[str]):
    """`s` with every secret in `values` masked (see make_scrubber): for page text the runner reads outside
    an observation, such as the adjudication lines, an assertion's excerpt, the final page's title and url."""
    scrub = make_scrubber(values)
    return scrub(s) if scrub else s


def mask_secrets(obs: dict, values: list[str]) -> dict:
    """Replace every secret value (and its observer-truncated prefixes) in what Jev and the trace get to see.

    The observer reads fields back after they were typed into, so a secret typed into anything but a
    password field returns as an element's `value` (and, for a contenteditable, its text), from where it
    would reach the state, the target criteria, the trace and `recent_actions`; a GET form or a router puts
    it in the url and in hrefs, an app may echo it in the title. Masking here, in Python and right after the
    observation, closes every one of those channels at once. `fingerprint` is left alone: it is compared in
    Python only and never sent or written. Empty values are ignored."""
    scrub = make_scrubber(values)
    if scrub is None:
        return obs
    for e in obs.get("elements") or []:
        for key in ("name", "text", "value", "context", "href"):
            if e.get(key):
                e[key] = scrub(e[key])
        for o in e.get("options") or []:
            o["text"] = scrub(o.get("text"))
    obs["visible_text"] = scrub(obs.get("visible_text") or "")
    obs["title"] = scrub(obs.get("title") or "")
    obs["url"] = scrub(obs.get("url") or "")
    return obs


def fingerprint(page) -> dict:
    """The current identity/meaning fingerprint of the tagged nodes (same functions as observe())."""
    return page.evaluate(FINGERPRINT_JS)


def _tuple_diff(before: list, after: list) -> str | None:
    for name, b, a in zip(TUPLE_FIELDS, before, after):
        if b != a:
            return name
    return None if len(before) == len(after) else "shape"


def compare_fingerprint(before: dict, after: dict, operation: str, target_idx=None) -> str | None:
    """Why the page no longer means what Jev saw, or None if the decision can be executed.

    Scroll and WAIT never go stale. CLICK / TYPE_TEXT / SELECT compare the url and only the target node's
    tuple: unrelated content may change (a clock, a notification count) without invalidating a click on a
    still-identical control. DONE / BLOCKED / PRESS_ENTER and anything else compare url, title, the text head,
    how many of the observation's covered controls are still covered (a loading overlay lifting off a form is
    the change a WAIT on such a page is waiting for, and it moves no tagged node) and every node tuple, because
    those decisions are about the whole page. `wait_for_change` uses this whole-page form.
    """
    if operation in GUARD_SKIPPED:
        return None
    if before.get("url") != after.get("url"):
        return "url changed"
    b_nodes, a_nodes = before.get("nodes") or {}, after.get("nodes") or {}
    if operation in TARGET_OPERATIONS:
        key = str(target_idx)
        if key not in b_nodes:
            return f"target [{key}] was not in the observation"
        if key not in a_nodes:
            return f"target [{key}] is no longer on the page"
        diff = _tuple_diff(b_nodes[key], a_nodes[key])
        return f"target [{key}] changed: {diff}" if diff else None
    if before.get("title") != after.get("title"):
        return "title changed"
    if before.get("text_head") != after.get("text_head"):
        return "visible text changed"
    if before.get("covered") is not None and after.get("covered") is not None and before["covered"] != after["covered"]:
        # a loading overlay lifted off a form (or a dialog closed): nothing tagged changed, the page did
        return f"covered controls changed: {before['covered']} -> {after['covered']}"
    if before.get("loading") is not None and after.get("loading") is not None and before["loading"] != after["loading"]:
        # an autocomplete's placeholder row giving way to its suggestions (or appearing): the change a wait on such a page waits for
        return f"loading options changed: {before['loading']} -> {after['loading']}"
    for key, tup in b_nodes.items():
        if key not in a_nodes:
            return f"element [{key}] is no longer on the page"
        diff = _tuple_diff(tup, a_nodes[key])
        if diff:
            return f"element [{key}] changed: {diff}"
    extra = [k for k in a_nodes if k not in b_nodes]
    if extra:
        return f"element [{extra[0]}] appeared"
    return None


def element_label(e: dict) -> str:
    """One-line description of an element: the `label` a chosen target gets in the trace and in Jev's
    `recent_actions`, and the row format `render_table` hashes into the page signature. (The state sends
    elements as records and the target questions offer objects; see policy.describe_element and
    policy.target_criterion.)"""
    parts = [e["role"], f'"{e["name"]}"' if e.get("name") else '""']
    if e.get("text"):
        parts.append(f'text="{e["text"]}"')
    if e.get("context"):
        parts.append(f'in "{e["context"]}"')
    if e.get("value"):
        parts.append(f'value="{e["value"]}"')
    if e.get("checked") is not None and e["role"] in ("checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"):
        parts.append("checked" if e["checked"] else "unchecked")
    if e.get("disabled"):
        parts.append("DISABLED")
    if e.get("below"):
        parts.append("(below the fold)")  # offered although below the first screen; the click scrolls to it
    return " ".join(parts)


def render_table(obs: dict) -> str:
    lines = [f"[{e['idx']}] {element_label(e)}" for e in obs["elements"]]
    if obs.get("truncated"):
        lines.append(f"... {obs['truncated']} more interactive elements not shown (scroll to reveal)")
    if obs.get("covered"):
        lines.append(f"... {obs['covered']} controls on screen are under another layer (overlay, dialog, banner) and not offered")
    if not lines:
        lines.append("(no interactive elements visible)")
    return "\n".join(lines)


def signature(obs: dict) -> str:
    """Stable fingerprint of what the page currently shows (used for loop detection)."""
    h = hashlib.sha1()
    h.update(obs["url"].encode())
    h.update(obs["title"].encode())
    h.update(render_table(obs).encode())
    h.update(obs["visible_text"][:500].encode())
    return h.hexdigest()[:12]
