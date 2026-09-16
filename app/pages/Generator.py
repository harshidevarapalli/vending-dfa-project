"""Machine generator: any coin set + product list -> naive DFA, minimized DFA,
Hopcroft trace, Mealy table. Can push the result into the Simulator page.

Run via: streamlit run app/Simulator.py   (this page appears in the sidebar)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.generator import ConfigError, build  # noqa: E402
from core.minimize import to_minimal  # noqa: E402
from core.render import classes_table, to_dot, trace_table  # noqa: E402

st.set_page_config(page_title="Machine Generator", layout="wide")
st.title("Build any vending machine")
st.caption("Enter coins and products. The generator builds the naive DFA, "
           "minimizes it with Hopcroft's algorithm, and shows both.")

if "gen_coins" not in st.session_state:
    st.session_state.gen_coins = [("c5", 5), ("c10", 10)]
if "gen_products" not in st.session_state:
    st.session_state.gen_products = [("s1", "Chips", 10), ("s2", "Juice", 15),
                                      ("s3", "Chocolate", 20)]

with st.form("config_form"):
    st.subheader("Coins")
    coin_rows = []
    for i in range(4):
        default = st.session_state.gen_coins[i] if i < len(st.session_state.gen_coins) else ("", 0)
        c1, c2 = st.columns(2)
        sym = c1.text_input(f"Symbol {i + 1}", value=default[0], key=f"coin_sym_{i}",
                             placeholder="c5")
        val = c2.number_input(f"Value ₹ {i + 1}", min_value=0, step=5, value=default[1],
                               key=f"coin_val_{i}")
        if sym and val:
            coin_rows.append((sym, val))

    st.subheader("Products")
    prod_rows = []
    for i in range(4):
        default = st.session_state.gen_products[i] if i < len(st.session_state.gen_products) else ("", "", 0)
        c1, c2, c3 = st.columns(3)
        sym = c1.text_input(f"Symbol {i + 1}", value=default[0], key=f"prod_sym_{i}",
                             placeholder="s1")
        name = c2.text_input(f"Name {i + 1}", value=default[1], key=f"prod_name_{i}",
                              placeholder="Chips")
        price = c3.number_input(f"Price ₹ {i + 1}", min_value=0, step=5, value=default[2],
                                 key=f"prod_price_{i}")
        if sym and name and price:
            prod_rows.append((sym, name, price))

    cap = st.number_input("Balance cap ₹", min_value=5, step=5, value=25)
    submitted = st.form_submit_button("Generate", type="primary")

if submitted:
    st.session_state.gen_coins = coin_rows
    st.session_state.gen_products = [(s, n, p) for s, n, p in prod_rows]
    cfg = {
        "coins": dict(coin_rows),
        "products": {s: {"name": n, "price": p} for s, n, p in prod_rows},
        "cap": int(cap),
    }
    try:
        naive, lam, cfg = build(cfg)
        mdfa, mlam, classes, trace = to_minimal(naive, lam)
    except ConfigError as e:
        st.error(str(e))
    else:
        st.session_state.gen_result = (naive, lam, mdfa, mlam, classes, trace, cfg)

if "gen_result" in st.session_state:
    naive, lam, mdfa, mlam, classes, trace, cfg = st.session_state.gen_result

    c1, c2, c3 = st.columns(3)
    c1.metric("Naive states", len(naive.states))
    c2.metric("Minimal states", len(mdfa.states))
    g = min(cfg["coins"].values())
    c3.metric("Theorem: cap/g + 3", cfg["cap"] // g + 3,
              delta="matches" if len(mdfa.states) == cfg["cap"] // g + 3 else "mismatch")

    d1, d2 = st.columns(2)
    with d1:
        st.subheader("Naive DFA")
        st.graphviz_chart(to_dot(naive), use_container_width=True)
    with d2:
        st.subheader("Minimized DFA")
        st.graphviz_chart(to_dot(mdfa), use_container_width=True)

    from core.minimize import _label
    name_of = {q: _label(blk, naive) for blk in classes for q in blk}

    st.subheader("Equivalence classes (what merged)")
    st.dataframe(classes_table(classes, name_of), use_container_width=True, hide_index=True)

    st.subheader("Hopcroft refinement trace")
    st.dataframe(trace_table(trace), use_container_width=True, hide_index=True)

    st.subheader("Mealy output table (minimized machine)")
    rows = [{"state": q, "symbol": a, "output": mlam[(q, a)]}
            for q in sorted(mdfa.states) for a in sorted(mdfa.input_symbols)]
    st.dataframe(rows, use_container_width=True, hide_index=True, height=200)

    if st.button("Load this machine into the Simulator", type="primary"):
        st.session_state.machine = (mdfa, mlam, cfg)
        st.session_state.state = mdfa.initial_state
        st.session_state.log = []
        st.session_state.message = "Insert coins, then choose a product."
        st.switch_page("Simulator.py")
