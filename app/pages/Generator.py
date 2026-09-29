"""Machine generator: any coin set + product list -> naive DFA, minimized DFA,
Hopcroft trace, Mealy table. Can push the result into the Simulator page.

Run via: streamlit run app/Simulator.py   (this page appears in the sidebar)
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.generator import ConfigError, build  # noqa: E402
from core.minimize import to_minimal  # noqa: E402
from core.render import classes_table, to_dot, trace_table  # noqa: E402
from core.theme import get_mode, inject_css, style_dot  # noqa: E402
from ui import panels  # noqa: E402
from ui.session import init_ui_state, on_reset, to_csv  # noqa: E402

st.set_page_config(page_title="Machine Generator", page_icon="🛠️", layout="wide")
init_ui_state()
inject_css(get_mode())
panels.top_bar("Build any vending machine",
               "Enter coins and products. The generator builds the naive DFA, "
               "minimizes it with Hopcroft's algorithm, and shows both.", tutorial=False)

if "gen_coins" not in st.session_state:
    st.session_state.gen_coins = [("c5", 5), ("c10", 10)]
if "gen_products" not in st.session_state:
    st.session_state.gen_products = [("s1", "Chips", 10), ("s2", "Juice", 15),
                                      ("s3", "Chocolate", 20)]
if "gen_cap" not in st.session_state:
    st.session_state.gen_cap = 25

_NAMES = ["Chips", "Juice", "Chocolate", "Cola", "Water", "Coffee", "Cookie", "Gum",
          "Popcorn", "Tea"]


def _sync_widgets(overwrite=False):
    """Copy gen_coins / gen_products / gen_cap into the form widgets' state."""
    coins, prods = st.session_state.gen_coins, st.session_state.gen_products
    vals = {"gen_cap_input": st.session_state.gen_cap}
    for i in range(4):
        c = coins[i] if i < len(coins) else ("", 0)
        p = prods[i] if i < len(prods) else ("", "", 0)
        vals.update({f"coin_sym_{i}": c[0], f"coin_val_{i}": c[1], f"prod_sym_{i}": p[0],
                     f"prod_name_{i}": p[1], f"prod_price_{i}": p[2]})
    for k, v in vals.items():
        if overwrite or k not in st.session_state:
            st.session_state[k] = v


def randomize():
    """Fill the form with a random *valid* configuration and generate it."""
    coins = [("c5", 5)] + random.sample([("c10", 10), ("c20", 20)], k=random.randint(1, 2))
    coins.sort(key=lambda c: c[1])
    cap = random.choice([20, 25, 30, 35, 40])
    names = random.sample(_NAMES, k=random.randint(2, 4))
    prods = [(f"s{i + 1}", n, 5 * random.randint(1, cap // 5)) for i, n in enumerate(names)]
    st.session_state.gen_coins, st.session_state.gen_products = coins, prods
    st.session_state.gen_cap = cap
    _sync_widgets(overwrite=True)
    cfg = {"coins": dict(coins), "cap": cap,
           "products": {s: {"name": n, "price": p} for s, n, p in prods}}
    naive, lam, cfg = build(cfg)
    mdfa, mlam, classes, trace = to_minimal(naive, lam)
    st.session_state.gen_result = (naive, lam, mdfa, mlam, classes, trace, cfg)


_sync_widgets()
st.button("Randomize", key="btn_randomize", on_click=randomize, icon=":material/casino:",
          help="Fill the form with a random valid machine and generate it")

with st.form("config_form"):
    fc, fp = st.columns([2, 3], gap="large")
    coin_rows = []
    with fc:
        panels.label("Coins")
        for i in range(4):
            c1, c2 = st.columns(2)
            sym = c1.text_input(f"Symbol {i + 1}", key=f"coin_sym_{i}",
                                placeholder="c5")
            val = c2.number_input(f"Value ₹ {i + 1}", min_value=0, step=5,
                                  key=f"coin_val_{i}")
            if sym and val:
                coin_rows.append((sym, val))
        cap = st.number_input("Balance cap ₹", min_value=5, step=5, key="gen_cap_input")

    prod_rows = []
    with fp:
        panels.label("Products")
        for i in range(4):
            c1, c2, c3 = st.columns(3)
            sym = c1.text_input(f"Symbol {i + 1}", key=f"prod_sym_{i}",
                                placeholder="s1")
            name = c2.text_input(f"Name {i + 1}", key=f"prod_name_{i}",
                                 placeholder="Chips")
            price = c3.number_input(f"Price ₹ {i + 1}", min_value=0, step=5,
                                    key=f"prod_price_{i}")
            if sym and name and price:
                prod_rows.append((sym, name, price))

    submitted = st.form_submit_button("Generate", type="primary", icon=":material/build:")

if submitted:
    st.session_state.gen_coins = coin_rows
    st.session_state.gen_products = [(s, n, p) for s, n, p in prod_rows]
    st.session_state.gen_cap = int(cap)
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
    mode = get_mode()

    c1, c2, c3 = st.columns(3)
    c1.metric("Naive states", len(naive.states))
    c2.metric("Minimal states", len(mdfa.states))
    g = min(cfg["coins"].values())
    c3.metric("Theorem: cap/g + 3", cfg["cap"] // g + 3,
              delta="matches" if len(mdfa.states) == cfg["cap"] // g + 3 else "mismatch")

    d1, d2 = st.columns(2, gap="large")
    with d1:
        with st.container(key="card_naive"):
            panels.label("Naive DFA")
            st.graphviz_chart(style_dot(to_dot(naive), mode), width="stretch")
    with d2:
        with st.container(key="card_min"):
            panels.label("Minimized DFA")
            st.graphviz_chart(style_dot(to_dot(mdfa), mode), width="stretch")

    from core.minimize import _label
    name_of = {q: _label(blk, naive) for blk in classes for q in blk}
    cls_rows = classes_table(classes, name_of)
    tr_rows = trace_table(trace)
    mealy_rows = [{"state": q, "symbol": a, "output": mlam[(q, a)]}
                  for q in sorted(mdfa.states) for a in sorted(mdfa.input_symbols)]

    tabs = st.tabs(["Equivalence classes", "Hopcroft trace", "Mealy output table"])
    for tab, rows, fname, mono in (
            (tabs[0], cls_rows, "equivalence_classes.csv", ("minimal state", "merged from")),
            (tabs[1], tr_rows, "hopcroft_trace.csv", ("splitter", "block split", "into")),
            (tabs[2], mealy_rows, "mealy_table.csv", ("state", "symbol"))):
        with tab:
            st.download_button("Download CSV", to_csv(rows), fname, "text/csv",
                               key=f"dl_{fname}", icon=":material/download:",
                               disabled=not rows)
            if rows:
                with st.container(height=min(420, 60 + 38 * len(rows)), border=False):
                    panels.html_table(rows, mono_cols=mono)
            else:
                st.caption("Nothing to show: no refinement steps were needed.")

    if st.button("Load this machine into the Simulator", type="primary",
                 icon=":material/play_arrow:"):
        st.session_state.machine = (mdfa, mlam, cfg)
        st.session_state.state = mdfa.initial_state
        st.session_state.log = []
        st.session_state.message = "Insert coins, then choose a product."
        on_reset()
        st.switch_page("Simulator.py")
