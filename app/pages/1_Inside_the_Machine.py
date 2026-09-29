"""Inside the Machine — cinematic, scroll-driven explainer (frontend only).

A full-screen HTML/Three.js experience embedded in Streamlit. It never
re-implements the automaton: the machine it animates is produced here by the
existing backend (core.generator.build + core.minimize.to_minimal, called
read-only) and handed to the page as JSON. If the Generator page loaded a
custom machine into the session, that machine is shown instead.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from streamlit.errors import StreamlitPageNotFoundError  # noqa: E402

from core import theme  # noqa: E402
from core.generator import build, load_config  # noqa: E402
from core.minimize import to_minimal  # noqa: E402

st.set_page_config(page_title="Inside the Machine", page_icon="🥤", layout="wide",
                   initial_sidebar_state="collapsed")

WEB = ROOT / "web"


def machine_payload(cfg):
    """Serialize the backend's own machine for the browser (read-only use)."""
    naive, lam, cfg = build(cfg)
    dfa, mlam, classes, trace = to_minimal(naive, lam)
    from core.minimize import _label
    return {
        "cfg": cfg,
        "start": dfa.initial_state,
        "final": sorted(dfa.final_states),
        "states": sorted(dfa.states),
        "symbols": sorted(dfa.input_symbols),
        "delta": {q: dict(row) for q, row in dfa.transitions.items()},
        "lambda": {q: {a: mlam[(q, a)] for a in dfa.input_symbols} for q in dfa.states},
        "naive": {
            "states": sorted(naive.states),
            "final": sorted(naive.final_states),
            "classes": [sorted(b) for b in classes],
            "name_of": {q: _label(b, naive) for b in classes for q in b},
            "steps": len(trace),
        },
    }


def palette_css():
    p = theme
    return (f"--primary:{p.PRIMARY};--secondary:{p.SECONDARY};--bg:{p.BACKGROUND};"
            f"--panel:{p.PANEL};--text:{p.TEXT};--muted:{p.MUTED};--warning:{p.WARNING};"
            f"--success:{p.SUCCESS};")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def render_html(payload):
    html = _read(str(WEB / "experience.html"))
    three = _read(str(WEB / "vendor" / "three.min.js"))
    app = _read(str(WEB / "experience.js"))
    return (html.replace("/*__PALETTE__*/", palette_css())
                .replace("/*__MACHINE__*/null", json.dumps(payload, ensure_ascii=False))
                .replace("/*__APP__*/", app)
                .replace("/*__THREE__*/", three))


cfg = (st.session_state.machine[2] if "machine" in st.session_state
       else load_config(ROOT / "spec" / "config.json"))
html = render_html(machine_payload(cfg))

# Full-bleed stage: the experience owns the whole viewport.
st.markdown("""<style>
[data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: none !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stAppViewContainer"], .stApp { background: %s; }
[data-testid="stIFrame"], .stApp iframe { height: 100vh !important; width: 100%% !important;
  display: block; border: 0; }
[data-testid="stMain"] { overflow: hidden; }
</style>""" % theme.BACKGROUND, unsafe_allow_html=True)

with st.sidebar:
    st.caption("Showing the machine currently loaded in this session. Build a different "
               "one on the Generator page and it appears here too.")
    st.download_button("Download offline copy (HTML)", html, "state_machine.html", "text/html",
                       width="stretch", icon=":material/download:",
                       help="A single file that opens in any browser, with no Python or internet "
                            "needed. Handy as a viva backup.")

st.iframe(html, height=900)

# ── Dashboard dock (added): top-left entry into the Streamlit dashboard ──
# Native page links, so switching pages keeps this session's machine,
# history and stats. Pinned above the experience; the experience is untouched.
st.markdown("""<style>
.st-key-vm_dock { position: fixed; top: 12px; left: 56px; z-index: 999990; width: auto !important;
  display: flex; flex-direction: row; align-items: center; gap: 6px; padding: 5px 6px 5px 12px;
  background: rgba(18,28,46,.88); border: 1px solid rgba(155,174,195,.22); border-radius: 12px;
  backdrop-filter: blur(6px); }
.st-key-vm_dock .vm-dock-label { font: 600 11px/1 'IBM Plex Mono', ui-monospace, monospace;
  letter-spacing: .14em; text-transform: uppercase; color: %(muted)s; margin-right: 4px; white-space: nowrap; }
.st-key-vm_dock [data-testid="stElementContainer"], .st-key-vm_dock [data-testid="stPageLink"] { width: auto !important; margin: 0; }
.st-key-vm_dock [data-testid="stMarkdownContainer"] p { margin: 0; }
.st-key-vm_dock > div, .st-key-vm_dock [data-testid="stElementContainer"] { align-self: center; height: auto !important; }
.st-key-vm_dock [data-testid="stMarkdownContainer"] { display: flex; align-items: center; margin: 0 !important; }
.st-key-vm_dock a[data-testid="stPageLink-NavLink"] { background: %(panel)s; border: 1px solid rgba(155,174,195,.22);
  border-bottom: 3px solid rgba(0,0,0,.5); border-radius: 9px; padding: 4px 11px; margin: 0;
  transition: transform .07s ease, border-color .15s ease; }
.st-key-vm_dock a[data-testid="stPageLink-NavLink"]:hover { border-color: %(primary)s; background: %(panel)s; }
.st-key-vm_dock a[data-testid="stPageLink-NavLink"]:active { transform: translateY(2px); border-bottom-width: 1px; }
.st-key-vm_dock a[data-testid="stPageLink-NavLink"] p, .st-key-vm_dock a[data-testid="stPageLink-NavLink"] span {
  color: %(text)s !important; font-weight: 600; font-size: 14px; }
@media (max-width: 640px) { .st-key-vm_dock .vm-dock-label { display: none; } }
</style>""" % {"muted": theme.MUTED, "panel": theme.PANEL, "primary": theme.PRIMARY, "text": theme.TEXT},
            unsafe_allow_html=True)

with st.container(key="vm_dock", horizontal=True):
    st.markdown('<span class="vm-dock-label">Dashboard</span>', unsafe_allow_html=True)
    try:
        st.page_link("Simulator.py", label="Simulator", icon=":material/joystick:")
        st.page_link("pages/Generator.py", label="Generator", icon=":material/build:")
    except StreamlitPageNotFoundError:   # page run on its own (e.g. in a unit test)
        pass
