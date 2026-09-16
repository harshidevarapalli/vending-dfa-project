"""Mealy layer (Member B): step and run any machine (dfa, lam)."""
from dataclasses import dataclass


@dataclass
class Step:
    n: int
    state: str
    symbol: str
    next_state: str
    output: str


def step(dfa, lam, state, symbol):
    nxt = dfa.transitions[state][symbol]
    return nxt, lam[(state, symbol)]


def run(dfa, lam, symbols):
    """Return (steps, verdict). symbols is a list like ["c10", "c10", "s2"]."""
    q, rows = dfa.initial_state, []
    for i, a in enumerate(symbols, 1):
        nxt, out = step(dfa, lam, q, a)
        rows.append(Step(i, q, a, nxt, out))
        q = nxt
    return rows, ("ACCEPT" if q in dfa.final_states else "REJECT")


def explain_dead(cfg, state, symbol):
    """Human reason a transition went to the trap state."""
    if state in ("q_done",) or state.startswith("done_"):
        return "Purchase already finished. Press Reset for a new transaction."
    if state == "q_dead":
        return "Transaction was rejected earlier. Press Reset."
    bal = int(state[1:])
    if symbol in cfg["coins"]:
        return f"Overpaid: ₹{bal} + ₹{cfg['coins'][symbol]} is over the ₹{cfg['cap']} cap."
    p = cfg["products"][symbol]
    return f"Not enough money for {p['name']}: need ₹{p['price']}, have ₹{bal}."


def print_trace(dfa, lam, symbols):
    rows, verdict = run(dfa, lam, symbols)
    print(f"{'step':>4}  {'state':<8} {'input':<7} {'next':<8} output")
    for r in rows:
        print(f"{r.n:>4}  {r.state:<8} {r.symbol:<7} {r.next_state:<8} {r.output}")
    print(verdict)
    return verdict
