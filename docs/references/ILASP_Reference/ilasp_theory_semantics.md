# ILASP / LAS / LOAS – Theory Cheat Sheet (Semantics)

This cheat sheet summarises the *learning-theoretic objects* used by ILASP-style learning tasks: partial interpretations, (context-dependent) examples, ordering examples for preferences/weak constraints, and noisy variants with penalties.

The focus is on the definitions used in the ILASP literature (LAS/LOAS and their context/noise extensions).

---

## 1) Background: ASP semantics (what “answer set” means)

A **hypothesis** `H` is an ASP program (typically a set of candidate rules/weak constraints selected from a finite rule space).  
It is always evaluated together with **background knowledge** `B` (fixed ASP program).

- `AS(P)` denotes the set of **answer sets** (stable models) of an ASP program `P`.
- (For preference learning) `ord(P)` denotes the **preference relation** induced by `P` over its answer sets: it contains triples `⟨A1, A2, op⟩` describing when `A1` is preferred to `A2` (or tied), for operators such as `<, >, =, ≤, ≥, ≠`.  
  Ordering examples constrain `ord(B ∪ H)`.

---

## 2) Partial interpretations (PIs)

A **partial interpretation** is a pair of sets of ground atoms:
- `e = ⟨e_inc, e_exc⟩`

Intuition:
- `e_inc` are atoms that **must be true** in an answer set,
- `e_exc` are atoms that **must be false** in an answer set.

### “Extends” / “satisfies” a partial interpretation
A set of atoms `A` (typically an answer set) **extends** `e = ⟨e_inc, e_exc⟩` iff:
- `e_inc ⊆ A`, and
- `e_exc ∩ A = ∅`.

This is the basic coverage notion for positive/negative examples.

---

## 3) Context-dependent partial interpretations (CDPIs)

In many ILASP frameworks, each example carries a **context program** that is added to the background/hypothesis when testing that example.

A **context-dependent partial interpretation** (CDPI) is a pair:
- `⟨e, C⟩`
where:
- `e` is a partial interpretation, and
- `C` is an ASP program (the **context**).

### Accepting answer sets (AAS)
Given a program `P` (in ILASP, usually `P = B ∪ H`), define:

- `AAS(⟨e, C⟩, P) := { A ∈ AS(P ∪ C)  |  A extends e }`.

That is: **answer sets of `P ∪ C` that satisfy the PI**.

### Program accepts a CDPI
A program `P` **accepts** a CDPI `⟨e, C⟩` iff:
- `AAS(⟨e, C⟩, P)` is non-empty.

(So “acceptance” is an existential condition over answer sets.)

---

## 4) Ordering examples (for learning preferences / weak constraints)

Ordering examples tell the learner *which answer sets should be preferred to which others* (this is the key ingredient needed to learn weak constraints / preferences). fileciteturn6file11

### Context-dependent ordering examples (CDOEs)
A **context-dependent ordering example** (CDOE) is:
- `o = ⟨e1, e2, op⟩`
where `e1,e2` are CDPIs and `op` is one of `<, >, =, ≤, ≥, ≠`. fileciteturn6file16

An **accepting pair** of answer sets for `o` w.r.t. `P` is a pair `⟨I1, I2⟩` such that:
1. `I1 ∈ AAS(e1, P)`,
2. `I2 ∈ AAS(e2, P)`,
3. `I1 op_P I2` (i.e., the relation induced by `P` orders them accordingly). fileciteturn6file16

### Brave vs cautious respect
Given program `P` and CDOE `o = ⟨e1,e2,op⟩`:

- **Bravely respects** `o` iff **there exists** an accepting pair `⟨I1,I2⟩` that satisfies the ordering. fileciteturn6file16  
- **Cautiously respects** `o` iff the ordering holds **for all relevant pairs** (equivalently, there is *no* accepting pair for the inverse operator). fileciteturn6file16

Intuition:
- *brave ordering* = “some pair of acceptable answer sets is ordered correctly”,
- *cautious ordering* = “every such pair is ordered correctly”.

---

## 5) Learning tasks (non-noisy)

A typical (context-aware, preference-capable) learning task contains:

- `B`: background knowledge (ASP program)
- `SM`: hypothesis space / rule space (finite set of candidate rules and weak constraints)
- `E+`: positive CDPI examples
- `E-`: negative CDPI examples
- `Ob`: brave ordering examples (CDOEs)
- `Oc`: cautious ordering examples (CDOEs)

A hypothesis `H ⊆ SM` is an **inductive solution** iff `B ∪ H`:

1) **covers** each positive example: accepts it,  
2) **covers** each negative example: does *not* accept it,  
3) **covers** each brave ordering: bravely respects it,  
4) **covers** each cautious ordering: cautiously respects it. fileciteturn6file14

(ILASP searches for solutions that are *optimal* according to a cost function; in the non-noisy setting this is typically “shortest hypothesis”.)

---

## 6) Noisy tasks (weighted examples with penalties)

To handle mislabeled / imperfect data, ILASP introduces **penalties** (weights) on examples: uncovered examples need not be fatal, but they add cost. fileciteturn6file12

### Weighted CDPIs / CDOEs
- Weighted CDPI: `⟨eid, epen, ecdpi⟩`
- Weighted CDOE: `⟨oid, open, oord⟩`
where `epen/open` is a positive integer or `∞`. fileciteturn6file12

Acceptance/respect is defined by ignoring the weights (it’s the same as for the underlying CDPI/CDOE). fileciteturn6file3

### ILP\_noise LOAS task
A noisy LOAS task has the same shape as above, but all examples are weighted. fileciteturn6file12

Given `T = ⟨B, SM, ⟨E+, E-, Ob, Oc⟩⟩` and `H ⊆ SM`, define:

- `uncov(H,T)` = the set of examples that `B ∪ H` does **not** cover (positives not accepted, negatives accepted, orderings not respected). fileciteturn6file12
- `pen(H,T)` = sum of penalties over `uncov(H,T)`. fileciteturn6file12
- `S(H,T)` (score) = `|H| + pen(H,T)`. fileciteturn6file12

Then:
- `H` is an **inductive solution** iff `S(H,T)` is finite (i.e., it covers all examples with infinite penalty). fileciteturn6file12
- `H` is an **optimal inductive solution** iff it has finite score and no other `H' ⊆ SM` has smaller score. fileciteturn6file12

---

## 7) Why ordering examples matter (weak constraints)

Without ordering examples, weak constraints are “invisible” to standard coverage: removing a weak constraint often doesn’t change the set of answer sets, so example coverage cannot force learning it. Ordering examples constrain which answer sets must dominate others, thereby incentivising learning weak constraints. fileciteturn6file11

---

## 8) CDILP (ILASP4-style) in one paragraph

Modern ILASP algorithms (e.g., ILASP4) implement *conflict-driven* search. They iteratively:
1) solve for an optimal hypothesis under currently known “coverage constraints”,
2) find a counterexample the hypothesis fails to cover,
3) add a new constraint explaining why the example wasn’t covered,
until no counterexample remains (then the hypothesis is guaranteed optimal). fileciteturn8file15

(Those “coverage constraints” are Boolean formulae over rule identifiers and act like learned nogoods/explanations.) fileciteturn8file15

---

## 9) Practical glossary

- **Hypothesis space / rule space `SM`**: the finite set of candidate rules/weak constraints allowed to appear in `H`.
- **Coverage (positive PI/CDPI)**: existential satisfaction by some answer set (in the appropriate context).
- **Negative examples**: forbids existence of an answer set satisfying the PI (again, in context).
- **Brave ordering**: “∃ accepting pair ordered correctly.”
- **Cautious ordering**: “all accepting pairs ordered correctly” (or “no accepting pair violates it”).
- **Penalty `∞`**: hard constraint (must be covered, otherwise infinite score).

