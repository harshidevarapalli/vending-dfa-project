from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "Simulator.py")


def click(at, key):
    at.button(key=key).click().run(timeout=15)


def test_purchase_with_change():
    at = AppTest.from_file(APP).run(timeout=15)
    assert not at.exception
    for k in ("btn_c10", "btn_c10", "btn_s2"):
        click(at, k)
    assert at.session_state.state == "q_done"
    assert "Juice + ₹5 change" in at.success[0].value


def test_overpay_then_reset():
    at = AppTest.from_file(APP).run(timeout=15)
    for k in ("btn_c10", "btn_c10", "btn_c10"):
        click(at, k)
    assert at.session_state.state == "q_dead"
    assert "cap" in at.error[0].value
    click(at, "btn_reset")
    assert at.session_state.state == "q0"
