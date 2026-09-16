"""DOT rendering (Member D owns)."""
from collections import defaultdict


def to_dot(dfa, highlight=None):
    edges = defaultdict(list)
    for q, row in dfa.transitions.items():
        for a, t in row.items():
            edges[(q, t)].append(a)
    out = ['digraph M {', 'rankdir=LR; bgcolor="transparent";',
           'node [shape=circle, fontname="Helvetica", fontsize=11];',
           'edge [fontname="Helvetica", fontsize=9];',
           'start [shape=point]; start -> "%s";' % dfa.initial_state]
    for q in sorted(dfa.states):
        attrs = []
        if q in dfa.final_states:
            attrs.append("shape=doublecircle")
        style = []
        if q == "q_dead":
            style.append("dashed")
        if q == highlight:
            style.append("filled")
            attrs.append('fillcolor="#FFD966"')
        if style:
            attrs.append('style="%s"' % ",".join(style))
        out.append('"%s" [%s];' % (q, ", ".join(attrs)))
    for (u, v), syms in sorted(edges.items()):
        out.append('"%s" -> "%s" [label="%s"];' % (u, v, ",".join(sorted(syms))))
    out.append("}")
    return "\n".join(out)


def classes_table(classes, name_of):
    """Human-readable rows: [minimal_name, sorted(members)]."""
    rows = []
    for blk in classes:
        members = sorted(blk)
        rows.append({"minimal state": name_of[members[0]], "merged from": ", ".join(members)})
    return rows


def trace_table(trace):
    rows = []
    for i, step in enumerate(trace, 1):
        inter, diff = step["after"]
        rows.append({
            "step": i,
            "symbol": step["symbol"],
            "splitter": "{" + ",".join(step["splitter"]) + "}",
            "block split": "{" + ",".join(step["before"]) + "}",
            "into": "{" + ",".join(inter) + "}  /  {" + ",".join(diff) + "}",
        })
    return rows
