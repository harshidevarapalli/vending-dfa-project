"""Config -> NAIVE DFA + Mealy output map (Member C owns; starter version).

The naive design has one 'done' state per (product, change) so that
minimization has real work to do (default config: 16 states -> 8).
"""
import json
from functools import reduce
from math import gcd

from automata.fa.dfa import DFA

DEAD = "q_dead"


class ConfigError(ValueError):
    pass


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(cfg, max_balance_states=40):
    coins = cfg.get("coins") or {}
    products = cfg.get("products") or {}
    cap = cfg.get("cap")
    if not coins:
        raise ConfigError("Add at least one coin.")
    if not products:
        raise ConfigError("Add at least one product.")
    if any((not isinstance(v, int)) or v <= 0 for v in coins.values()):
        raise ConfigError("Coin values must be positive whole rupees.")
    g = reduce(gcd, coins.values())
    if g not in coins.values():
        raise ConfigError(f"One coin must be worth ₹{g} (the gcd of the coin values).")
    if not isinstance(cap, int) or cap <= 0 or cap % g:
        raise ConfigError(f"Cap must be a positive multiple of ₹{g}.")
    for s, p in products.items():
        price = p.get("price")
        if not isinstance(price, int) or price <= 0 or price % g:
            raise ConfigError(f"Price of {p.get('name', s)} must be a positive multiple of ₹{g}.")
        if price > cap:
            raise ConfigError(f"{p.get('name', s)} costs more than the ₹{cap} cap.")
    if cap // g + 1 > max_balance_states:
        raise ConfigError("Machine too large to draw; lower the cap or use bigger coins.")
    return g


def build(cfg):
    """Return (dfa, lam, cfg). lam maps (state, symbol) -> output text."""
    g = validate(cfg)
    coins = cfg["coins"]
    prices = {s: p["price"] for s, p in cfg["products"].items()}
    cap = cfg["cap"]
    sym = set(coins) | set(prices) | {"cancel"}
    T, lam, done = {}, {}, set()
    for b in range(0, cap + 1, g):
        q = f"q{b}"
        T[q] = {}
        for c, v in coins.items():
            ok = b + v <= cap
            T[q][c] = f"q{b + v}" if ok else DEAD
            lam[(q, c)] = "—" if ok else f"BEEP, return ₹{v}"
        T[q]["cancel"] = "q0"
        lam[(q, "cancel")] = f"REFUND ₹{b}" if b else "—"
        for s, p in prices.items():
            if b >= p:
                d = f"done_{s}_ch{b - p}"
                done.add(d)
                T[q][s] = d
                name = cfg["products"][s]["name"]
                lam[(q, s)] = name + (f" + ₹{b - p} change" if b > p else "")
            else:
                T[q][s] = DEAD
                lam[(q, s)] = "BEEP"
    for q in done | {DEAD}:
        T[q] = {a: DEAD for a in sym}
        lam.update({(q, a): "BEEP" for a in sym})
    dfa = DFA(states=set(T), input_symbols=sym, transitions=T,
              initial_state="q0", final_states=done)
    return dfa, lam, cfg
