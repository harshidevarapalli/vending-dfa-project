"""First-time 4-step onboarding modal (frontend owner)."""
import streamlit as st

STEPS = [
    ("🪙", "Insert a coin",
     "Press a coin button. Each coin is an <b>input symbol</b> (c5, c10…). "
     "Watch the credit display and the highlighted state move together: in a DFA, "
     "<i>the state is the memory</i>.",
     "δ(q0, c10) = q10"),
    ("🍫", "Choose a product",
     "Pick something you can afford. Products are symbols too (s1, s2, s3). "
     "Choosing one that costs more than your balance sends the machine to the "
     "trap state <b>q_dead</b>.",
     "δ(q10, s1) = q_done"),
    ("🔀", "Watch the DFA transition",
     "The diagram fills the <b>current state</b> in pink and draws the arrow you just "
     "followed in blue. The Automaton Monitor and the “How the DFA works” panel "
     "explain every step in plain words.",
     "previous —symbol→ current"),
    ("✅", "Complete the purchase",
     "Reaching <b>q_done</b> (double circle) means your input string is "
     "<b>accepted</b>: it belongs to L(M). The Mealy layer prints what drops out: "
     "product + change. Press <b>Reset</b> for the next customer.",
     "w = c10 c10 s2 ∈ L(M)"),
]


def _go(delta):
    st.session_state.tutorial_step = max(0, min(len(STEPS) - 1,
                                                st.session_state.tutorial_step + delta))


@st.dialog("How to use the simulator", width="medium")
def _dialog():
    i = st.session_state.get("tutorial_step", 0)
    ico, title, body, formal = STEPS[i]
    dots = "".join(f'<span class="{"on" if j == i else "done" if j < i else ""}"></span>'
                   for j in range(len(STEPS)))
    st.markdown(
        f'<div class="vm-tut"><div class="step-ico">{ico}</div>'
        f'<div class="n">Step {i + 1} of {len(STEPS)}</div><h3>{title}</h3>'
        f'<p>{body}</p><div class="formal">{formal}</div></div>'
        f'<div class="vm-dots">{dots}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1.4])
    if c1.button("Skip", key="tut_skip", type="tertiary", width="stretch"):
        st.rerun()
    c2.button("Back", key="tut_back", on_click=_go, args=(-1,), disabled=i == 0,
              width="stretch")
    if i < len(STEPS) - 1:
        c3.button("Next", key="tut_next", on_click=_go, args=(1,), type="primary",
                  width="stretch")
    elif c3.button("Start simulating", key="tut_start", type="primary",
                   width="stretch"):
        st.rerun()


def maybe_show():
    """Open the modal once when requested (first visit or the Tutorial button).

    The flag is cleared *before* opening, so closing with X / Esc never
    re-opens it on the next click.
    """
    if st.session_state.get("tutorial_open"):
        st.session_state.tutorial_open = False
        _dialog()
