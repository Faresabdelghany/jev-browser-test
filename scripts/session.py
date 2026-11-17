"""What a run can take over from an earlier one besides a saved path: a logged-in session, and the browser's HTTP cache.

**Sessions.** A spec that puts its login in `login` (scripted steps, like `setup`, run before it) says which part
of its preparation only establishes who is logged in. With `session.reuse` on (`--reuse-sessions`; a suite's
`--sessions`) the first run that logs in saves the browser's storage state (cookies, localStorage) and the page it
was on to `.jev/sessions/<key>.json`, and every later run of a spec with the **same login on the same site** starts
from that state on that page and skips the `login` steps. The key is a keyed hash of the site's origin, the login
steps as this run would execute them (so another account is another session) and the device: the file name says
nothing about the credentials, and the file holds what the browser holds after a login, never what was typed. A
saved session is checked before it is used: the page it was saved on must answer at the same URL shape (an
application that sends an expired session to its login page fails this) and show what the login's `wait_for`
steps waited for; a session that fails the check is deleted and the run logs in as if there had been none. A spec
that tests the login itself keeps it in the flow (or in `setup`) and has no `login` block; `"session": "never"`
keeps a spec with one out of reuse even under `--reuse-sessions`.

**HTTP cache.** With `browser.http_cache` (`--http-cache`) the browser is launched on a profile directory under
`.jev/http-cache/` instead of a throwaway one, and before every launch everything in that profile except the cache
folders is removed. What survives a run is therefore the HTTP cache and the compiled-code cache, with the
browser's own freshness rules, and nothing else: no cookies, no localStorage, no service worker. One profile is one
browser at a time, so parallel runs take different slots (`slot-0`, `slot-1`, ...), each warm after its first use.

Both directories write their own `.gitignore` (replay.private_dir): local state, never committed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
import time
from urllib.parse import urlsplit

from replay import private_dir, url_shape

SESSION_FORMAT = 1
DEFAULT_SESSION_DIR = os.path.join(".jev", "sessions")
DEFAULT_CACHE_DIR = os.path.join(".jev", "http-cache")
DEFAULT_MAX_AGE_S = 12 * 3600  # a saved session older than this is not tried (the check before use is what really decides)
KEPT_IN_PROFILE = ("Cache", "Code Cache")  # under <profile>/Default: the only folders a run inherits
CACHE_SLOTS = 16
SLOT_STALE_S = 3600  # a slot's lock older than this was left by a run that died
VALIDATE_WAIT_MS = 10000  # how long a reused session's page gets to show what the login waited for


def origin_of(url: str) -> str:
    u = urlsplit(url or "")
    return f"{u.scheme}://{u.netloc}"


def _salt(directory: str) -> bytes:
    """A random key kept beside the sessions: session file names are HMACs under it, so a name cannot be tested
    against guesses of the credentials that went into it."""
    private_dir(directory)
    path = os.path.join(directory, ".salt")
    try:
        with open(path, "rb") as f:
            salt = f.read().strip()
        if salt:
            return salt
    except OSError:
        pass
    salt = secrets.token_hex(16).encode("ascii")
    with open(path, "wb") as f:
        f.write(salt)
    return salt


def session_key(spec: dict, directory: str) -> str:
    """Which saved session a run may use: the same site, the same login as executed, the same device."""
    b = spec.get("browser") or {}
    what = {"origin": origin_of(spec["start_url"]), "login": spec.get("login") or [], "device": b.get("device")}
    body = json.dumps(what, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(_salt(directory), body, hashlib.sha256).hexdigest()[:32]


def session_file(directory: str, key: str) -> str:
    return os.path.join(directory, f"{key}.json")


def load_session(file: str, max_age_s: float = DEFAULT_MAX_AGE_S, now: float | None = None) -> tuple[dict | None, str | None]:
    """(session, None) when `file` holds a session worth trying, else (None, why not)."""
    if not os.path.isfile(file):
        return None, "no saved session yet"
    try:
        with open(file, encoding="utf-8") as f:
            session = json.load(f)
    except (OSError, ValueError) as e:
        return None, f"the saved session could not be read ({type(e).__name__})"
    if not isinstance(session, dict) or session.get("format") != SESSION_FORMAT or not isinstance(session.get("state"), dict) \
            or not isinstance(session.get("url"), str):
        return None, "the saved session is not one this runner wrote"
    age = (time.time() if now is None else now) - float(session.get("saved_at") or 0)
    if age > max_age_s:
        return None, f"the saved session is {int(age // 3600)} h old (session.max_age_s: {int(max_age_s)})"
    session["age_s"] = int(age)
    return session, None


def save_session(file: str, state: dict, url: str, now: float | None = None) -> None:
    """Write the storage state and the page the login ended on. The file is as sensitive as a logged-in browser:
    readable by its owner only where the system has such a thing."""
    private_dir(os.path.dirname(file) or ".")
    tmp = f"{file}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"format": SESSION_FORMAT, "saved_at": time.time() if now is None else now, "url": url, "state": state}, f)
    os.replace(tmp, file)


def drop_session(file: str) -> None:
    try:
        os.remove(file)
    except OSError:
        pass


def page_mismatch(saved_url: str, now_url: str) -> str | None:
    """Why the page a saved session was opened on is not the page it was saved on, or None: an application answers
    an expired session with its login page, which is another URL."""
    if url_shape(saved_url) != url_shape(now_url):
        return f"the session was saved on {url_shape(saved_url)} and the application answered with {url_shape(now_url)}"
    return None


def local_storage_script(state: dict) -> str | None:
    """An init script that puts a storage state's localStorage back, per origin, once per tab (a context opened on a
    profile directory takes no storage state from Playwright; cookies are added with add_cookies). None when the state
    has none."""
    items = {o.get("origin"): [[i.get("name"), i.get("value")] for i in o.get("localStorage") or []]
             for o in state.get("origins") or [] if o.get("origin") and o.get("localStorage")}
    if not items:
        return None
    return ("(() => { try { const all = " + json.dumps(items) + "; const mine = all[location.origin];"
            " if (!mine || sessionStorage.getItem('__jevSessionRestored')) return;"
            " sessionStorage.setItem('__jevSessionRestored', '1');"
            " for (const [k, v] of mine) localStorage.setItem(k, v); } catch (e) {} })();")


def strip_profile(profile: str) -> None:
    """Remove everything from a browser profile except its HTTP and code caches, so a launch on it starts as clean as
    a throwaway profile and as warm as the last run left the cache."""
    default = os.path.join(profile, "Default")
    for root, keep in ((profile, ("Default",)), (default, KEPT_IN_PROFILE)):
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if name in keep:
                continue
            path = os.path.join(root, name)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except OSError:
                    pass


class CacheSlot:
    """One profile directory for one browser: `acquire` takes the first slot nobody holds (a lock file created
    exclusively; one left by a run that died is taken over after SLOT_STALE_S), `release` gives it back."""

    def __init__(self, path: str, lock: str):
        self.path, self.lock = path, lock

    @classmethod
    def acquire(cls, directory: str, slots: int = CACHE_SLOTS, now: float | None = None) -> "CacheSlot | None":
        private_dir(directory)
        for n in range(slots):
            lock = os.path.join(directory, f"slot-{n}.lock")
            try:
                if os.path.exists(lock) and (time.time() if now is None else now) - os.path.getmtime(lock) > SLOT_STALE_S:
                    os.remove(lock)
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            except OSError:
                continue
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
            path = os.path.join(directory, f"slot-{n}")
            os.makedirs(path, exist_ok=True)
            return cls(path, lock)
        return None

    def release(self) -> None:
        try:
            os.remove(self.lock)
        except OSError:
            pass
