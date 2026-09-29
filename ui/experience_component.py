"""Two-way Streamlit component that serves web/ (frontend owner).

declare_component must be called from an importable module, so it lives here
rather than in the page script.
"""
from pathlib import Path

import streamlit.components.v1 as components

WEB = Path(__file__).resolve().parents[1] / "web"

experience = components.declare_component("vm_experience", path=str(WEB))
