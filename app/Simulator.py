"""Vending automaton simulator (Member B).  Run:  streamlit run app/Simulator.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.generator import build, load_config  # noqa: E402
from core.mealy import explain_dead, step  # noqa: E402
from core.minimize import to_minimal  # noqa: E402
from core.render import to_dot  # noqa: E402

st.set_page_config(page_title="Vending Automaton", layout="wide")


def load_default():
    cfg = load_config(ROOT / "spec" / "config.json")
    naive, lam, cfg = build(cfg)
    dfa, mlam, _ = to_minimal(naive, lam)
    return dfa, mlam, cfg


def reset():
    st.session_state.state = st.session_state.machine[0].initial_state
    st.session_state.log = []
    st.session_state.message = "Insert coins, then choose a product."


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


st.title("Vending machine automaton")
state = st.session_state.state
left, right = st.columns([1, 2], gap="large")

with left:
    bal = state[1:] if state[1:].isdigit() else "—"
    st.metric("Balance", f"₹{bal}")
    st.caption(f"Current state: `{state}`")
    if state == "q_dead":
        st.error(st.session_state.message)
    elif state in dfa.final_states:
        st.success(st.session_state.message)
    else:
        st.info(st.session_state.message)

    st.subheader("Coins")
    cols = st.columns(len(cfg["coins"]) + 1)
    for col, (c, v) in zip(cols, cfg["coins"].items()):
        col.button(f"₹{v}", key=f"btn_{c}", on_click=press, args=(c,), use_container_width=True)
    cols[-1].button("Cancel", key="btn_cancel", on_click=press, args=("cancel",),
                    use_container_width=True)

    st.subheader("Products")
    for s, p in cfg["products"].items():
        st.button(f"{p['name']} · ₹{p['price']}", key=f"btn_{s}", on_click=press,
                  args=(s,), use_container_width=True)

    st.button("Reset machine", key="btn_reset", on_click=reset, type="primary")

with right:
    st.graphviz_chart(to_dot(dfa, highlight=state), use_container_width=True)

st.subheader("Step log")
if st.session_state.log:
    st.dataframe(st.session_state.log, use_container_width=True, hide_index=True)
else:
    st.caption("No steps yet.")
