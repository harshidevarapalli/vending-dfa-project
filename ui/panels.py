"""Reusable UI panels for the Simulator and Generator pages (frontend owner).

Pure presentation: every function reads session state / the machine and
renders HTML or Streamlit widgets. No automaton logic lives here.
"""
from html import escape

import streamlit as st

from core.theme import get_mode, icon_for, palette
from ui.session import balance_of, stats, symbol_label, to_csv


def label(text):
    """Small uppercase section label with an accent dot."""
    st.markdown(f'<div class="vm-label"><span class="dot"></span>{escape(text)}</div>',
                unsafe_allow_html=True)


# ── top bar: title + tutorial + theme toggle ───────────────────────────
def _toggle_theme():
    st.session_state.theme_mode = "dark" if st.session_state.theme_toggle else "light"


def open_tutorial():
    st.session_state.tutorial_open = True
    st.session_state.tutorial_step = 0


def top_bar(title, caption=None, tutorial=True):
    c1, c2, c3 = st.columns([7, 1.25, 1.25], vertical_alignment="center")
    with c1:
        st.title(title)
        if caption:
            st.caption(caption)
    if tutorial:
        c2.button("Tutorial", key="btn_tutorial", icon=":material/help:",
                  on_click=open_tutorial, width="stretch",
                  help="Reopen the 4-step walkthrough")
    c3.toggle("Dark mode", key="theme_toggle", value=get_mode() == "dark",
              on_change=_toggle_theme)


# ── LCD machine status ─────────────────────────────────────────────────
def lcd(state, message, dfa):
    bal = balance_of(state)
    if state in dfa.final_states:
        big, tag = "SOLD", "ACCEPTED"
    elif state == "q_dead":
        big, tag = "ERROR", "TRAP"
    else:
        big, tag = f"₹{bal if bal is not None else '—'}", "CREDIT"
    st.markdown(
        f'<div class="vm-lcd"><div class="row"><span class="small">{tag}</span>'
        f'<span class="state">{escape(state)}</span></div>'
        f'<div class="big">{escape(big)}</div>'
        f'<div class="msg">&gt; {escape(message)}</div></div>',
        unsafe_allow_html=True)


# ── Automaton monitor ──────────────────────────────────────────────────
def monitor(state, cfg, log):
    last = st.session_state.get("last")
    bal = balance_of(state)
    prev = last["prev"] if last else "—"
    sym = last["symbol"] if last else "—"
    edge = f"δ({last['prev']}, {last['symbol']}) = {last['next']}" if last else "—"
    cells = [
        ("State", state, "cur"), ("Previous", prev, ""),
        ("Last input", sym, ""), ("Balance", f"₹{bal}" if bal is not None else "—", ""),
        ("Transition", edge, "edge"),
    ]
    html = '<div class="vm-mon">' + "".join(
        f'<div class="vm-cell {cls}"><div class="k">{k}</div>'
        f'<div class="v" title="{escape(str(v))}">{escape(str(v))}</div></div>'
        for k, v, cls in cells) + "</div>"
    recent = log[-6:]
    if recent:
        chips = []
        for i, r in enumerate(recent):
            cls = "latest" if i == len(recent) - 1 else ""
            if r["next"] == "q_dead":
                cls += " bad"
            elif r["next"] == "q_done" or r["next"].startswith("done_"):
                cls += " ok"
            chips.append(f'<span class="vm-chip {cls}">{escape(r["state"])} '
                         f'—<b>{escape(r["input"])}</b>→ {escape(r["next"])}</span>')
        html += '<div class="vm-chips">' + "".join(chips) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── "How the DFA works" explainer ──────────────────────────────────────
def _affordable(cfg, bal):
    return [p["name"] for p in cfg["products"].values() if p["price"] <= bal]


def explain(dfa, cfg, state, log):
    last = st.session_state.get("last")
    word = " ".join(r["input"] for r in log) or "ε"
    if not last:
        sigma = ", ".join(sorted(dfa.input_symbols))
        cheapest = min(p["price"] for p in cfg["products"].values())
        body = (f'<div class="formal">{escape(dfa.initial_state)} &nbsp;<span class="lam">'
                f'start state, balance ₹0</span></div>'
                f"<p>Every button is one <b>input symbol</b> from Σ = {{{escape(sigma)}}}. "
                f"The DFA reads it and follows exactly <b>one</b> arrow; that's what "
                f"<i>deterministic</i> means.</p>"
                f"<p>Insert coins until the balance reaches a product's price "
                f"(cheapest ₹{cheapest}), then choose it.</p>")
        st.markdown(f'<div class="vm-exp">{body}</div>', unsafe_allow_html=True)
        return

    prev, sym, nxt, out, kind = (last[k] for k in ("prev", "symbol", "next", "output", "kind"))
    b0, b1 = balance_of(prev), balance_of(nxt)
    formal = (f'<div class="formal">δ({escape(prev)}, {escape(sym)}) = {escape(nxt)}'
              f' &nbsp;<span class="lam">λ = {escape(out)}</span></div>')
    if kind == "coin":
        can = _affordable(cfg, b1)
        hint = (f"You can now afford: <b>{escape(', '.join(can))}</b>." if can
                else "Not enough for any product yet. Keep inserting coins.")
        text = (f'<span class="tag coin">coin</span>You inserted a {escape(symbol_label(cfg, sym))}. '
                f"A DFA has no memory except its current state, so “the balance is ₹{b1}” "
                f"is stored entirely as <b>being in {escape(nxt)}</b>.</p><p>{hint}")
    elif kind == "cancel":
        text = (f'<span class="tag cancel">cancel</span>Cancel sends every balance state back '
                f"to the start: δ(q<sub>b</sub>, cancel) = q0. The Mealy output refunds "
                f"₹{b0 or 0}, and the machine “forgets” the coins. The input string keeps going.")
    elif kind == "accept":
        text = (f'<span class="tag accept">accepted</span><b>{escape(nxt)}</b> is an accepting '
                f"state (double circle), so the input string <b>w ∈ L(M)</b>, a valid "
                f"transaction. The Mealy layer turns that into a physical output: "
                f"<b>{escape(out)}</b>.</p><p>Any further input goes to the trap: one string = "
                f"one transaction. Press <b>Reset</b> for the next customer.")
    elif kind == "trap" and sym in cfg["coins"]:
        v = cfg["coins"][sym]
        text = (f'<span class="tag trap">trap</span>₹{b0} + ₹{v} = ₹{b0 + v} would exceed the '
                f"₹{cfg['cap']} cap. The cap is exactly what keeps the set of states "
                f"<b>finite</b>, so overflowing goes to the trap <b>q_dead</b> and λ returns the coin.")
    elif kind == "trap":
        p = cfg["products"][sym]
        text = (f'<span class="tag trap">trap</span>{escape(p["name"])} costs ₹{p["price"]} but the '
                f"balance is only ₹{b0}. Selecting it sends the DFA to <b>q_dead</b>, a trap "
                f"state whose every arrow loops back to itself, so this string can never be "
                f"accepted. Press <b>Reset</b>.")
    else:
        text = (f'<span class="tag trap">blocked</span>The machine was already in '
                f"<b>{escape(prev)}</b>. Both q_done and q_dead send every symbol to q_dead: "
                f"the transaction is over. Press <b>Reset</b> to start a new input string.")
    verdict = "in F (accepting)" if nxt in dfa.final_states else "not in F"
    st.markdown(f'<div class="vm-exp">{formal}<p>{text}</p>'
                f'<div class="word">w = {escape(word)} · current state {verdict}</div></div>',
                unsafe_allow_html=True)


def _state_key(q):
    b = balance_of(q)
    return (0, b) if b is not None else (1 if q != "q_dead" else 2, 0)


def legend(dfa, cfg):
    p = palette(get_mode())
    rows = []
    for q in sorted(dfa.states, key=_state_key):
        b = balance_of(q)
        if q == dfa.initial_state:
            meaning, look = "Start: balance ₹0", "arrow from a dot"
        elif b is not None:
            meaning, look = f"Balance ₹{b} inserted so far", "circle"
        elif q in dfa.final_states:
            meaning, look = "Purchase complete (accepting)", "double circle"
        elif q == "q_dead":
            meaning, look = "Trap: illegal input, no way out", "dashed circle"
        else:
            meaning, look = "Merged state", "circle"
        rows.append(f'<tr><td class="mono">{escape(q)}</td><td>{meaning}</td><td>{look}</td></tr>')
    colors = [(p["primary"], "Current state (filled)"), (p["secondary"], "Previous state + last transition"),
              (p["success_ink"], "Accepting state"), (p["warning_ink"], "Trap state")]
    key = "".join(f'<tr><td><span class="vm-swatch" style="background:{c}"></span></td>'
                  f'<td colspan="2">{t}</td></tr>' for c, t in colors)
    st.markdown(
        '<table class="vm-table"><thead><tr><th>State</th><th>Meaning</th><th>Drawn as</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'<table class="vm-table" style="margin-top:.6rem"><thead><tr><th colspan="3">Colour key'
        f'</th></tr></thead><tbody>{key}</tbody></table>',
        unsafe_allow_html=True)


# ── Transaction history ────────────────────────────────────────────────
def history(cfg, limit=8):
    h = st.session_state.get("history", [])
    started = st.session_state.get("session_started")
    s = stats()
    st.caption(f"Session started {started:%H:%M} · {s['transactions']} transactions · "
               f"{s['purchases']} purchases")
    if not h:
        st.markdown('<div class="vm-empty">No finished transactions yet. Buy something, '
                    'cancel, or trigger a rejection and it appears here.</div>',
                    unsafe_allow_html=True)
        return
    cards = []
    for e in reversed(h[-limit:]):
        coins = " + ".join(f"₹{c}" for c in e["coins"]) or "no coins"
        if e["kind"] == "purchase":
            ico = icon_for(e["title"])
            right = f'<b>₹{e["price"]}</b>change ₹{e["change"]}'
        elif e["kind"] == "cancel":
            ico, right = "↩", f'<b>₹{e["refund"]}</b>refunded'
        else:
            ico, right = "⚠", f'<b>₹{e["paid"]}</b>balance'
        cards.append(
            f'<div class="vm-tx {e["kind"]}"><div class="ico">{ico}</div><div>'
            f'<div class="t">{escape(e["title"])}</div>'
            f'<div class="d">{escape(coins)} · w = {escape(e["word"])}</div></div>'
            f'<div class="r">{right}<br>{e["started"]}–{e["time"]}</div></div>')
    st.markdown('<div class="vm-hist">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    if len(h) > limit:
        st.caption(f"Showing the latest {limit} of {len(h)}. Download the CSV for all.")


# ── Sidebar stats ──────────────────────────────────────────────────────
def sidebar_stats(log):
    s = stats()
    with st.sidebar:
        label("Session statistics")
        a, b = st.columns(2)
        a.metric("Purchases", s["purchases"])
        b.metric("Revenue", f"₹{s['revenue']}")
        a.metric("Change given", f"₹{s['change']}")
        b.metric("Refunded", f"₹{s['refunds']}")
        a.metric("Rejected", s["rejected"])
        b.metric("Steps", s["steps"])
        rate = f"{100 * s['purchases'] / s['transactions']:.0f}%" if s["transactions"] else "—"
        st.caption(f"Acceptance rate: {rate} of finished transactions")
        label("Export")
        st.download_button("Step log (CSV)", to_csv(log), "step_log.csv", "text/csv",
                           key="dl_log", disabled=not log, width="stretch",
                           icon=":material/download:")
        hist = [{k: e[k] for k in ("started", "time", "kind", "title", "coins", "price",
                                   "change", "refund", "word")}
                for e in st.session_state.get("history", [])]
        st.download_button("Transactions (CSV)", to_csv(hist), "transactions.csv", "text/csv",
                           key="dl_hist", disabled=not hist, width="stretch",
                           icon=":material/download:")


def html_table(rows, mono_cols=()):
    """Theme-aware static table for small lists of dicts."""
    if not rows:
        return
    cols = list(rows[0].keys())
    head = "".join(f"<th>{escape(str(c))}</th>" for c in cols)
    body = "".join(
        "<tr>" + "".join(f'<td class="{"mono" if c in mono_cols else ""}">{escape(str(r[c]))}</td>'
                         for c in cols) + "</tr>" for r in rows)
    st.markdown(f'<table class="vm-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True)
