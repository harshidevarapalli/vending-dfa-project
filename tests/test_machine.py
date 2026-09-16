import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.generator import ConfigError, build, load_config  # noqa: E402
from core.mealy import run  # noqa: E402
from core.minimize import to_minimal  # noqa: E402
from spec.spec import spec_dfa  # noqa: E402

CFG = load_config(ROOT / "spec" / "config.json")


@pytest.fixture(scope="module")
def machines():
    naive, lam, cfg = build(CFG)
    mdfa, mlam, classes, trace = to_minimal(naive, lam)
    return naive, lam, mdfa, mlam


def test_spec_equals_generated(machines):
    naive, _, mdfa, _ = machines
    assert spec_dfa() == naive          # automata-lib compares languages
    assert spec_dfa() == mdfa


def test_state_counts(machines):
    naive, _, mdfa, _ = machines
    assert len(naive.states) == 16
    assert len(mdfa.states) == 8


def oracle(word):
    prices = {s: p["price"] for s, p in CFG["products"].items()}
    b = 0
    for i, a in enumerate(word):
        if a == "cancel":
            b = 0
        elif a in CFG["coins"]:
            b += CFG["coins"][a]
            if b > CFG["cap"]:
                return False
        else:
            return i == len(word) - 1 and b >= prices[a]
    return False


def test_oracle_all_strings(machines):
    spec = spec_dfa()
    symbols = sorted(spec.input_symbols)
    for n in range(0, 6):
        for w in itertools.product(symbols, repeat=n):
            assert spec.accepts_input(list(w)) == oracle(w), w


@pytest.mark.parametrize("word,verdict,last_output", [
    ("c10 c10 s3", "ACCEPT", "Chocolate"),
    ("c10 c10 s2", "ACCEPT", "Juice + ₹5 change"),
    ("c10 c10 s1", "ACCEPT", "Chips + ₹10 change"),
    ("c5 c5 s2", "REJECT", "BEEP"),
    ("c10 c10 c10", "REJECT", "BEEP, return ₹10"),
    ("c5 cancel c10 s1", "ACCEPT", "Chips"),
])
def test_demo_traces(machines, word, verdict, last_output):
    _, _, mdfa, mlam = machines
    rows, v = run(mdfa, mlam, word.split())
    assert v == verdict
    assert rows[-1].output == last_output


def test_lambda_total(machines):
    _, lam, mdfa, mlam = machines
    naive = machines[0]
    for d, L in ((naive, lam), (mdfa, mlam)):
        for q in d.states:
            for a in d.input_symbols:
                assert (q, a) in L


@pytest.mark.parametrize("coins,prices,cap,naive_n,min_n", [
    ({"c5": 5, "c10": 10}, [10, 15, 20], 25, 16, 8),
    ({"c5": 5, "c10": 10}, [20], 25, 9, 8),
    ({"c5": 5, "c10": 10, "c20": 20}, [10, 15, 20], 30, 20, 9),
    ({"c5": 5, "c10": 10}, [10, 20], 20, 10, 7),
])
def test_minimal_size_theorem(coins, prices, cap, naive_n, min_n):
    cfg = {"coins": coins, "cap": cap,
           "products": {f"s{i+1}": {"name": f"P{i+1}", "price": p} for i, p in enumerate(prices)}}
    naive, lam, _ = build(cfg)
    mdfa, _, _, _ = to_minimal(naive, lam)
    assert len(naive.states) == naive_n
    assert len(mdfa.states) == min_n == cap // 5 + 3


def test_bad_config_rejected():
    with pytest.raises(ConfigError):
        build({"coins": {"c5": 5}, "cap": 25, "products": {"s1": {"name": "X", "price": 12}}})
