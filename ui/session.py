"""UI-only session bookkeeping (frontend owner).

Records what the user did — transactions, stats, last transition — by
*observing* the (state, symbol, next, output) tuples the Simulator already
computes with core.mealy.step. It never changes the automaton.
"""
import csv
import io
from datetime import datetime

import streamlit as st

_DEFAULTS = {
    "theme_mode": "dark",
    "last": None,            # dict(prev, symbol, next, output, kind)
    "fx_n": 0,               # bumps on every step so animations replay
    "history": [],           # finished transactions, newest last
    "tx": None,              # the transaction in progress
    "tutorial_open": True,   # auto-open once on first visit
    "tutorial_step": 0,
}


def init_ui_state():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v if not isinstance(v, list) else list(v)
    if "session_started" not in st.session_state:
        st.session_state.session_started = datetime.now()
    if st.session_state.tx is None:
        st.session_state.tx = _new_tx()


def _now():
    return datetime.now().strftime("%H:%M:%S")


def _new_tx():
    return {"coins": [], "symbols": [], "started": _now()}


def balance_of(state):
    """Balance encoded in a balance-state name like 'q15'; None otherwise."""
    if state and state.startswith("q") and state[1:].isdigit():
        return int(state[1:])
    return None


def symbol_label(cfg, sym):
    if sym in cfg["coins"]:
        return f"₹{cfg['coins'][sym]} coin"
    if sym == "cancel":
        return "Cancel"
    if sym in cfg["products"]:
        return cfg["products"][sym]["name"]
    return sym


def classify(dfa, cfg, prev, sym, nxt):
    """One of: coin, cancel, accept, trap, blocked."""
    if prev in ("q_dead",) or prev in dfa.final_states:
        return "blocked"
    if nxt == "q_dead":
        return "trap"
    if nxt in dfa.final_states:
        return "accept"
    if sym == "cancel":
        return "cancel"
    return "coin"


def record_step(dfa, cfg, prev, sym, nxt, out):
    """Call after every simulator step. Updates last transition + history."""
    kind = classify(dfa, cfg, prev, sym, nxt)
    st.session_state.last = {"prev": prev, "symbol": sym, "next": nxt,
                             "output": out, "kind": kind}
    st.session_state.fx_n += 1
    tx = st.session_state.tx
    tx["symbols"].append(sym)
    bal = balance_of(prev) or 0

    if kind == "coin":
        tx["coins"].append(cfg["coins"][sym])
    elif kind == "cancel":
        _close(tx, "cancel", "Cancelled", refund=bal, detail=out)
    elif kind == "accept":
        price = cfg["products"][sym]["price"]
        _close(tx, "purchase", cfg["products"][sym]["name"], product=sym,
               paid=bal, price=price, change=bal - price, detail=out)
    elif kind == "trap":
        if sym in cfg["coins"]:
            title = "Rejected: over cap"
        else:
            title = f"Rejected: {cfg['products'][sym]['name']} unaffordable"
        _close(tx, "reject", title, product=sym if sym in cfg["products"] else None,
               paid=bal, detail=out)
    # 'blocked' = input after the transaction ended; already recorded.


def _close(tx, kind, title, **info):
    entry = {"kind": kind, "title": title, "time": _now(), "started": tx["started"],
             "coins": list(tx["coins"]), "word": " ".join(tx["symbols"]),
             "paid": 0, "price": 0, "change": 0, "refund": 0, "product": None}
    entry.update(info)
    st.session_state.history.append(entry)
    st.session_state.tx = _new_tx()


def on_reset():
    """Reset pressed: start a clean transaction and clear the last transition."""
    st.session_state.tx = _new_tx()
    st.session_state.last = None
    st.session_state.fx_n += 1


def stats():
    h = st.session_state.history
    buys = [e for e in h if e["kind"] == "purchase"]
    return {
        "purchases": len(buys),
        "revenue": sum(e["price"] for e in buys),
        "change": sum(e["change"] for e in buys),
        "refunds": sum(e["refund"] for e in h if e["kind"] == "cancel"),
        "rejected": sum(1 for e in h if e["kind"] == "reject"),
        "transactions": len(h),
        "steps": len(st.session_state.get("log", [])),
    }


def to_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: (" + ".join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})
    return buf.getvalue()
