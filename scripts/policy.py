"""Policy: turn (spec, observation, history) into one System One request, and read the answers.

Design (borrowed from browser-use/jev-ultrafast):
  * The action space is *indexed*: Jev picks an operation and a numbered element, never free text.
  * Operation and every possible target are asked in the SAME request (speculatively). Only the
    target matching the chosen operation is executed. Two decisions, one round trip.
  * Only supported operations and compatible targets are offered, so an impossible action cannot
    be chosen. No text field visible -> TYPE_TEXT is not even an option.
  * Text Jev types comes from `spec.data` (prepared by Claude). Jev chooses WHICH value, never
    what to write. A needed-but-missing value should surface as BLOCKED, which escalates to Claude.
  * The spec's checks ride along as Noul questions every step, so verification costs no extra call.
"""
from __future__ import annotations

from jev_client import choice, noul
from observe import element_label, render_table

CLICK_ROLES = {
    "link", "button", "submit", "reset", "image", "tab", "menuitem", "menuitemcheckbox", "menuitemradio",
    "option", "checkbox", "radio", "switch", "clickable", "file",
}
TYPE_ROLES = {"textbox", "searchbox", "combobox"}
HISTORY_WINDOW = 8

OPERATION_DESCRIPTIONS = {
    "CLICK": "Click one of the listed elements (link, button, tab, checkbox, ...)",
    "TYPE_TEXT": "Type one of the available data values into a text field",
    "PRESS_ENTER": "Press Enter to submit the field that was just typed into",
    "SELECT": "Choose an option in one of the listed dropdowns",
    "SCROLL_DOWN": "Scroll down to reveal more of the page",
    "SCROLL_UP": "Scroll up to reveal earlier parts of the page",
    "WAIT": "The page is still loading or changing; wait before acting",
    "DONE": "The goal has been fully achieved on the current page; nothing more to do",
    "BLOCKED": "The goal cannot be achieved from here: a needed value or element is missing, the site refuses, or the flow is impossible",
}


def _value_preview(spec: dict, key: str) -> str:
    if key in spec["secrets"]:
        return f"{key} = <secret>"
    v = spec["data"][key]
    v = v if len(v) <= 40 else v[:37] + "..."
    return f'{key} = "{v}"'


def build_state(spec: dict, obs: dict, step: int, history: list[str]) -> dict:
    """The state Jev evaluates. Keep it compact: goal, hints, where we are, what we did, what we see."""
    recent = history[-HISTORY_WINDOW:]
    state = {
        "goal": spec["goal"],
        "step": f"{step} of {spec['budget']['max_steps']}",
        "page": {"title": obs["title"], "url": obs["url"]},
        "actions_so_far": "\n".join(recent) if recent else "(none yet)",
        "interactive_elements": render_table(obs),
        "visible_text": obs["visible_text"],
        "available_data_values": [_value_preview(spec, k) for k in spec["data"]] or ["(none)"],
    }
    if spec.get("notes"):
        state["hints"] = spec["notes"]
    return state


def build_questions(spec: dict, obs: dict, last_operation: str | None) -> tuple[dict, dict]:
    """Return (questions, meta). meta records which target options exist so answers can be resolved."""
    elements = obs["elements"]
    clickable = [e for e in elements if e["role"] in CLICK_ROLES and not e.get("disabled")]
    typable = [e for e in elements if e["role"] in TYPE_ROLES and not e.get("disabled")]
    selects = [e for e in elements if e["role"] == "select" and not e.get("disabled") and e.get("options")]

    ops = {}
    if clickable:
        ops["CLICK"] = OPERATION_DESCRIPTIONS["CLICK"]
    if typable and spec["data"]:
        ops["TYPE_TEXT"] = OPERATION_DESCRIPTIONS["TYPE_TEXT"]
    if last_operation == "TYPE_TEXT":
        ops["PRESS_ENTER"] = OPERATION_DESCRIPTIONS["PRESS_ENTER"]
    if selects:
        ops["SELECT"] = OPERATION_DESCRIPTIONS["SELECT"]
    if obs.get("can_scroll_down"):
        ops["SCROLL_DOWN"] = OPERATION_DESCRIPTIONS["SCROLL_DOWN"]
    if obs.get("can_scroll_up"):
        ops["SCROLL_UP"] = OPERATION_DESCRIPTIONS["SCROLL_UP"]
    ops["WAIT"] = OPERATION_DESCRIPTIONS["WAIT"]
    ops["DONE"] = OPERATION_DESCRIPTIONS["DONE"]
    ops["BLOCKED"] = OPERATION_DESCRIPTIONS["BLOCKED"]

    questions = {
        "operation": choice(
            "Given the goal, the actions so far and the current page, which single operation should be performed next?",
            ops,
        )
    }
    meta = {"operations": list(ops)}

    if "CLICK" in ops:
        questions["click_target"] = choice(
            "If the next operation is CLICK, which element should be clicked to make progress toward the goal?",
            {str(e["idx"]): element_label(e) for e in clickable},
        )
    if "TYPE_TEXT" in ops:
        questions["type_target"] = choice(
            "If the next operation is TYPE_TEXT, which text field should receive the value?",
            {str(e["idx"]): element_label(e) for e in typable},
        )
        questions["type_value"] = choice(
            "If the next operation is TYPE_TEXT, which of the available data values should be typed?",
            {k: _value_preview(spec, k) for k in spec["data"]},
        )
    if "SELECT" in ops:
        select_options = {}
        for e in selects:
            for o in e["options"]:
                if o.get("disabled"):
                    continue
                select_options[f"{e['idx']}:{o['i']}"] = f'{e["role"]} "{e["name"]}" -> "{o["text"]}"'
        if select_options:
            questions["select_target"] = choice(
                "If the next operation is SELECT, which dropdown option should be chosen?",
                select_options,
            )
        else:
            del questions["operation"]["criteria"]["SELECT"]
            meta["operations"].remove("SELECT")

    for name, statement in spec["checks"].items():
        questions[name] = noul(statement)
    return questions, meta


def read_choice(answers: dict, key: str) -> dict | None:
    a = answers.get(key)
    if not a or a.get("type") != "choice" or "choice" not in a:
        return None
    probs = a.get("probabilities") or {}
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:5]
    return {
        "choice": str(a["choice"]),
        "confidence": float(a.get("confidence", 0.0) or 0.0),
        "top_probabilities": {k: round(float(v), 3) for k, v in top},
    }


def read_checks(answers: dict, spec: dict) -> dict[str, float]:
    out = {}
    for name in spec["checks"]:
        a = answers.get(name)
        if a and a.get("type") == "noul" and "noul" in a:
            out[name] = round(float(a["noul"]), 3)
    return out


def resolve_target(operation: str, answers: dict, obs: dict) -> dict | None:
    """Pick the target answer that matches the chosen operation and attach the element it refers to."""
    key = {"CLICK": "click_target", "TYPE_TEXT": "type_target", "SELECT": "select_target"}.get(operation)
    if not key:
        return None
    picked = read_choice(answers, key)
    if not picked:
        return {"question": key, "missing": True}
    by_idx = {e["idx"]: e for e in obs["elements"]}
    if operation == "SELECT":
        el_idx, opt_idx = picked["choice"].split(":")
        el = by_idx.get(int(el_idx))
        opt = next((o for o in (el or {}).get("options", []) if str(o["i"]) == opt_idx), None)
        label = f'[{el_idx}] {element_label(el)} -> "{opt["text"]}"' if el and opt else picked["choice"]
        return {**picked, "question": key, "element": int(el_idx), "option": int(opt_idx), "label": label}
    el = by_idx.get(int(picked["choice"]))
    label = f'[{picked["choice"]}] {element_label(el)}' if el else picked["choice"]
    return {**picked, "question": key, "element": int(picked["choice"]), "label": label}
