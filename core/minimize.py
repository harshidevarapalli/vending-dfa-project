"""Minimization (Member C owns).

Own implementation of Hopcroft's partition-refinement algorithm, with a
step-by-step trace suitable for the report and the Generator page.
Cross-checked against automata-lib's minify() in tests/test_machine.py.
"""
from automata.fa.dfa import DFA


def _reachable(dfa):
    seen, stack = {dfa.initial_state}, [dfa.initial_state]
    while stack:
        q = stack.pop()
        for a in dfa.input_symbols:
            t = dfa.transitions[q][a]
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


def hopcroft(dfa):
    """Return (partition, trace).

    partition: list[frozenset[str]] — the final equivalence classes.
    trace: list of dicts {symbol, splitter, before, after} — one entry per
    refinement step, in the order the splits actually happened.
    """
    states = _reachable(dfa)
    symbols = sorted(dfa.input_symbols)
    final = set(dfa.final_states) & states
    nonfinal = states - final

    # Inverse transitions: inv[a][t] = states q with delta(q, a) = t
    inv = {a: {} for a in symbols}
    for q in states:
        for a in symbols:
            t = dfa.transitions[q][a]
            inv[a].setdefault(t, set()).add(q)

    P = [b for b in (final, nonfinal) if b]
    # Worklist holds the smaller of the two initial blocks (standard Hopcroft
    # start); if only one block exists, seed with it.
    if len(P) == 2:
        W = [min(P, key=len)]
    else:
        W = list(P)

    trace = []
    while W:
        A = W.pop()
        for c in symbols:
            X = set()
            for t in A:
                X |= inv[c].get(t, set())
            if not X:
                continue
            newP = []
            for Y in P:
                inter, diff = Y & X, Y - X
                if inter and diff:
                    newP.append(inter)
                    newP.append(diff)
                    trace.append({
                        "symbol": c,
                        "splitter": sorted(A),
                        "before": sorted(Y),
                        "after": [sorted(inter), sorted(diff)],
                    })
                    if Y in W:
                        W.remove(Y)
                        W.append(inter)
                        W.append(diff)
                    else:
                        W.append(inter if len(inter) <= len(diff) else diff)
                else:
                    newP.append(Y)
            P = newP
    return [frozenset(b) for b in P], trace


def _label(block, dfa):
    if "q_dead" in block:
        return "q_dead"
    if block <= set(dfa.final_states):
        return "q_done"
    if len(block) == 1:
        return next(iter(block))
    return "{" + ",".join(sorted(block)) + "}"


def to_minimal(dfa, lam):
    """Return (min_dfa, min_lam, classes, trace)."""
    classes, trace = hopcroft(dfa)
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
            final_states={name_of[q] for q in dfa.final_states if q in name_of})
    return m, L, classes, trace
