# Vending Machine Automaton — starter kit

Multi-product vending machine as a DFA acceptor + Mealy transducer, with
formal minimization and an interactive Streamlit simulator.

## Run it (5 minutes)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # expect: 17 passed
streamlit run app/Simulator.py     # opens http://localhost:8501
```

The diagram in the app is rendered in the browser, so you do NOT need system
Graphviz for the app (only for exporting report figures with `dot`).

## What's in here

| Path | Owner | Status |
|---|---|---|
| `spec/config.json` | A | Default machine: ₹5/₹10 coins, Chips ₹10, Juice ₹15, Chocolate ₹20, cap ₹25 |
| `spec/spec.py` | A | Hand-written minimal DFA (8 states). Tag `spec-v1` once confirmed |
| `docs/A_formal_model.md` | A | Draft of report §3 and §5 — rewrite in your own words |
| `core/mealy.py` | B | Step/run any machine, trace printer, "why rejected" messages |
| `app/Simulator.py` | B | Working simulator page |
| `tests/` | B | 17 tests: spec = generator, brute-force oracle, demo traces, app clicks |
| `core/generator.py` | C | Working starter: config → naive 16-state DFA + outputs |
| `core/minimize.py` | C | STARTER uses `minify()`; C replaces `partition()` with own Hopcroft + trace |
| `core/render.py` | D | Starter DOT renderer; D polishes + builds `app/pages/Generator.py` |

## Quick checks from a Python shell

```python
from core.generator import build, load_config
from core.minimize import to_minimal
from core.mealy import print_trace
naive, lam, cfg = build(load_config("spec/config.json"))
dfa, mlam, classes = to_minimal(naive, lam)
print(len(naive.states), "->", len(dfa.states))   # 16 -> 8
print_trace(dfa, mlam, ["c10", "c10", "s2"])      # Juice + ₹5 change, ACCEPT
```

## Rules
- Don't rename states/symbols after `spec-v1` without telling everyone.
- `main` must always pass `pytest` and run the app.
- Keep `spec/spec.py` hand-written — the equality test is only meaningful if it's independent.
