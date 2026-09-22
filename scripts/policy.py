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
  * The state is structured (TypeSafe's guidance: an object with a descriptive name for each part):
    `elements` as records with the operations each can be the target of, `available_data_values` as
    {key, value}, `recent_actions` as {step, operation, target, value_key, ok, page_changed}.
  * Answers are data from a network service and the runner acts on them, so nothing is trusted
    before it is checked: a Choice answer must pick an offered key, carry a well-formed
    distribution over offered keys, and put its pick on top (`validate_choice`). Only a validated
    choice is ever turned into an element index.
"""
from __future__ import annotations

from jev_client import choice, noul
from observe import element_label
from rules import CHECK, NEXT_ACTION, TARGET, VALUE

CLICK_ROLES = {
    "link", "button", "submit", "reset", "image", "tab", "menuitem", "menuitemcheckbox", "menuitemradio",
    "option", "checkbox", "radio", "switch", "clickable", "file",
}
TYPE_ROLES = {"textbox", "searchbox", "combobox"}
CHECKABLE_ROLES = {"checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"}
HISTORY_WINDOW = 10  # recent_actions entries Jev sees; jev-ultrafast keeps the same window
TARGET_QUESTIONS = {"CLICK": "click_target", "TYPE_TEXT": "type_target", "SELECT": "select_target"}
PROBABILITY_SUM_TOLERANCE = 0.02

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


def value_preview(spec: dict, key: str) -> str:
    """What Jev is shown for a data value: the literal "<secret>" for secrets, else the value cut to 40 chars."""
    if key in spec["secrets"]:
        return "<secret>"
    v = spec["data"][key]
    return v if len(v) <= 40 else v[:37] + "..."


def data_values(spec: dict) -> list[dict]:
    """`available_data_values` in the state and the `type_value` options share this rendering."""
    return [{"key": k, "value": value_preview(spec, k)} for k in spec["data"]]


def element_operations(spec: dict, e: dict) -> list[str]:
    """The operations an observed element can be the target of.

    Used both to describe the element in the state and to decide which elements each target
    question offers, so the state and the questions cannot disagree about what is actionable.
    """
    ops = []
    if e.get("disabled"):
        return ops
    if e["role"] in CLICK_ROLES:
        ops.append("CLICK")
    if e["role"] in TYPE_ROLES and spec["data"]:
        ops.append("TYPE_TEXT")
    if e["role"] == "select" and any(not o.get("disabled") for o in e.get("options") or []):
        ops.append("SELECT")
    return ops


def describe_element(spec: dict, e: dict) -> dict:
    """One element as Jev sees it in `state.elements`: named fields, not a rendered line."""
    d = {"index": e["idx"], "role": e["role"], "label": e.get("name") or ""}
    if e.get("text"):
        d["text"] = e["text"]
    d["value"] = e.get("value") or ""
    d["checked"] = e.get("checked") if e.get("checked") is not None else None
    d["context"] = e.get("context") or None
    if e.get("disabled"):
        d["disabled"] = True
    if e["role"] == "select":
        d["options"] = [o["text"] for o in e.get("options") or [] if not o.get("disabled")]
    d["operations"] = element_operations(spec, e)
    return d


def target_criterion(e: dict) -> dict:
    """A click_target / type_target option as an object (TypeSafe criteria may be objects).

    `element` and `role` always; `current_value` always for text fields and selects (an empty string
    tells Jev the field is empty, which the rule about not re-filling a field needs) and otherwise only
    when non-empty; `checked` as "true"/"false" for checkable roles; `text` and `context` when present.
    """
    c = {"element": f'[{e["idx"]}] {e["role"]} "{e.get("name") or ""}"', "role": e["role"]}
    if e.get("text"):
        c["text"] = e["text"]
    if e["role"] in TYPE_ROLES or e["role"] == "select" or e.get("value"):
        c["current_value"] = e.get("value") or ""
    if e["role"] in CHECKABLE_ROLES and e.get("checked") is not None:
        c["checked"] = "true" if e["checked"] else "false"
    if e.get("context"):
        c["context"] = e["context"]
    return c


def build_state(spec: dict, obs: dict, step: int, history: list[dict]) -> dict:
    """The state Jev evaluates: an object with a descriptive name for every part.

    `elements` is the table as structured records, `available_data_values` the strings Jev may pick
    for TYPE_TEXT (secrets masked), `recent_actions` the last HISTORY_WINDOW entries of the runner's
    history. Each history entry is a dict {step, operation, target, value_key, ok, page_changed}
    (runner-inserted waits carry a `reason` instead of a target). `page_changed` is filled in by the
    runner once the next observation exists; it is what lets Jev notice its own click did nothing.
    """
    state = {"goal": spec["goal"]}
    if spec.get("notes"):
        state["hints"] = spec["notes"]
    state.update({
        "step": {"n": step, "max": spec["budget"]["max_steps"]},
        "page": {"url": obs["url"], "title": obs["title"]},
        "elements": [describe_element(spec, e) for e in obs["elements"]],
        "truncated_elements": obs.get("truncated", 0),
        "visible_text": obs["visible_text"],
        "available_data_values": data_values(spec),
        "recent_actions": list(history[-HISTORY_WINDOW:]),
    })
    return state


def build_questions(spec: dict, obs: dict, last_operation: str | None) -> tuple[dict, dict]:
    """Return (questions, meta).

    meta["operations"] lists the offered operations; meta["offered"] maps every Choice question that
    was actually built (operation, click_target, type_target, type_value, select_target) to the keys
    it offered, which is what `validate_choice` checks answers against.
    """
    elements = obs["elements"]
    can = {e["idx"]: element_operations(spec, e) for e in elements}
    clickable = [e for e in elements if "CLICK" in can[e["idx"]]]
    typable = [e for e in elements if "TYPE_TEXT" in can[e["idx"]]]
    selects = [e for e in elements if "SELECT" in can[e["idx"]]]

    ops = {}
    if clickable:
        ops["CLICK"] = OPERATION_DESCRIPTIONS["CLICK"]
    if typable:
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

    goal = spec["goal"]

    def target_instructions(operation: str) -> dict:
        return {"goal": goal, "operation": operation, "rules": [NEXT_ACTION, TARGET]}

    questions = {"operation": choice({"goal": goal, "rules": NEXT_ACTION}, ops)}
    if "CLICK" in ops:
        questions["click_target"] = choice(target_instructions("CLICK"), {str(e["idx"]): target_criterion(e) for e in clickable})
    if "TYPE_TEXT" in ops:
        questions["type_target"] = choice(target_instructions("TYPE_TEXT"), {str(e["idx"]): target_criterion(e) for e in typable})
        questions["type_value"] = choice(
            {"goal": goal, "operation": "TYPE_TEXT", "rules": [NEXT_ACTION, VALUE]},
            {d["key"]: d for d in data_values(spec)},
        )
    if "SELECT" in ops:
        # element_operations only reports SELECT when at least one option is enabled, so this is never empty
        select_options = {
            f"{e['idx']}:{o['i']}": {"element": f'[{e["idx"]}] select "{e.get("name") or ""}"', "option": o["text"],
                                     "current_value": e.get("value") or ""}
            for e in selects for o in e["options"] if not o.get("disabled")
        }
        questions["select_target"] = choice(target_instructions("SELECT"), select_options)

    for name, statement in spec["checks"].items():
        questions[name] = noul({"statement": statement, "rules": CHECK})
    meta = {
        "operations": list(ops),
        "offered": {k: list(q["criteria"]) for k, q in questions.items() if q["type"] == "choice"},
    }
    return questions, meta


def _unit_number(v) -> bool:
    """True for an int or float (not a bool) within [0, 1].

    The chained comparison is false for NaN and +/-inf on its own, and it never converts to float,
    so a 400-digit JSON integer is dropped like any other bad value instead of raising OverflowError
    (math.isfinite would) out of the loop and losing the step.
    """
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1


def validate_choice(answer, offered) -> str | None:
    """Return None when `answer` is a well-formed Choice over the `offered` keys, else a short reason.

    Strict on purpose: the pick must be an offered key, every probability key must be offered, the
    values finite in [0, 1] and summing to 1 (+/- PROBABILITY_SUM_TOLERANCE), `confidence` finite in
    [0, 1], and the pick must carry the top probability. Missing fields are invalid. A rejected
    answer is never acted on; the reason lands in the trace as `step.invalid_answer`.
    """
    if answer is None:
        return "no answer"
    if not isinstance(answer, dict):
        return "answer is not an object"
    if answer.get("type") != "choice":
        return f"type is {answer.get('type')!r}, not 'choice'"
    offered = set(offered)
    picked = answer.get("choice")
    if not isinstance(picked, str):
        return "choice is missing or not a string"
    if picked not in offered:
        return f"choice {picked!r} was not offered"
    probs = answer.get("probabilities")
    if not isinstance(probs, dict) or not probs:
        return "probabilities missing or empty"
    for k, v in probs.items():
        if k not in offered:
            return f"probability key {k!r} was not offered"
        if not _unit_number(v):
            return f"probability of {k!r} is not a finite number in [0, 1]"
    total = sum(probs.values())
    if abs(total - 1) > PROBABILITY_SUM_TOLERANCE:
        return f"probabilities sum to {total:.3f}, not 1"
    if not _unit_number(answer.get("confidence")):
        return "confidence is missing or not a finite number in [0, 1]"
    if picked not in probs:
        return f"choice {picked!r} has no probability"
    if probs[picked] < max(probs.values()) - 1e-6:
        return f"choice {picked!r} is not the top option"
    return None


def read_choice(answers: dict, key: str, offered: list[str] | None = None) -> dict | None:
    """Parse the Choice answer under `key` into {choice, confidence, top_probabilities}.

    With `offered` (the keys the question was built with, from meta["offered"]) the answer must pass
    `validate_choice`, otherwise None. The loop always passes it. Without `offered` the parse is
    lenient (shape only, nothing checked against the option set); that form is for reading traces
    and ad-hoc tooling, never for deciding what to execute.
    """
    a = answers.get(key)
    if offered is not None:
        if validate_choice(a, offered) is not None:
            return None
    elif not isinstance(a, dict) or a.get("type") != "choice" or "choice" not in a:
        return None
    probs = a.get("probabilities") or {}
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:5]
    return {
        "choice": str(a["choice"]),
        "confidence": float(a.get("confidence", 0.0) or 0.0),
        "top_probabilities": {k: round(float(v), 3) for k, v in top},
    }


def read_checks(answers: dict, spec: dict) -> dict[str, float]:
    """Noul probability per check. A check whose answer is missing or malformed (no `noul`, or a
    value that is not a finite number in [0, 1]) is left out; its absence in the trace is the signal."""
    out = {}
    for name in spec["checks"]:
        a = answers.get(name)
        if isinstance(a, dict) and a.get("type") == "noul" and _unit_number(a.get("noul")):
            out[name] = round(float(a["noul"]), 3)
    return out


def resolve_target(operation: str, answers: dict, obs: dict, meta: dict) -> dict | None:
    """Pick the target answer that matches the chosen operation and attach the element it refers to.

    The answer is validated against the keys the question offered (meta["offered"]) before any of it
    is parsed, so an unvalidated string never reaches int(). An invalid or missing answer returns
    {"question", "missing": True, "invalid": reason}; `missing` keeps execute() failing safely.
    """
    key = TARGET_QUESTIONS.get(operation)
    if not key:
        return None
    offered = meta["offered"].get(key, [])
    problem = validate_choice(answers.get(key), offered)
    if problem:
        return {"question": key, "missing": True, "invalid": problem}
    picked = read_choice(answers, key, offered)
    by_idx = {e["idx"]: e for e in obs["elements"]}
    if operation == "SELECT":
        el_idx, opt_idx = picked["choice"].split(":")  # offered keys are built as "<idx>:<option>"
        el = by_idx.get(int(el_idx))
        opt = next((o for o in (el or {}).get("options", []) if str(o["i"]) == opt_idx), None)
        label = f'[{el_idx}] {element_label(el)} -> "{opt["text"]}"' if el and opt else picked["choice"]
        return {**picked, "question": key, "element": int(el_idx), "option": int(opt_idx), "label": label}
    el = by_idx.get(int(picked["choice"]))  # offered keys are built as str(idx)
    label = f'[{picked["choice"]}] {element_label(el)}' if el else picked["choice"]
    return {**picked, "question": key, "element": int(picked["choice"]), "label": label}
