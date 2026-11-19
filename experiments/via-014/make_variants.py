"""0.14.0: a `via` variant of each public example whose flow goes through one control, for a with / without comparison.

    python make_variants.py <the checkout's specs/examples> <output folder>

Each variant is the example with `id: <id>-via` and the `via` below; `shop-checkout-error-account-via` also drops the
example's `expect` (its Finish button does nothing: with `via` the run ends in via_no_effect). Run the examples and the
variants in one suite (`run_suite.py <examples> <variants> --repeat 3 --workers 2`), then `tab.py results.json`."""
import json, os, sys
SRC, OUT = sys.argv[1], sys.argv[2]
VIA = {
    "add-remove-elements": {"click": "Add Element"}, "dynamic-controls": {"click": "Remove"}, "forgot-password": {"click": "Retrieve password"},
    "load-wait": {"click": "Start"}, "login-logout": {"click": "Login"}, "modal-close": {"click": "Close"}, "notify-random": {"click": "Click here"},
    "shop-add-second-item": {"click": "Add to cart"}, "shop-checkout": {"click": "Finish"}, "todo-add-filter": {"click": "Active"},
    "toolshop-search-cart": {"click": "Search"}, "web-form-submit": {"click": "Submit"}, "wiki-search": {"type": "Search Wikipedia"},
    "hrm-login": {"click": "Login"}, "hrm-pim-add-employee-list": {"click": "Search"}, "shop-checkout-error-account": {"click": "Finish"},
}
os.makedirs(OUT, exist_ok=True)
for name, via in VIA.items():
    spec = json.load(open(os.path.join(SRC, name + ".json"), encoding="utf-8"))
    spec["id"], spec["via"] = name + "-via", via
    if name == "shop-checkout-error-account":
        spec.pop("expect", None)
    json.dump(spec, open(os.path.join(OUT, name + "-via.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(len(VIA), "variants in", OUT)
