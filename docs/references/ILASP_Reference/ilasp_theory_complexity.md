# ILASP / LAS / LOAS – Theory Cheat Sheet (Complexity)

This cheat sheet summarises the *computational complexity* results commonly cited for ILASP learning frameworks, focusing on two standard decision problems:

- **Verification**: given a task `T` and hypothesis `H`, decide whether `H` is a solution of `T`.
- **Satisfiability**: given a task `T`, decide whether there exists *some* solution `H`.

Unless stated otherwise, these results are for **propositional** tasks (i.e., ground `B`, ground `SM`, and ground examples/contexts). fileciteturn8file8

---

## 1) Complexity classes used (quick reminder)

- **NP**: “guess & check” with polynomial-time verification.
- **DP**: problems that can be written as an intersection of an NP problem and a coNP problem (informally, “NP + coNP combined”).
- **Σ₂^P (Sigma\_2\^P)**: NP with an NP-oracle (equivalently, the second level of the polynomial hierarchy, often aligned with ∃∀-QBF).  
  Some papers denote this class as **P₂** in prose; when they show a nondeterministic TM with an NP-oracle, that is Σ₂^P. fileciteturn7file19

---

## 2) Frameworks (what varies)

Common ILASP learning frameworks form a chain of generalisations. A key result is that many of these frameworks reduce to each other in polynomial time for the two decision problems. fileciteturn7file11

You will see (among others):

- **ILPb**: learning from (non-context) partial interpretations with *brave* induction (existential coverage).
- **ILPsm**: learning from stable models (a related baseline).
- **ILPc**: learning with *cautious* induction (universal constraints over answer sets).
- **ILPLAS**: learning from answer sets with both brave and cautious induction.
- **ILPLOAS / ILPcontextLOAS**: adds ordering examples (to learn weak constraints/preferences) and contexts.

---

## 3) Results for ILPb and ILPsm

### Verification
Verifying whether a given `H` is a solution is **NP-complete** for ILPb. fileciteturn7file11  
The same holds for ILPsm. fileciteturn7file11

### Satisfiability
Deciding whether an ILPb task has *some* solution is **NP-complete**. fileciteturn7file10  
The same holds for ILPsm. fileciteturn7file11

(High-level intuition: you can nondeterministically guess `H ⊆ SM` and check coverage using NP checks.)

---

## 4) Results for ILPc / ILPLAS / ILPLOAS / ILPcontextLOAS (non-noisy)

### Verification
For each of these frameworks, **verification is DP-complete**. fileciteturn7file4

Intuition:
- you need *both* an existential check (“some answer set exists / some example is bravely covered”) and a universal check (“all answer sets satisfy something / no counterexample answer set exists”), naturally combining NP and coNP-style reasoning.

### Satisfiability
For each of these frameworks, **satisfiability is Σ₂^P-complete** (denoted “P₂-complete” in the 2018 AI paper). fileciteturn7file4turn7file19

Membership idea (from the proof sketch):
- nondeterministically guess `H ⊆ SM`,
- then verify `H` using NP-oracle queries. fileciteturn7file19

Hardness idea:
- reduction from answer-set existence for a ground disjunctive program (a Σ₂^P-complete problem), mapped into an ILPc task. fileciteturn7file19

---

## 5) Noisy learning (ILP\_noise LOAS)

For propositional tasks, the noisy extension **does not increase** the complexity of the two decision problems relative to ILPcontextLOAS. fileciteturn8file8

### Verification (noisy)
**DP-complete**. fileciteturn8file8

### Satisfiability (noisy)
**Σ₂^P-complete**. fileciteturn8file8

(The proof uses polynomial reductions in both directions between ILPcontextLOAS and ILP\_noise LOAS.) fileciteturn7file8

---

## 6) “Finding an optimal hypothesis” vs the decision problems above

ILASP systems are designed to return an **optimal** solution (e.g., shortest `H`, or minimum `|H| + penalty`). fileciteturn8file9  
The papers above focus on **verification** and **satisfiability** as clean decision problems; the exact complexity of *computing* an optimal hypothesis depends on how “optimality” is posed (function problem vs decision form) and on the scoring function.

A common way to reason about “optimality” is to study a decision variant such as:
- “Is there a solution with score ≤ k?”
or
- “Is a given solution optimal (no better solution exists)?”

Those variants often align with optimization-style reasoning over ASP (which can lift complexity by another level in the polynomial hierarchy), but you should cite a paper-specific theorem before making a formal claim.

---

## 7) Quick lookup table

| Framework | Verification | Satisfiability |
|---|---:|---:|
| ILPb | NP-complete fileciteturn7file11 | NP-complete fileciteturn7file10 |
| ILPsm | NP-complete fileciteturn7file11 | NP-complete fileciteturn7file11 |
| ILPc | DP-complete fileciteturn7file4 | Σ₂^P-complete fileciteturn7file4turn7file19 |
| ILPLAS | DP-complete fileciteturn7file4 | Σ₂^P-complete fileciteturn7file4turn7file19 |
| ILPLOAS | DP-complete fileciteturn7file4 | Σ₂^P-complete fileciteturn7file4turn7file19 |
| ILPcontextLOAS | DP-complete fileciteturn7file4 | Σ₂^P-complete fileciteturn7file4turn7file19 |
| ILP\_noise LOAS | DP-complete fileciteturn8file8 | Σ₂^P-complete fileciteturn8file8 |

---

## 8) What to cite in writeups / custom-GPT knowledge

If you only need a small number of “load-bearing” citations for a knowledge base, these are the most direct ones:

- DP-completeness of verification + Σ₂^P-completeness of satisfiability (non-noisy, ordering/context frameworks). fileciteturn7file4
- DP-completeness / Σ₂^P-completeness for the noisy extension. fileciteturn8file8
- Definition of penalties/score/optimality in noisy tasks. fileciteturn6file12

