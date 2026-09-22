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
  const valueOf = el => {
    const tag = (el.tagName || '').toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && type !== 'checkbox' && type !== 'radio') {
      return type === 'password' ? (el.value ? '(filled)' : '') : String(el.value || '').slice(0, 40);
    }
    if (tag === 'textarea') return String(el.value || '').slice(0, 40);
    if (tag === 'select') { const o = el.options[el.selectedIndex]; return o ? clean(o.text).slice(0, 40) : ''; }
    return '';
  };
  const checkedOf = el => {
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (type === 'checkbox' || type === 'radio') return !!el.checked;
    if (el.hasAttribute('aria-checked')) return el.getAttribute('aria-checked') === 'true';
    return null;
  };
  const disabledOf = el => !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
  const visibleOf = el => {
    if (!el.isConnected) return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  };
  // [connected, visible, value, checked, disabled, hash of the surrounding form/dialog/row/item text]
  const nodeTuple = el => [el.isConnected, visibleOf(el), valueOf(el), checkedOf(el), disabledOf(el),
                           strHash(clean(scopeOf(el).innerText || '').slice(0, 2000))];
  const visibleText = maxChars => (document.body ? clean(document.body.innerText) : '').slice(0, maxChars);
"""

OBSERVE_JS = "(args) => {\n" + JS_HELPERS + r"""
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
    const formControl = tag === 'input' || tag === 'select' || tag === 'textarea';
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.pointerEvents === 'none') return false;
    // opacity:0 on a form control with a real box is the "hidden input behind a styled box" pattern
    // (antd/MUI/Bootstrap checkboxes, file inputs under an Upload button) -> still the thing to click.
    if (cs.opacity === '0' && !formControl) return false;
    const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2));
    const cy = Math.min(vh - 1, Math.max(0, r.top + r.height / 2));
    const top = document.elementFromPoint(cx, cy);
    if (top && top !== el && !el.contains(top) && !top.contains(el)) {
      // covered by something else (modal, banner, overlay) -> a human could not click it either,
      // unless what is on top is the control's own styled box: its label, or a sibling in the same wrapper.
      const lbl = top.closest('label');
      const sibling = el.parentElement && (top.parentElement === el.parentElement || el.parentElement.contains(top));
      if (!((lbl && lbl.control === el) || (formControl && sibling))) return false;
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
    let value;
    if ((tag === 'input' && type !== 'checkbox' && type !== 'radio') || tag === 'textarea') {
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
      value: value || undefined, options, checked, via, context,
      href: tag === 'a' ? (el.getAttribute('href') || '').slice(0, 80) : undefined,
      disabled, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)
    });
    return true;
  };

  // Pass 1: semantic controls (tags, ARIA roles, explicit handlers).
  for (const el of document.querySelectorAll(SEL)) describe(el, 'semantic');

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
  const nodes = {};
  kept.forEach((c, i) => {
    c.el.setAttribute('data-jev-idx', String(i));
    c.idx = i;
    nodes[String(i)] = nodeTuple(c.el);
    delete c.el;
  });
  return {
    url: location.href,
    title: document.title,
    elements: kept,
    truncated: candidates.length - kept.length,
    visible_text: visibleText(maxTextChars),
    fingerprint: { url: location.href, title: document.title, text_head: visibleText(500), nodes },
    scroll: {
      y: Math.round(window.scrollY),
      viewport: vh,
      height: Math.round(Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0))
    }
  };
}
"""

# Cheap re-read of what the observation recorded, without re-tagging: the nodes still carry data-jev-idx.
FINGERPRINT_JS = "() => {\n" + JS_HELPERS + r"""
  const nodes = {};
  for (const el of document.querySelectorAll('[data-jev-idx]')) nodes[el.getAttribute('data-jev-idx')] = nodeTuple(el);
  return { url: location.href, title: document.title, text_head: visibleText(500), nodes };
}
"""

TUPLE_FIELDS = ("connected", "visible", "value", "checked", "disabled", "context")
GUARD_SKIPPED = {"SCROLL_DOWN", "SCROLL_UP", "WAIT"}
TARGET_OPERATIONS = {"CLICK", "TYPE_TEXT", "SELECT"}


def observe(page, max_elements: int = 60, max_text_chars: int = 2000) -> dict:
    """Run the observation script on the current page and return the observation dict.

    Besides the element table it carries `fingerprint`: url, title, the first 500 chars of visible text and
    one identity/meaning tuple per tagged node, which `fingerprint()` + `compare_fingerprint()` check again
    right before acting.
    """
    obs = page.evaluate(OBSERVE_JS, {"maxElements": max_elements, "maxTextChars": max_text_chars})
    s = obs["scroll"]
    obs["can_scroll_down"] = s["y"] + s["viewport"] < s["height"] - 8
    obs["can_scroll_up"] = s["y"] > 8
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
    still-identical control. DONE / BLOCKED / PRESS_ENTER and anything else compare url, title, the text head
    and every node tuple, because those decisions are about the whole page.
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
    """One-line description of an element, used both in the state table and as a Choice option."""
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
