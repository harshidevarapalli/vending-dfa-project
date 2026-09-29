"""Frontend service layer for the HTML experience (frontend owner).

Packages the output of the EXISTING backend into JSON for the browser. Every
automaton fact here comes from calling core.generator.build,
core.minimize.to_minimal, core.mealy.explain_dead and the core.render table
helpers, read-only. Nothing in this file re-implements DFA/Mealy logic.
"""
import random

from core.generator import ConfigError, build
from core.mealy import explain_dead
from core.minimize import _label, to_minimal
from core.render import classes_table, trace_table
from core.theme import icon_for

# Same product-name pool and rules as the Streamlit Generator's Randomize.
NAMES = ["Chips", "Juice", "Chocolate", "Cola", "Water", "Coffee", "Cookie", "Gum",
         "Popcorn", "Tea"]
DEFAULT_FORM = {"coins": [["c5", 5], ["c10", 10]],
                "products": [["s1", "Chips", 10], ["s2", "Juice", 15], ["s3", "Chocolate", 20]],
                "cap": 25}


def _graph(dfa):
    return {"states": sorted(dfa.states), "final": sorted(dfa.final_states),
            "start": dfa.initial_state, "symbols": sorted(dfa.input_symbols),
            "delta": {q: dict(row) for q, row in dfa.transitions.items()}}


def _dead_reasons(dfa, cfg):
    """explain_dead() for every arrow into the trap, so the browser shows the
    exact message the Streamlit Simulator shows."""
    out = {}
    for q, row in dfa.transitions.items():
        for a, t in row.items():
            if t == "q_dead":
                try:
                    out.setdefault(q, {})[a] = explain_dead(cfg, q, a)
                except (ValueError, KeyError):
                    pass
    return out


def machine_payload(cfg):
    """The minimized machine (+ naive info for the minimisation chapter)."""
    naive, lam, cfg = build(cfg)
    dfa, mlam, classes, trace = to_minimal(naive, lam)
    return {
        **_graph(dfa),
        "cfg": cfg,
        "lambda": {q: {a: mlam[(q, a)] for a in dfa.input_symbols} for q in dfa.states},
        "dead_reason": _dead_reasons(dfa, cfg),
        "icons": {p["name"]: icon_for(p["name"]) for p in cfg["products"].values()},
        "naive": {
            "states": sorted(naive.states),
            "final": sorted(naive.final_states),
            "classes": [sorted(b) for b in classes],
            "name_of": {q: _label(b, naive) for b in classes for q in b},
            "steps": len(trace),
        },
    }


def form_of(cfg):
    return {"coins": [[s, v] for s, v in cfg["coins"].items()],
            "products": [[s, p["name"], p["price"]] for s, p in cfg["products"].items()],
            "cap": cfg["cap"]}


def generate(cfg):
    """Everything the Streamlit Generator page shows, as JSON."""
    try:
        naive, lam, cfg = build(cfg)
        mdfa, mlam, classes, trace = to_minimal(naive, lam)
    except ConfigError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # e.g. clashing symbols: report instead of crashing
        return {"ok": False, "error": f"Could not build this machine: {e}"}
    name_of = {q: _label(blk, naive) for blk in classes for q in blk}
    g = min(cfg["coins"].values())
    theorem = cfg["cap"] // g + 3
    return {
        "ok": True,
        "cfg": cfg,
        "form": form_of(cfg),
        "naive": _graph(naive),
        "minimal": _graph(mdfa),
        "metrics": {"naive": len(naive.states), "minimal": len(mdfa.states),
                    "theorem": theorem, "matches": len(mdfa.states) == theorem},
        "classes": classes_table(classes, name_of),
        "trace": trace_table(trace),
        "mealy": [{"state": q, "symbol": a, "output": mlam[(q, a)]}
                  for q in sorted(mdfa.states) for a in sorted(mdfa.input_symbols)],
        "machine": machine_payload(cfg),
    }


def random_config(rng=random):
    """Same rules as the Streamlit Generator's Randomize button."""
    coins = [("c5", 5)] + rng.sample([("c10", 10), ("c20", 20)], k=rng.randint(1, 2))
    coins.sort(key=lambda c: c[1])
    cap = rng.choice([20, 25, 30, 35, 40])
    names = rng.sample(NAMES, k=rng.randint(2, 4))
    prods = [(f"s{i + 1}", n, 5 * rng.randint(1, cap // 5)) for i, n in enumerate(names)]
    return {"coins": dict(coins), "cap": cap,
            "products": {s: {"name": n, "price": p} for s, n, p in prods}}


def prebuilt(default_cfg, n=12, seed=None):
    """Backend-generated machines baked into the offline copy."""
    rng = random.Random(seed)
    out, seen = [generate(default_cfg)], set()
    while len(out) < n + 1:
        cfg = random_config(rng)
        key = repr(sorted(cfg["coins"].items())) + repr(cfg["cap"]) + repr(list(cfg["products"].items()))
        if key in seen:
            continue
        seen.add(key)
        r = generate(cfg)
        if r["ok"]:
            out.append(r)
    return out
