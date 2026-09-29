"""Vending automaton simulator (Member B; UI upgrade by frontend).

Run:  streamlit run app/Simulator.py

The automaton logic below (load_default / reset / press) is unchanged; the
new UI only *observes* each step through ui.session.record_step.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.generator import build, load_config  # noqa: E402
from core.mealy import explain_dead, step  # noqa: E402
from core.minimize import to_minimal  # noqa: E402
from core.render import to_dot  # noqa: E402
from core.theme import get_mode, icon_for, inject_css, style_dot  # noqa: E402
from ui import panels, tutorial  # noqa: E402
from ui.session import balance_of, init_ui_state, on_reset, record_step  # noqa: E402

st.set_page_config(page_title="Vending Automaton", page_icon="🥤", layout="wide")


def load_default():
    cfg = load_config(ROOT / "spec" / "config.json")
    naive, lam, cfg = build(cfg)
    dfa, mlam, _classes, _trace = to_minimal(naive, lam)
    return dfa, mlam, cfg


def reset():
    st.session_state.state = st.session_state.machine[0].initial_state
    st.session_state.log = []
    st.session_state.message = "Insert coins, then choose a product."
    on_reset()


init_ui_state()
if "machine" not in st.session_state:
    st.session_state.machine = load_default()   # Generator page may replace this
    reset()

dfa, lam, cfg = st.session_state.machine


def press(symbol):
    q = st.session_state.state
    nxt, out = step(dfa, lam, q, symbol)
    st.session_state.log.append(
        {"step": len(st.session_state.log) + 1, "state": q, "input": symbol,
         "next": nxt, "output": out})
    st.session_state.state = nxt
    if nxt == "q_dead":
        st.session_state.message = f"{out} — {explain_dead(cfg, q, symbol)}"
    elif nxt in dfa.final_states:
        st.session_state.message = f"Dispensed: {out}. Transaction accepted."
    else:
        st.session_state.message = out if out != "—" else f"Balance ₹{nxt[1:]}"
    record_step(dfa, cfg, q, symbol, nxt, out)


# ── page chrome ────────────────────────────────────────────────────────
state = st.session_state.state
bal = balance_of(state)
last = st.session_state.last
fx = f"fx_{last['kind'] if last else 'idle'}_{st.session_state.fx_n}"

# Per-machine button styling: coin keys look like coins; products you can
# currently afford get a success edge, the rest are dimmed (still clickable,
# because pressing them is how you *see* the trap transition).
coin_css = "".join(
    f".st-key-btn_{c} button {{ border-radius: 999px; font-family: 'IBM Plex Mono', monospace; "
    f"font-size: 1.05rem; min-height: 3rem; }}\n" for c in cfg["coins"])
prod_css = "".join(
    (f".st-key-btn_{s} button {{ border-left: 4px solid var(--vm-success); }}\n"
     if bal is not None and p["price"] <= bal else
     f".st-key-btn_{s} button {{ opacity: .62; }}\n.st-key-btn_{s} button:hover {{ opacity: 1; }}\n")
    for s, p in cfg["products"].items())
inject_css(get_mode(), coin_css + prod_css)

panels.top_bar("Vending machine automaton",
               "A DFA acceptor with a Mealy output layer. Every button is one input symbol.")
tutorial.maybe_show()
panels.sidebar_stats(st.session_state.log)

left, right = st.columns([5, 7], gap="large")

with left:
    with st.container(key="card_machine"):
        panels.label("Machine status")
        with st.container(key=f"{fx}_lcd"):
            panels.lcd(state, st.session_state.message, dfa)

    with st.container(key="card_coins"):
        panels.label("Coin input")
        cols = st.columns(len(cfg["coins"]) + 1)
        for col, (c, v) in zip(cols, cfg["coins"].items()):
            col.button(f"₹{v}", key=f"btn_{c}", on_click=press, args=(c,), width="stretch")
        cols[-1].button("Cancel", key="btn_cancel", on_click=press, args=("cancel",),
                        width="stretch", icon=":material/undo:")

    with st.container(key="card_products"):
        panels.label("Product selection")
        for s, p in cfg["products"].items():
            st.button(f"{p['name']} · ₹{p['price']}", key=f"btn_{s}", on_click=press,
                      args=(s,), width="stretch", icon=icon_for(p["name"]))

    with st.container(key="card_status"):
        panels.label("Transaction status")
        if state == "q_dead":
            with st.container(key="status_error"):
                st.error(st.session_state.message)
        elif state in dfa.final_states:
            with st.container(key="status_success"):
                st.success(st.session_state.message)
        else:
            with st.container(key="status_info"):
                st.info(st.session_state.message)
        st.button("Reset machine", key="btn_reset", on_click=reset, type="primary",
                  icon=":material/restart_alt:", width="stretch")

with right:
    with st.container(key="card_monitor"):
        panels.label("Automaton monitor")
        with st.container(key=f"{fx}_mon"):
            panels.monitor(state, cfg, st.session_state.log)
        prev = last["prev"] if last else None
        st.graphviz_chart(style_dot(to_dot(dfa, highlight=state), get_mode(), state, prev),
                          width="stretch")

    with st.container(key="card_explain"):
        panels.label("How the DFA works")
        panels.explain(dfa, cfg, state, st.session_state.log)
        with st.expander("State legend", icon=":material/info:"):
            panels.legend(dfa, cfg)

h_col, log_col = st.columns([6, 6], gap="large")
with h_col:
    with st.container(key="card_history"):
        panels.label("Transaction history")
        panels.history(cfg)
with log_col:
    with st.container(key="card_log"):
        panels.label("Step log")
        if st.session_state.log:
            with st.container(height=320, border=False):
                st.table(list(reversed(st.session_state.log)))
        else:
            st.caption("No steps yet.")
