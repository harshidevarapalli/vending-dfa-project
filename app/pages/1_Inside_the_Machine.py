"""Inside the Machine — the immersive HTML front end (frontend only).

A full-screen HTML/Three.js experience with its own sidebar, Simulator and
Generator, embedded as a two-way Streamlit component. It never re-implements
the automaton:

* the machine it animates comes from core.generator.build +
  core.minimize.to_minimal (called read-only, via ui.gen_service);
* the HTML Generator sends its form here, and this page answers with the
  output of those same backend functions and the core.render tables;
* "Load into Simulator" puts the machine into st.session_state exactly like
  the Streamlit Generator page does, so every page shares it.

The downloadable offline copy bakes in the default machine plus a set of
machines pre-built by the same backend code.
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
from ui import gen_service  # noqa: E402
from ui.session import init_ui_state, on_reset  # noqa: E402

st.set_page_config(page_title="Inside the Machine", page_icon="🥤", layout="wide",
                   initial_sidebar_state="collapsed")

WEB = ROOT / "web"
DEFAULT_CFG = ROOT / "spec" / "config.json"

# Kept for anything that imported it from here before the refactor.
machine_payload = gen_service.machine_payload


def palette():
    return {"primary": theme.PRIMARY, "secondary": theme.SECONDARY, "bg": theme.BACKGROUND,
            "panel": theme.PANEL, "text": theme.TEXT, "muted": theme.MUTED,
            "warning": theme.WARNING, "success": theme.SUCCESS}


def _read(path):
    return Path(path).read_text(encoding="utf-8")


# ── offline single-file build ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _prebuilt(cfg_json):
    return gen_service.prebuilt(json.loads(cfg_json), n=12)


def render_html(payload, prebuilt=None):
    """Inline every asset into ONE file that opens without Python or internet."""
    html = _read(str(WEB / "index.html"))
    for tag, path in (('<link rel="stylesheet" href="views.css">', "views.css"),):
        html = html.replace(tag, "<style>\n" + _read(str(WEB / path)) + "\n</style>")
    for src in ("vendor/three.min.js", "experience.js", "views.js", "boot.js"):
        html = html.replace(f'<script src="{src}"></script>',
                            "<script>\n" + _read(str(WEB / src)) + "\n</script>")
    data = {"machine": payload, "palette": palette(), "default_form": gen_service.DEFAULT_FORM,
            "prebuilt": prebuilt or []}
    css_vars = "".join(f"--{k}:{v};" for k, v in palette().items())
    return (html.replace("/*__PALETTE__*/", css_vars)
                .replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))


# ── live two-way component ─────────────────────────────────────────────
from ui.experience_component import experience as _experience  # noqa: E402


def handle(req):
    """Answer one request from the HTML UI using the backend (read-only)."""
    op, data = req.get("op"), req.get("data") or {}
    if op == "generate":
        return gen_service.generate(data.get("cfg") or {})
    if op == "randomize":
        return gen_service.generate(gen_service.random_config())
    if op == "load":
        # Same effect as the Streamlit Generator's "Load this machine into the Simulator".
        naive, lam, cfg = build(data["cfg"])
        mdfa, mlam, _classes, _trace = to_minimal(naive, lam)
        st.session_state.machine = (mdfa, mlam, cfg)
        st.session_state.state = mdfa.initial_state
        st.session_state.log = []
        st.session_state.message = "Insert coins, then choose a product."
        init_ui_state()
        on_reset()
        return {"ok": True}
    return {"ok": False, "error": f"Unknown request: {op}"}


req = st.session_state.get("vm_experience")
if isinstance(req, dict) and req.get("id") and req["id"] != st.session_state.get("vm_last_req"):
    st.session_state.vm_last_req = req["id"]
    try:
        reply = handle(req)
    except Exception as e:  # never crash the page on a bad request
        reply = {"ok": False, "error": f"Backend error: {e}"}
    st.session_state.vm_reply = {**reply, "id": req["id"]}

cfg = (st.session_state.machine[2] if "machine" in st.session_state else load_config(DEFAULT_CFG))
payload = gen_service.machine_payload(cfg)

# Full-bleed stage: the experience owns the whole viewport.
st.markdown("""<style>
[data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: none !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stAppViewContainer"], .stApp { background: %s; }
[data-testid="stCustomComponentV1"], [data-testid="stIFrame"], .stApp iframe {
  height: 100vh !important; width: 100%% !important; display: block; border: 0; }
[data-testid="stMain"] { overflow: hidden; }
</style>""" % theme.BACKGROUND, unsafe_allow_html=True)

with st.sidebar:
    st.caption("Showing the machine currently loaded in this session. Build a different "
               "one on the Generator page and it appears here too.")
    st.download_button(
        "Download offline copy (HTML)",
        render_html(payload, _prebuilt(json.dumps(load_config(DEFAULT_CFG)))),
        "state_machine.html", "text/html", width="stretch", icon=":material/download:",
        help="A single file that opens in any browser, with no Python or internet needed. "
             "Its Generator includes machines pre-built by the backend. Handy as a viva backup.")

_experience(machine=payload, palette=palette(), default_form=gen_service.DEFAULT_FORM,
            reply=st.session_state.get("vm_reply"), key="vm_experience", default=None)

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
