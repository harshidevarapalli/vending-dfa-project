"""Hand-written minimal DFA for the default config (Member A).

Frozen at git tag spec-v1. Do NOT generate this file: it is the independent
reference that the generator is tested against.
"""
STATES = {"q0", "q5", "q10", "q15", "q20", "q25", "q_done", "q_dead"}
SYMBOLS = {"c5", "c10", "cancel", "s1", "s2", "s3"}
START = "q0"
FINAL = {"q_done"}

D, OK = "q_dead", "q_done"
TRAP = {a: D for a in SYMBOLS}

DELTA = {
    "q0":  {"c5": "q5",  "c10": "q10", "cancel": "q0", "s1": D,  "s2": D,  "s3": D},
    "q5":  {"c5": "q10", "c10": "q15", "cancel": "q0", "s1": D,  "s2": D,  "s3": D},
    "q10": {"c5": "q15", "c10": "q20", "cancel": "q0", "s1": OK, "s2": D,  "s3": D},
    "q15": {"c5": "q20", "c10": "q25", "cancel": "q0", "s1": OK, "s2": OK, "s3": D},
    "q20": {"c5": "q25", "c10": D,     "cancel": "q0", "s1": OK, "s2": OK, "s3": OK},
    "q25": {"c5": D,     "c10": D,     "cancel": "q0", "s1": OK, "s2": OK, "s3": OK},
    "q_done": dict(TRAP),
    "q_dead": dict(TRAP),
}

assert set(DELTA) == STATES
assert all(set(DELTA[q]) == SYMBOLS for q in STATES), "delta must be total"


def spec_dfa():
    from automata.fa.dfa import DFA
    return DFA(states=STATES, input_symbols=SYMBOLS, transitions=DELTA,
               initial_state=START, final_states=FINAL)
