"""Minimization (Member C owns).

STARTER: uses automata-lib's minify() so the app works today.
C replaces `partition()` with an own Hopcroft implementation + trace,
keeping the `to_minimal()` signature unchanged.
"""
from automata.fa.dfa import DFA


def partition(dfa):
    """Return the list of equivalence classes (sets of original state names)."""
    m = dfa.minify(retain_names=True)
    return [set(s) if isinstance(s, frozenset) else {s} for s in m.states]


def _label(block, dfa):
    if "q_dead" in block:
        return "q_dead"
    if block <= set(dfa.final_states):
        return "q_done"
    if len(block) == 1:
        return next(iter(block))
    return "{" + ",".join(sorted(block)) + "}"


def to_minimal(dfa, lam):
    """Return (min_dfa, min_lam, classes) with readable state names."""
    classes = partition(dfa)
    name_of = {}
    for blk in classes:
        lbl = _label(blk, dfa)
        for q in blk:
            name_of[q] = lbl
    T, L = {}, {}
    for blk in classes:
        rep = sorted(blk)[0]
        src = name_of[rep]
        T[src] = {a: name_of[t] for a, t in dfa.transitions[rep].items()}
        for a in dfa.input_symbols:
            L[(src, a)] = lam[(rep, a)]
    m = DFA(states=set(T), input_symbols=set(dfa.input_symbols), transitions=T,
            initial_state=name_of[dfa.initial_state],
            final_states={name_of[q] for q in dfa.final_states})
    return m, L, classes
