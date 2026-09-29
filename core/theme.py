"""Shared look & feel for every page (frontend owner).

Edit ONLY the eight hex values below to re-colour the whole app. Everything
else (light-mode variants, borders, LCD, diagram colours) is derived from
them. This module never touches automaton logic: it styles pages and
post-processes the DOT text that core/render.py already produces.
"""
import re

import streamlit as st

# ── Palette: edit these ────────────────────────────────────────────────
PRIMARY = "#FF6F91"      # accents, current state, primary buttons
SECONDARY = "#74C7F5"    # last transition, links, info
BACKGROUND = "#0B1220"   # page background (dark)
PANEL = "#121C2E"        # cards / panels (dark)
TEXT = "#F7FAFF"         # body text (dark)
MUTED = "#9BAEC3"        # secondary text, idle edges
WARNING = "#FFB36B"      # warnings, trap state, insufficient balance
SUCCESS = "#7DE2B0"      # accept state, purchase, LCD digits
# ───────────────────────────────────────────────────────────────────────

MODES = ("dark", "light")
MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """Blend colour a toward b by fraction t (0 = a, 1 = b)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


def rgba(h, alpha):
    r, g, b = _rgb(h)
    return f"rgba({r},{g},{b},{alpha})"


def palette(mode="dark"):
    """Resolved colour tokens for a mode. *_ink = the colour to use for TEXT
    in that hue (pastels are darkened in light mode so they stay readable)."""
    lcd = {"lcd_bg": mix(BACKGROUND, "#000000", 0.35),
           "lcd_text": SUCCESS, "lcd_dim": mix(SUCCESS, BACKGROUND, 0.7)}
    if mode == "light":
        return {
            **lcd,
            "bg": TEXT, "panel": mix(TEXT, "#FFFFFF", 0.75),
            "raised": mix(TEXT, BACKGROUND, 0.04), "border": mix(TEXT, BACKGROUND, 0.14),
            "text": BACKGROUND, "muted": mix(MUTED, BACKGROUND, 0.5),
            "primary": PRIMARY, "primary_ink": mix(PRIMARY, BACKGROUND, 0.35),
            "secondary": SECONDARY, "secondary_ink": mix(SECONDARY, BACKGROUND, 0.5),
            "success": SUCCESS, "success_ink": mix(SUCCESS, BACKGROUND, 0.55),
            "warning": WARNING, "warning_ink": mix(WARNING, BACKGROUND, 0.5),
            "on_accent": BACKGROUND, "edge": mix(MUTED, BACKGROUND, 0.35),
        }
    return {
        **lcd,
        "bg": BACKGROUND, "panel": PANEL,
        "raised": mix(PANEL, TEXT, 0.05), "border": mix(PANEL, TEXT, 0.13),
        "text": TEXT, "muted": MUTED,
        "primary": PRIMARY, "primary_ink": PRIMARY,
        "secondary": SECONDARY, "secondary_ink": SECONDARY,
        "success": SUCCESS, "success_ink": SUCCESS,
        "warning": WARNING, "warning_ink": WARNING,
        "on_accent": BACKGROUND, "edge": MUTED,
    }


def get_mode():
    return st.session_state.get("theme_mode", "dark")


# ── Icons ──────────────────────────────────────────────────────────────
_ICONS = [
    (("chip", "crisp", "lays", "nacho"), "🍟"), (("juice", "orange"), "🧃"),
    (("choc", "candy", "kitkat", "bar"), "🍫"), (("cola", "soda", "coke", "pepsi"), "🥤"),
    (("water",), "💧"), (("coffee", "latte"), "☕"), (("tea", "chai"), "🍵"),
    (("cookie", "biscuit"), "🍪"), (("cake", "muffin"), "🧁"), (("gum", "mint"), "🍬"),
    (("sandwich",), "🥪"), (("popcorn",), "🍿"), (("milk",), "🥛"),
    (("apple", "fruit"), "🍎"), (("noodle", "maggi"), "🍜"), (("nut", "peanut"), "🥜"),
]


def icon_for(name):
    """Pick an emoji for a product name (fallback: a generic package)."""
    n = (name or "").lower()
    for words, emoji in _ICONS:
        if any(w in n for w in words):
            return emoji
    return "📦"


# ── Diagram styling (post-processes core.render.to_dot output) ─────────
def style_dot(dot, mode="dark", current=None, previous=None, last_symbol=None):
    """Re-colour a DOT string for the theme and highlight the last transition.

    current:  state to fill (render.to_dot already marks it with #FFD966)
    previous: state we came from — gets a secondary-colour outline
    (previous -> current) edge gets a thick secondary stroke.
    """
    p = palette(mode)
    head = ('graph [pad="0.15", nodesep="0.22", ranksep="0.32"];\n'
            f'node [color="{p["edge"]}", fontcolor="{p["text"]}", penwidth=1.3, '
            f'fontname="Helvetica", fontsize=16];\n'
            f'edge [color="{p["edge"]}", fontcolor="{p["muted"]}", arrowsize=0.8, fontsize=14];')
    anchor = 'edge [fontname="Helvetica", fontsize=9];'
    if anchor in dot:
        dot = dot.replace(anchor, anchor + "\n" + head, 1)
    else:
        dot = dot.replace("{", "{\n" + head, 1)
    # accept / trap state colours
    dot = dot.replace("[shape=doublecircle", f'[shape=doublecircle, color="{p["success_ink"]}"')
    dot = re.sub(r'^"q_dead" \[', f'"q_dead" [color="{p["warning_ink"]}", fontcolor="{p["warning_ink"]}", ',
                 dot, flags=re.M)
    # current-state fill (render.py uses #FFD966)
    dot = dot.replace('fillcolor="#FFD966"',
                      f'fillcolor="{p["primary"].lower()}", fontcolor="{p["on_accent"]}", '
                      f'color="{p["primary"].lower()}", penwidth=2')
    if previous and previous != current:
        dot = re.sub(r'^("%s" \[)' % re.escape(previous),
                     lambda m: m.group(1) + f'color="{p["secondary"]}", penwidth=2.2, ',
                     dot, flags=re.M)
    if previous and current:
        pat = r'^("%s" -> "%s" \[label=")([^"]*)("\])' % (re.escape(previous), re.escape(current))
        dot = re.sub(pat, lambda m: (m.group(1) + m.group(2) + '", color="'
                                     + p["secondary"] + '", fontcolor="' + p["secondary_ink"]
                                     + '", penwidth=2.6, fontname="Helvetica-Bold"]'),
                     dot, flags=re.M)
    return dot


# ── CSS ────────────────────────────────────────────────────────────────
def inject_css(mode=None, extra=""):
    """Inject the global stylesheet for `mode` (defaults to the session's)."""
    p = palette(mode or get_mode())
    v = "\n".join(f"  --vm-{k.replace('_', '-')}: {c};" for k, c in p.items())
    st.markdown(f"<style>\n:root, .stApp {{\n{v}\n}}\n{_CSS}\n{extra}\n</style>",
                unsafe_allow_html=True)


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

.stApp { background: var(--vm-bg); color: var(--vm-text); font-family: %(sans)s; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 2.2rem; max-width: 1400px; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--vm-text); font-family: %(sans)s; letter-spacing: -0.01em; }
.stApp h1 { font-size: 1.9rem; font-weight: 700; }
.stApp p, .stApp li, .stApp label, .stApp span { color: inherit; }
[data-testid="stCaptionContainer"], .stApp small { color: var(--vm-muted) !important; }
.stApp code { background: var(--vm-raised); color: var(--vm-primary-ink); border-radius: 4px; }
.stApp hr { border-color: var(--vm-border); }

/* sidebar */
[data-testid="stSidebar"] { background: var(--vm-panel); border-right: 1px solid var(--vm-border); }
[data-testid="stSidebar"] * { color: var(--vm-text); }
[data-testid="stSidebarNavLink"] { border-radius: 8px; }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: var(--vm-raised); box-shadow: inset 3px 0 0 var(--vm-primary); }

/* keyed section cards: st.container(key="card_*") */
[class*="st-key-card_"] { background: var(--vm-panel); border: 1px solid var(--vm-border);
  border-radius: 14px; padding: 1rem 1.1rem 1.1rem; }
.vm-label { font: 600 0.68rem/1 %(sans)s; letter-spacing: .12em; text-transform: uppercase;
  color: var(--vm-muted); margin: 0 0 .55rem; display: flex; align-items: center; gap: .45rem; }
.vm-label .dot { width: 6px; height: 6px; border-radius: 50%%; background: var(--vm-primary); }

/* buttons: tactile keys */
.stButton button, [data-testid="stDownloadButton"] > button, [data-testid="stFormSubmitButton"] > button {
  background: var(--vm-raised); color: var(--vm-text); border: 1px solid var(--vm-border);
  border-bottom-width: 3px; border-radius: 10px; font-weight: 600;
  transition: transform 80ms ease, border-color 120ms ease, background 120ms ease, box-shadow 120ms ease; }
.stButton button:hover, [data-testid="stDownloadButton"] > button:hover {
  border-color: var(--vm-primary); color: var(--vm-text); background: var(--vm-raised); }
.stButton button:active, [data-testid="stDownloadButton"] > button:active {
  transform: translateY(2px); border-bottom-width: 1px; margin-bottom: 2px; }
.stButton button:focus-visible { outline: 2px solid var(--vm-secondary); outline-offset: 2px; }
.stButton button p, [data-testid="stDownloadButton"] button p { color: inherit; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--vm-primary) !important; color: var(--vm-on-accent) !important;
  border-color: var(--vm-primary) !important; border-bottom-color: rgba(0,0,0,.28) !important; }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: var(--vm-on-accent) !important; }
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.06); }
[data-testid="stBaseButton-tertiary"] { color: var(--vm-muted); }

/* LCD */
.vm-lcd { background: var(--vm-lcd-bg); border: 1px solid var(--vm-border); border-radius: 10px;
  padding: .75rem .9rem; font-family: %(mono)s; color: var(--vm-lcd-text);
  box-shadow: inset 0 2px 10px rgba(0,0,0,.45); }
.vm-lcd .row { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }
.vm-lcd .big { font-size: 2.3rem; font-weight: 600; letter-spacing: .04em; line-height: 1.1;
  text-shadow: 0 0 10px rgba(125,226,176,.35); }
.vm-lcd .small { font-size: .78rem; color: var(--vm-lcd-dim); letter-spacing: .06em; text-transform: uppercase; }
.vm-lcd .msg { font-size: .85rem; margin-top: .35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vm-lcd .state { color: var(--vm-lcd-text); border: 1px solid var(--vm-lcd-dim); border-radius: 5px; padding: 0 .4rem; font-size: .85rem; }

/* monitor */
.vm-mon { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .5rem; }
.vm-cell.edge { grid-column: 1 / -1; display: flex; align-items: baseline; gap: .8rem; }
.vm-cell.edge .v { margin-top: 0; }
.vm-cell { background: var(--vm-lcd-bg); border: 1px solid var(--vm-border); border-radius: 8px; padding: .5rem .6rem; min-width: 0; }
.vm-cell .k { font: 600 .62rem/1 %(sans)s; letter-spacing: .1em; text-transform: uppercase; color: var(--vm-lcd-dim); }
.vm-cell .v { font: 600 1rem/1.35 %(mono)s; color: var(--vm-lcd-text); margin-top: .3rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vm-cell.cur .v { color: var(--vm-primary); }
.vm-cell.edge .v { color: var(--vm-secondary); font-size: .88rem; }
@media (max-width: 1100px) { .vm-mon { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.vm-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .6rem; }
.vm-chip { font: 500 .75rem/1 %(mono)s; padding: .32rem .5rem; border-radius: 6px; background: var(--vm-raised);
  border: 1px solid var(--vm-border); color: var(--vm-muted); }
.vm-chip b { color: var(--vm-text); font-weight: 600; }
.vm-chip.latest { border-color: var(--vm-secondary); color: var(--vm-text); }
.vm-chip.bad { border-color: var(--vm-warning); }
.vm-chip.ok { border-color: var(--vm-success); }

/* explainer */
.vm-exp .formal { font: 600 .95rem/1.5 %(mono)s; color: var(--vm-text); background: var(--vm-raised);
  border-left: 3px solid var(--vm-secondary); border-radius: 6px; padding: .45rem .7rem; margin: .1rem 0 .6rem; }
.vm-exp .formal .lam { color: var(--vm-muted); font-weight: 400; }
.vm-exp p { margin: 0 0 .45rem; line-height: 1.55; font-size: .92rem; }
.vm-exp .tag { display: inline-block; font: 600 .66rem/1 %(sans)s; letter-spacing: .08em; text-transform: uppercase;
  padding: .3rem .45rem; border-radius: 5px; margin-right: .35rem; }
.tag.coin { background: %(sec_a)s; color: var(--vm-secondary-ink); }
.tag.accept { background: %(suc_a)s; color: var(--vm-success-ink); }
.tag.trap { background: %(warn_a)s; color: var(--vm-warning-ink); }
.tag.cancel { background: var(--vm-raised); color: var(--vm-muted); }
.vm-exp .word { font-family: %(mono)s; font-size: .82rem; color: var(--vm-muted); }

/* legend + tables */
.vm-table { width: 100%%; border-collapse: collapse; font-size: .85rem; }
.vm-table th { text-align: left; font: 600 .66rem/1 %(sans)s; letter-spacing: .1em; text-transform: uppercase;
  color: var(--vm-muted); padding: .5rem .5rem; border-bottom: 1px solid var(--vm-border); }
.vm-table td { padding: .42rem .5rem; border-bottom: 1px solid var(--vm-border); color: var(--vm-text); vertical-align: top; }
.vm-table td.mono { font-family: %(mono)s; }
.vm-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 50%%; vertical-align: -1px; margin-right: .4rem; }
[data-testid="stTable"] table { background: var(--vm-panel); color: var(--vm-text); border-color: var(--vm-border); font-size: .85rem; }
[data-testid="stTable"] th { background: var(--vm-raised) !important; color: var(--vm-muted) !important; border-color: var(--vm-border) !important; }
[data-testid="stTable"] td { border-color: var(--vm-border) !important; color: var(--vm-text) !important; }

/* history */
.vm-hist { display: flex; flex-direction: column; gap: .5rem; }
.vm-tx { display: grid; grid-template-columns: auto 1fr auto; gap: .8rem; align-items: center; background: var(--vm-raised);
  border: 1px solid var(--vm-border); border-left: 3px solid var(--vm-muted); border-radius: 9px; padding: .55rem .75rem; }
.vm-tx.purchase { border-left-color: var(--vm-success); }
.vm-tx.cancel { border-left-color: var(--vm-secondary); }
.vm-tx.reject { border-left-color: var(--vm-warning); }
.vm-tx .ico { font-size: 1.35rem; width: 1.8rem; text-align: center; }
.vm-tx .t { font-weight: 600; font-size: .92rem; }
.vm-tx .d { color: var(--vm-muted); font-size: .8rem; margin-top: .1rem; font-family: %(mono)s; }
.vm-tx .r { text-align: right; font-family: %(mono)s; font-size: .8rem; color: var(--vm-muted); }
.vm-tx .r b { display: block; color: var(--vm-text); font-size: .95rem; }
.vm-empty { color: var(--vm-muted); font-size: .88rem; padding: .6rem 0; }

/* alerts (status) */
[data-testid="stAlertContainer"] { background: var(--vm-raised) !important; border: 1px solid var(--vm-border); border-radius: 10px; color: var(--vm-text) !important; }
[data-testid="stAlertContainer"] p { color: var(--vm-text) !important; }
.st-key-status_success [data-testid="stAlertContainer"] { border-color: var(--vm-success); background: %(suc_a)s !important; }
.st-key-status_error [data-testid="stAlertContainer"] { border-color: var(--vm-warning); background: %(warn_a)s !important; }
.st-key-status_info [data-testid="stAlertContainer"] { border-color: var(--vm-secondary); background: %(sec_a)s !important; }

/* metrics, expanders, inputs, forms, tabs, dialog, toast */
[data-testid="stMetric"] { background: var(--vm-raised); border: 1px solid var(--vm-border); border-radius: 10px; padding: .55rem .7rem; }
[data-testid="stMetricLabel"] p { color: var(--vm-muted) !important; font-size: .74rem; }
[data-testid="stMetricValue"] { color: var(--vm-text); font-family: %(mono)s; font-size: 1.35rem; }
[data-testid="stExpander"] details { background: var(--vm-panel); border: 1px solid var(--vm-border); border-radius: 10px; }
[data-testid="stExpander"] summary { color: var(--vm-text); }
[data-testid="stExpander"] summary:hover { color: var(--vm-primary-ink); }
[data-testid="stForm"] { background: var(--vm-panel); border: 1px solid var(--vm-border); border-radius: 14px; }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, .stApp input, .stApp textarea {
  background: var(--vm-raised) !important; color: var(--vm-text) !important; border-color: var(--vm-border) !important; }
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] { background: var(--vm-raised); color: var(--vm-text); }
.stApp input::placeholder { color: var(--vm-muted) !important; opacity: .7; }
[data-testid="stTab"] p { color: var(--vm-muted); }
[data-testid="stTab"][aria-selected="true"] p { color: var(--vm-text); }
[data-baseweb="tab-highlight"] { background: var(--vm-primary) !important; }
[data-testid="stDialog"] [role="dialog"] { background: var(--vm-panel); color: var(--vm-text); border: 1px solid var(--vm-border); border-radius: 16px; }
[data-testid="stDialog"] [role="dialog"] * { color: inherit; }
[data-testid="stToast"] { background: var(--vm-panel) !important; border: 1px solid var(--vm-border); color: var(--vm-text); }
[data-testid="stToast"] * { color: var(--vm-text) !important; }
[data-testid="stGraphVizChart"] { background: transparent; }
[data-testid="stCheckbox"] label p, [data-testid="stWidgetLabel"] p { color: var(--vm-text); }

/* diagram: pulse the active node (fill set by style_dot) */
[data-testid="stGraphVizChart"] svg g.node ellipse[fill="%(primary_l)s"] { animation: vm-pulse 1.6s ease-in-out 2; transform-box: fill-box; transform-origin: center; }
@keyframes vm-pulse { 0%%,100%% { stroke-width: 2; } 50%% { stroke-width: 6; stroke-opacity: .5; } }

/* micro-interactions: fx containers get a fresh key per step so they replay */
@keyframes vm-tick { 0%% { transform: scale(1); } 35%% { transform: scale(1.035); } 100%% { transform: scale(1); } }
@keyframes vm-shake { 0%%,100%% { transform: translateX(0); } 25%% { transform: translateX(-5px); } 50%% { transform: translateX(4px); } 75%% { transform: translateX(-2px); } }
@keyframes vm-flash-ok { 0%% { box-shadow: 0 0 0 0 %(suc_b)s; } 100%% { box-shadow: 0 0 0 14px rgba(0,0,0,0); } }
@keyframes vm-flash-sel { 0%% { box-shadow: 0 0 0 0 %(sec_b)s; } 100%% { box-shadow: 0 0 0 12px rgba(0,0,0,0); } }
@keyframes vm-fade-in { from { opacity: .35; transform: translateY(3px); } to { opacity: 1; transform: none; } }
[class*="st-key-fx_coin"] .vm-lcd .big { animation: vm-tick 220ms ease-out; }
[class*="st-key-fx_coin"] .vm-lcd { animation: vm-flash-sel 420ms ease-out; }
[class*="st-key-fx_accept"] .vm-lcd { animation: vm-flash-ok 600ms ease-out; border-color: var(--vm-success); }
[class*="st-key-fx_trap"] .vm-lcd { animation: vm-shake 260ms ease-in-out; border-color: var(--vm-warning); }
[class*="st-key-fx_trap"] .vm-lcd .big, [class*="st-key-fx_trap"] .vm-lcd .msg { color: var(--vm-warning); }
[class*="st-key-fx_cancel"] .vm-lcd .big { animation: vm-fade-in 260ms ease-out; }
[class*="st-key-fx_"] .vm-cell.edge, [class*="st-key-fx_"] .vm-chip.latest, [class*="st-key-fx_"] .vm-tx:first-child { animation: vm-fade-in 260ms ease-out; }
@media (prefers-reduced-motion: reduce) { .stApp *, .stApp *::before { animation: none !important; transition: none !important; } }

/* tutorial */
.vm-tut { text-align: center; padding: .4rem 0 .2rem; }
.vm-tut .step-ico { width: 64px; height: 64px; margin: 0 auto .7rem; border-radius: 50%%; display: grid; place-items: center;
  font-size: 1.9rem; background: var(--vm-raised); border: 1px solid var(--vm-border); }
.vm-tut .n { font: 600 .7rem/1 %(sans)s; letter-spacing: .14em; text-transform: uppercase; color: var(--vm-primary-ink); }
.vm-tut h3 { margin: .35rem 0 .45rem; font-size: 1.3rem; }
.vm-tut p { color: var(--vm-muted); font-size: .93rem; line-height: 1.55; margin: 0 auto; max-width: 30rem; }
.vm-tut .formal { font-family: %(mono)s; color: var(--vm-text); font-size: .88rem; margin-top: .55rem; }
.vm-dots { display: flex; justify-content: center; gap: .45rem; margin: 1rem 0 .3rem; }
.vm-dots span { width: 8px; height: 8px; border-radius: 50%%; background: var(--vm-border); transition: all 150ms; }
.vm-dots span.on { background: var(--vm-primary); width: 22px; border-radius: 4px; }
.vm-dots span.done { background: var(--vm-muted); }
"""


def _fill_css():
    """Resolve %-placeholders that depend on fixed palette values."""
    global _CSS
    _CSS = _CSS % {
        "sans": SANS, "mono": MONO,
        "sec_a": rgba(SECONDARY, 0.14), "suc_a": rgba(SUCCESS, 0.14), "warn_a": rgba(WARNING, 0.14),
        "sec_b": rgba(SECONDARY, 0.45), "suc_b": rgba(SUCCESS, 0.5),
        "primary_l": PRIMARY.lower(),
    }


_fill_css()
