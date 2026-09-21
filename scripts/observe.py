"""Turn the live page into a numbered element table Jev can choose from.

Every step produces a *fresh* table (indices are not stable across steps). Each
included element is tagged with `data-jev-idx="<n>"` so the runner can act on it
with a plain Playwright locator. Only the main frame is observed.
"""
from __future__ import annotations

import hashlib

OBSERVE_JS = r"""
(args) => {
  const { maxElements, maxTextChars } = args;
  document.querySelectorAll('[data-jev-idx]').forEach(e => e.removeAttribute('data-jev-idx'));
  const SEL = [
    'a[href]', 'button', 'input', 'select', 'textarea', 'summary',
    '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[role="menuitemcheckbox"]',
    '[role="menuitemradio"]', '[role="option"]', '[role="checkbox"]', '[role="radio"]', '[role="switch"]',
    '[role="combobox"]', '[role="textbox"]', '[role="searchbox"]', '[contenteditable="true"]', '[onclick]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');
  const vw = window.innerWidth, vh = window.innerHeight;
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const candidates = [];
  const seen = new Set();

  // Returns true if the element was accepted into the table.
  const describe = (el, via) => {
    if (seen.has(el)) return false;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && type === 'hidden') return false;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0' || cs.pointerEvents === 'none') return false;
    const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2));
    const cy = Math.min(vh - 1, Math.max(0, r.top + r.height / 2));
    const top = document.elementFromPoint(cx, cy);
    if (top && top !== el && !el.contains(top) && !top.contains(el)) {
      // covered by something else (modal, banner, overlay) -> a human could not click it either
      const lbl = top.closest('label');
      if (!(lbl && lbl.control === el)) return false;
    }
    let role = el.getAttribute('role');
    if (!role) {
      if (tag === 'a') role = 'link';
      else if (tag === 'button') role = 'button';
      else if (tag === 'select') role = 'select';
      else if (tag === 'textarea') role = 'textbox';
      else if (tag === 'summary') role = 'button';
      else if (tag === 'input') role = ['checkbox','radio','submit','button','file','range','reset','image'].includes(type) ? type : 'textbox';
      else if (el.isContentEditable) role = 'textbox';
      else role = 'clickable';
    }
    const text = clean(el.innerText || el.textContent).slice(0, 80);
    let labelText = '';
    if (el.labels && el.labels.length) labelText = clean(el.labels[0].innerText);
    const name = clean(
      el.getAttribute('aria-label') || labelText || el.getAttribute('placeholder') ||
      el.getAttribute('title') || el.getAttribute('alt') || (tag === 'input' && type === 'submit' ? el.value : '') ||
      text || el.getAttribute('name') || el.id || ''
    ).slice(0, 80);
    let value;
    if (tag === 'input' || tag === 'textarea') {
      value = type === 'password' ? (el.value ? '(filled)' : '') : String(el.value || '').slice(0, 40);
    } else if (tag === 'select') {
      const o = el.options[el.selectedIndex];
      value = o ? clean(o.text).slice(0, 40) : '';
    }
    let options;
    if (tag === 'select') {
      options = Array.from(el.options).slice(0, 40).map((o, i) => ({ i, text: clean(o.text).slice(0, 50), disabled: !!o.disabled }));
    }
    let checked;
    if (type === 'checkbox' || type === 'radio') checked = !!el.checked;
    else if (el.hasAttribute('aria-checked')) checked = el.getAttribute('aria-checked') === 'true';
    const disabled = !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
    seen.add(el);
    candidates.push({
      el, role, tag, type: type || undefined, name, text: text && text !== name ? text : undefined,
      value: value || undefined, options, checked, via,
      href: tag === 'a' ? (el.getAttribute('href') || '').slice(0, 80) : undefined,
      disabled, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)
    });
    return true;
  };

  // Pass 1: semantic controls (tags, ARIA roles, explicit handlers).
  for (const el of document.querySelectorAll(SEL)) describe(el, 'semantic');

  // Pass 2: non-semantic clickables. Frameworks like React attach handlers by delegation, so a
  // clickable <div> (an avatar menu, a card, a table row) has no role, no tabindex and no onclick
  // attribute -- the only visible hint is `cursor: pointer`. Because `cursor` is inherited, keep the
  // OUTERMOST element of each pointer chain, and skip anything nested inside a pass-1 control.
  if (document.body) {
    let scanned = 0;
    for (const el of document.body.querySelectorAll('*')) {
      if (++scanned > 8000) break;
      if (el.ownerSVGElement) continue;                 // svg internals: the <svg> root is enough
      const tag = el.tagName.toLowerCase();
      if (tag === 'script' || tag === 'style' || tag === 'template' || tag === 'noscript') continue;
      if (el.matches(SEL)) continue;                    // already considered in pass 1
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
      if (getComputedStyle(el).cursor !== 'pointer') continue;
      const p = el.parentElement;
      if (p && p !== document.body && getComputedStyle(p).cursor === 'pointer') continue;  // not outermost
      if (p && p.closest(SEL)) continue;                // inside a real control (span inside button)
      describe(el, 'cursor');
    }
  }
  candidates.sort((a, b) => (a.y - b.y) || (a.x - b.x));
  const kept = candidates.slice(0, maxElements);
  kept.forEach((c, i) => { c.el.setAttribute('data-jev-idx', String(i)); c.idx = i; delete c.el; });
  const body = document.body ? clean(document.body.innerText) : '';
  return {
    url: location.href,
    title: document.title,
    elements: kept,
    truncated: candidates.length - kept.length,
    visible_text: body.slice(0, maxTextChars),
    scroll: {
      y: Math.round(window.scrollY),
      viewport: vh,
      height: Math.round(Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0))
    }
  };
}
"""


def observe(page, max_elements: int = 60, max_text_chars: int = 2000) -> dict:
    """Run the observation script on the current page and return the observation dict."""
    obs = page.evaluate(OBSERVE_JS, {"maxElements": max_elements, "maxTextChars": max_text_chars})
    s = obs["scroll"]
    obs["can_scroll_down"] = s["y"] + s["viewport"] < s["height"] - 8
    obs["can_scroll_up"] = s["y"] > 8
    return obs


def element_label(e: dict) -> str:
    """One-line description of an element, used both in the state table and as a Choice option."""
    parts = [e["role"], f'"{e["name"]}"' if e.get("name") else '""']
    if e.get("text"):
        parts.append(f'text="{e["text"]}"')
    if e.get("value"):
        parts.append(f'value="{e["value"]}"')
    if e.get("checked") is not None and e["role"] in ("checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"):
        parts.append("checked" if e["checked"] else "unchecked")
    if e.get("disabled"):
        parts.append("DISABLED")
    return " ".join(parts)


def render_table(obs: dict) -> str:
    lines = [f"[{e['idx']}] {element_label(e)}" for e in obs["elements"]]
    if obs.get("truncated"):
        lines.append(f"... {obs['truncated']} more interactive elements not shown (scroll to reveal)")
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
