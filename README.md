# Vending Machine DFA

A multi-product vending machine modeled as a **DFA acceptor**, extended with a
**Mealy transducer** for physical output (dispense / change / refund / beep),
formally **minimized** with a from-scratch Hopcroft implementation, and
wrapped in an interactive **Streamlit** app — including a generator that
builds, minimizes, and simulates a machine for *any* coin set and product
list, not just the default one.

**Status: core pipeline complete and tested — 17/17 tests passing.**
Default machine: ₹5/₹10 coins → Chips ₹10 · Juice ₹15 · Chocolate ₹20, cap ₹25.
Naive design: 16 states. Minimized: **8 states** (proved minimal, see
`docs/A_formal_model.md`).

---

## Run it (5 minutes)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # expect: 17 passed
streamlit run app/Simulator.py     # opens http://localhost:8501
```

Two pages appear in the sidebar:

- **Simulator** — click coins and products, watch the current state light up
  on the diagram, see what the machine dispenses/refunds, and read the step
  log. Loads the default machine from `spec/config.json`.
- **Generator** — type in *any* coins, products, and balance cap. Builds the
  naive DFA, minimizes it with Hopcroft's algorithm, shows both diagrams
  side by side plus the equivalence classes and the refinement trace, and
  can load the result straight into the Simulator.

Diagrams render in the browser via `st.graphviz_chart`, so system Graphviz
is **not** required to run the app — only for exporting standalone figures
with the `dot` CLI for the report.

---

## Project layout

```
vending/
├── spec/
│   ├── config.json      # default machine: coins, products, cap
│   └── spec.py           # hand-written minimal DFA (8 states) — the
│                          # independent reference the generator is tested
│                          # against; frozen at git tag spec-v1
├── core/
│   ├── generator.py       # config -> naive DFA + Mealy output map
│   ├── minimize.py        # own Hopcroft partition-refinement implementation
│   │                       # + step-by-step trace (not automata-lib's minify)
│   ├── mealy.py            # step/run any (dfa, lam) machine; trace printer;
│   │                        # human-readable "why rejected" messages
│   └── render.py            # DOT diagram rendering + table helpers
├── app/
│   ├── Simulator.py          # main page — click-through simulator
│   └── pages/
│       └── Generator.py       # build/minimize/inspect any configuration
├── tests/
│   ├── test_machine.py         # spec==generated, brute-force oracle,
│   │                            # demo traces, λ totality, minimal-size
│   │                            # theorem across 4 configurations
│   └── test_app.py               # Streamlit AppTest: clicks through the UI
├── docs/
│   └── A_formal_model.md          # formal spec + all three proofs (§3, §5)
└── requirements.txt
```

## What each part does, in one line

| Module | Does |
|---|---|
| `spec/spec.py` | The ground truth: hand-written 8-state minimal DFA. Everything else is checked against this. |
| `core/generator.py` | Turns a config dict into the *naive* DFA (one state per product+change combo) plus its Mealy output map. |
| `core/minimize.py` | Real Hopcroft's algorithm — reachability pass, partition refinement with a worklist, full trace of every split. Verified to match both `spec.py` and `automata-lib`'s `minify()`. |
| `core/mealy.py` | Steps a machine one symbol at a time, or runs a whole input string and returns the trace + ACCEPT/REJECT. |
| `core/render.py` | Turns a DFA into a Graphviz DOT string (highlighted current state, doublecircle accept states, dashed trap), plus table formatters for the trace and equivalence classes. |
| `app/Simulator.py` | The click-through demo. |
| `app/pages/Generator.py` | The "design any machine" tool — form → naive/minimal diagrams → load into Simulator. |

## Quick checks from a Python shell

```python
from core.generator import build, load_config
from core.minimize import to_minimal
from core.mealy import print_trace

naive, lam, cfg = build(load_config("spec/config.json"))
dfa, mlam, classes, trace = to_minimal(naive, lam)

print(len(naive.states), "->", len(dfa.states))   # 16 -> 8
print(len(trace), "refinement steps")              # 6

print_trace(dfa, mlam, ["c10", "c10", "s2"])        # Juice + ₹5 change, ACCEPT
```

Try a different machine without touching any file:

```python
from core.generator import build
cfg = {"coins": {"c5": 5, "c10": 10}, "cap": 20,
       "products": {"s1": {"name": "Item", "price": 10}}}
naive, lam, cfg = build(cfg)
dfa, mlam, classes, trace = to_minimal(naive, lam)
print(len(naive.states), "->", len(dfa.states))     # 9 -> 7
```

## Testing

```bash
python -m pytest -q          # 17 tests, ~1s
python -m pytest -v          # see each test name
```

Covers: `spec.py` and the generator accept the same language; a brute-force
balance oracle checked against every input string up to length 5; six named
demo scenarios (exact payment, change, underpay, overpay, cancel); λ is
defined for every (state, symbol) pair; the minimal-size theorem
(`cap/g + 3`) holds across four different configurations; and the Streamlit
app responds correctly to real button clicks.

## Team ownership

| Area | Owner | Report section(s) |
|---|---|---|
| Formal model, spec, proofs | A | §3, §5 |
| Mealy layer, Simulator page, tests | B | §6, §9 |
| Minimization, Generator page, JFLAP cross-check | C | §7 |
| Diagrams, related work, system design, report assembly | D | §1, §2, §4, §8, §10 |

## Rules

- **Don't rename states or symbols** in `spec/spec.py` after tag `spec-v1`
  without telling the whole team — the generator's equality test and every
  diagram depend on the exact names matching.
- `main` must always pass `pytest` and run the app — don't push broken code
  to the shared branch.
- Keep `spec/spec.py` **hand-written**, never generated. The equivalence
  test (`test_spec_equals_generated`) is only meaningful because the two
  are built independently.
- Config values must satisfy: every coin and price is a positive multiple
  of the smallest coin's value, and every price is ≤ the balance cap
  (enforced by `core/generator.py:validate`, with a clear error message).
