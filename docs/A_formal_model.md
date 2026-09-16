# Draft — Report §3 (Formal specification) and §5 (Proofs)

> Member A: this is a working draft. Check every line, rewrite it in your own
> words, and be ready to explain each step in the viva.

## §3 Formal specification

The machine is the DFA **M = (Q, Σ, δ, q₀, F)** with

- **Σ = {c5, c10, cancel, s1, s2, s3}** — insert ₹5, insert ₹10, cancel,
  select Chips (₹10), Juice (₹15), Chocolate (₹20).
- **Q = {q0, q5, q10, q15, q20, q25, q_done, q_dead}** — `q_b` means "current
  balance is ₹b"; `q_done` means a purchase has just completed; `q_dead` is
  the trap for illegal actions.
- **q₀ = q0**, **F = {q_done}**.
- **δ** is total (8 × 6 = 48 entries), given in Table 4.1 (copy from `spec/spec.py`):
  - `δ(q_b, c_v) = q_(b+v)` if b + v ≤ 25, else `q_dead`
  - `δ(q_b, cancel) = q0`
  - `δ(q_b, s_i) = q_done` if b ≥ price(s_i), else `q_dead`
  - `δ(q_done, a) = δ(q_dead, a) = q_dead` for every a ∈ Σ

Design decisions: pay-then-select; balance cap ₹25; overpaying, selecting an
unaffordable product, or any input after a purchase is illegal and goes to the
trap; one input string models one transaction.

**Language.** L(M) is the set of strings w ∈ Σ* such that, tracking a running
balance that starts at 0, is reset to 0 by `cancel` and increased by each coin:
(i) the balance never exceeds ₹25, (ii) no select symbol appears before the
last position, and (iii) the last symbol selects a product whose price is at
most the balance at that moment.

The Mealy extension (Member B, §6) is **M' = (Q, q₀, Σ, O, δ, λ)** with the same
δ and λ : Q × Σ → O attaching an output (dispense, change, refund, beep).

## §5 Proofs

### Lemma 1 (balance invariant)
For every w ∈ Σ* that does not contain an illegal action, δ*(q0, w) = q_b where
b is the running balance after w. If w contains an illegal action,
δ*(q0, w) ∈ {q_done, q_dead} as appropriate.

*Proof* by induction on |w|.
Base: w = ε, δ*(q0, ε) = q0 and the balance is 0.
Step: let w = xa and suppose δ*(q0, x) = q_b with balance b.
- a = c_v: if b + v ≤ 25 the new balance is b + v and δ(q_b, c_v) = q_(b+v);
  otherwise the action is illegal and δ gives q_dead.
- a = cancel: balance becomes 0 and δ(q_b, cancel) = q0.
- a = s_i: if b ≥ price the purchase completes and δ gives q_done; otherwise
  it is illegal and δ gives q_dead.
If δ*(q0, x) ∈ {q_done, q_dead}, every further symbol goes to q_dead, matching
"input after a purchase / after an illegal action is illegal". ∎

### Theorem 1 (finiteness and regularity)
Balances are multiples of 5 (coins are ₹5 and ₹10) and never exceed 25 (any
coin that would do so goes to the trap), so b ∈ {0, 5, 10, 15, 20, 25}. By
Lemma 1, the only states the machine ever needs are these six plus q_done and
q_dead, so |Q| = 8 is finite. A language accepted by a DFA is regular, hence
L(M) is regular. ∎

*Remark (why the cap matters).* Without the cap the balance is unbounded, so
the machine would need a state for every multiple of 5 — infinitely many.
The cap is exactly what keeps the model a finite automaton.

### Theorem 2 (correctness)
w ∈ L(M) ⇔ δ*(q0, w) = q_done.
(⇒) If w ∈ L(M), its prefix before the last symbol is legal, so by Lemma 1
the machine is in q_b; the last symbol is an affordable select, so δ gives
q_done. (⇐) q_done is only entered from some q_b by an affordable select, and
every symbol after it leads to q_dead, so the select is the last symbol and
the prefix was legal: w ∈ L(M). ∎

### Theorem 3 (minimal size) — with Member C
For any valid configuration (coin values with gcd g, some coin worth g, all
prices ≤ cap and multiples of g), the minimal DFA has exactly **cap/g + 3**
states. Default: 25/5 + 3 = 8.

*Proof sketch.* All states are reachable (insert the g-coin k times to reach
q_(kg); buy something from q_cap; overpay from q_cap). Every pair is
distinguishable:
- q_done vs any other: ε.
- q_b vs q_dead: `cancel`, insert coins up to the cheapest price, select it —
  accepted from q_b, never from q_dead.
- q_b vs q_b' with b < b': insert the g-coin (cap − b')/g + 1 times. From q_b'
  this overflows into q_dead; from q_b the balance stays ≤ cap. Then top up
  to cap and select any product: accepted only from q_b.
Reachable + pairwise distinguishable ⇒ minimal (Myhill–Nerode). ∎

Verified by the test `test_minimal_size_theorem` on four configurations
(16→8, 9→8, 20→9, 10→7).
