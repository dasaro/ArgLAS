# clingo Proof + Complexity Companion (for theorem‑assisted encoding)

This companion is designed to be a **knowledge file** for a Custom GPT that supports:
- proving **correctness** of clingo/ASP encodings w.r.t. a mathematical specification; and
- classifying the **complexity** (Polynomial Hierarchy level) of the resulting reasoning task.

It consolidates (without loss of detail) the following materials:
- Proof/CORRECTNESS cheat‑sheet
- Complexity‑class cheat‑sheet
- Theorem‑assisted workflow + pitfalls

---

## Table of contents

1. Correctness: what to prove and how  
   1.1 Problem statement & projection  
   1.2 Semantics tools (reduct, closure, stable model test)  
   1.3 Soundness + completeness proof pattern  
   1.4 Generate–Define–Test proof decomposition  
   1.5 Tightness, completion, loop formulas (SAT‑style reasoning)  
   1.6 Correctness checklist and proof templates

2. Complexity: what problem are you solving and which class is it in  
   2.1 Reasoning tasks (existence/brave/cautious/optimal)  
   2.2 Program fragments (positive/normal/disjunctive/optimization)  
   2.3 Complexity table (P, NP, coNP, Σ₂^p, Δ₂^p, …)  
   2.4 Membership (upper bound) proof recipes  
   2.5 Hardness (lower bound) reduction recipes  
   2.6 Data vs combined complexity: how to avoid confusion  
   2.7 Complexity checklist

3. Theorem‑assisted workflow  
   3.1 Recommended documentation block for `.lp` encodings  
   3.2 Standard proof plan skeleton  
   3.3 Stability proof tricks to try first  
   3.4 Complexity classification prompts  
   3.5 Pitfalls and how to catch them  
   3.6 “Proof artifacts” to request from the user

---

# 1. Correctness: what to prove and how

# clingo/ASP Proof Cheat‑Sheet (Correctness)

This document is meant to help you **prove that a clingo program is correct** with respect to a precise mathematical specification.

It focuses on **stable-model semantics** and proof patterns that work well for “generate–define–test” encodings.

---

## 1. Mathematical problem statement (what the encoding should mean)

Fix:

- **Instance vocabulary**: a set of ground facts `I` describing an input instance.
- **Mathematical solution set**: `S(I)` (e.g., all proper colorings, all matchings, all schedules).
- **ASP program**: `P` (your encoding).

Define a **solution extraction map** `sol(·)` that projects a stable model to the intended output:
- Example: `sol(X) := { color(v,c) ∈ X }` (ignore auxiliaries).

**Target statement (projection equivalence):**
\[
\{ sol(X) \mid X \in SM(P \cup I) \} = S(I)
\]
where `SM(·)` is the set of stable models.

> In practice you often prove a *bijection modulo auxiliary atoms*: different stable models may exist but have the same projection; you typically care about equality of the projected sets.

---

## 2. The semantic facts you will cite in proofs

### 2.1 Reduct (Gelfond–Lifschitz) for a (ground) normal program
Given a program `P` and a set of atoms `X`, the **reduct** `P^X` is obtained by:
- dropping every rule whose default-negative body contains an atom in `X`;
- removing all default-negative literals from remaining rules.

(Slides formulation: `P^X = { h(r) <- B(r)+ | r in P, B(r)- ∩ X = ∅ }`.)

### 2.2 Consequences for a positive program
If `Q` is **positive** (no default negation), define:
- `Cn(Q)` = the **least** set of atoms closed under `Q` (least fixpoint semantics).
- Operationally: iteratively apply `T_Q` until a fixpoint:
  - `T_Q(X) = { h(r) | r in Q and B(r) ⊆ X }`.

### 2.3 Stable model characterization (reduct-based)
A set of atoms `X` is a **stable model** of `P` iff:
\[
Cn(P^X) = X
\]
Intuition: “`X` is exactly what can be derived from `P` once all `not` are evaluated w.r.t. `X`”.

---

## 3. Proof obligations: the standard two-lemma pattern

### 3.1 Soundness (ASP ⇒ math)
**Claim:** for every stable model `X ∈ SM(P ∪ I)`, the extracted object `sol(X)` is a valid solution, i.e. `sol(X) ∈ S(I)`.

**Typical structure:**
1. **Read off the guessed structure** from `X` (output predicates).
2. Show each requirement of the math definition holds because:
   - constraints eliminate forbidden configurations;
   - derivation rules ensure required consequences;
   - stable models satisfy all rules/constraints (they are models).

**Good practice:** state explicit invariants like
- “exactly one color per vertex”
- “edges connect different colors”
and prove each as a small lemma from the program.

### 3.2 Completeness (math ⇒ ASP)
**Claim:** for every math solution `s ∈ S(I)`, there exists a stable model `X` such that `sol(X) = s`.

**Typical structure:**
1. **Construct** an interpretation `X_s`:
   - include all atoms encoding `s`;
   - add necessary auxiliary atoms (often those that should be derived).
2. Show `X_s` satisfies every rule and violates no constraint (**modelhood**).
3. Prove stability, usually by showing:
   - `Cn((P∪I)^{X_s}) = X_s`.

**Common shortcut:** if auxiliaries are produced by a positive (or stratified) subprogram, show they coincide with the **least fixpoint** of that subprogram, so the closure part of the stability proof is easy.

---

## 4. Generate–Define–Test decomposition (recommended proof layout)

Many encodings can be decomposed conceptually into three blocks:

### 4.1 Generate (guess candidates)
Purpose: ensure that every candidate solution can be represented.
- choice rules / disjunction / explicit guessing predicates

Proof impact:
- Completeness often reduces to “my construction chooses exactly those atoms”.

### 4.2 Define (deterministic closure)
Purpose: derive auxiliary predicates from the guessed part and the instance.
- often positive/stratified rules

Proof impact:
- Use `Cn(·)` / fixpoint reasoning to show derived atoms are exactly the intended ones.

### 4.3 Test (filter invalid candidates)
Purpose: express constraints corresponding to the math definition.
- integrity constraints `:- Body.`

Proof impact:
- Soundness is mostly: stable model cannot violate any test.

---

## 5. Tightness / completion / loops (when you want SAT-style proofs)

This section is for **normal** (non-disjunctive) programs.

### 5.1 Clark completion (supported models)
Completion turns each predicate definition into an “if and only if”:
- Every stable model satisfies the completion.
- Completion models are **supported models** (may include circular self-support).

Use completion-based proofs when your encoding is “definition-like” and non-cyclic.

### 5.2 Tight programs (acyclic positive dependency graph)
If the **positive dependency graph** is acyclic (“tight”), then:
- stable models coincide with models of the completion.

This can make correctness proofs almost purely propositional.

### 5.3 Non-tight programs and loop formulas
If there are positive cycles, completion alone can admit non-stable supported models.
Loop formulas exclude circular support; stable models correspond to:
- completion + all loop formulas.

You rarely write loop formulas by hand, but this perspective is useful for proofs:
- show your encoding avoids circular definitions, or that cycles are “broken” by construction.

---

## 6. Correctness checklist (drop-in for papers and documentation)

When writing a proof, include:

1. **Instance format** (facts) and **solution projection** `sol(X)`.
2. **Soundness:** `X stable model ⇒ sol(X)` satisfies the math constraints.
3. **Completeness:** for every math solution `s`, build `X_s` and prove it is a stable model.
4. Explicitly justify any “auxiliary equals closure” claims via fixpoint arguments.
5. (If helpful) argue tightness / lack of circular support to simplify stability arguments.

---

## 7. Mini-templates you can copy into your proof write-up

### Soundness template
> Let `X ∈ SM(P ∪ I)`. We show `sol(X) ∈ S(I)`.  
> By rules …, `X` contains … (structure lemma).  
> By constraints …, `X` cannot contain … (forbidden pattern lemma).  
> Hence `sol(X)` satisfies properties (1)…(k) of the mathematical definition.  
> Therefore `sol(X) ∈ S(I)`.

### Completeness template
> Let `s ∈ S(I)`. Define `X_s := enc(s) ∪ aux(s,I)`.  
> (Modelhood) Every rule of `P∪I` is satisfied by `X_s`; no constraint body holds.  
> (Stability) Consider the reduct `(P∪I)^{X_s}`; its positive closure yields exactly `X_s`.  
> Thus `X_s ∈ SM(P∪I)` and `sol(X_s)=s`.



---

# 2. Complexity: what problem are you solving and which class is it in?

# clingo/ASP Complexity Cheat‑Sheet (Correctness + Complexity Class)

This document helps you **classify the complexity** of an ASP/clingo encoding and align it with the intended decision problem.

Unless stated otherwise, complexity claims are about the **ground (propositional) program** after grounding.

---

## 1. First decide: which *reasoning task* is your spec?

Common tasks (given `P` and an instance `I`):

### Existence / feasibility
- “Does there exist a stable model of `P ∪ I`?”
- Typical spec: “Does there exist a solution?”

### Brave reasoning (∃ stable model)
- “Is atom `a` true in **some** stable model of `P ∪ I`?”

### Cautious reasoning (∀ stable models)
- “Is atom `a` true in **all** stable models of `P ∪ I`?”

### Optimization (weak constraints / #minimize)
- “Is `X` an **optimal** stable model?”
- “Is `a` true in some/all **optimal** stable models?”

> Your *mathematical formulation* should determine which of these you are implementing.

---

## 2. Second decide: which *program fragment* does your encoding belong to?

Key syntactic axes (in the ground program):

- **Positive normal**: no default negation `not` (purely monotone rules).
- **Normal**: default negation allowed, but head is a single atom.
- **Disjunctive**: head may contain disjunction (multiple atoms).
- **Optimization**: weak constraints / `#minimize` / similar optimization statements.

The fragment matters because it fixes the “natural” complexity level.

---

## 3. Complexity results you can cite (table)

Let `a` be an atom and `X` a set of atoms.

### Positive normal logic programs `P`
- Decide whether `X` is **the** stable model of `P`: **P-complete**
- Decide whether `a` is in the stable model of `P`: **P-complete**

### Normal logic programs `P`
- Decide whether `X` is a stable model of `P`: **P-complete**
- Decide whether `a` is in **a** stable model of `P`: **NP-complete**

### Normal programs + optimization
- Decide whether `X` is an **optimal** stable model: **coNP-complete**
- Decide whether `a` is in an optimal stable model: **Δ₂^p-complete**

### (Positive) disjunctive logic programs `P`
- Decide whether `X` is a stable model of `P`: **coNP-complete**
- Decide whether `a` is in **a** stable model of `P`: **NP^NP-complete** (i.e., **Σ₂^p-complete**)

### Disjunctive programs + optimization
- Decide whether `X` is an **optimal** stable model: **coNP^NP-complete**
- Decide whether `a` is in an optimal stable model: **Δ₃^p-complete**

---

## 4. How to argue membership (upper bounds) for your encoding

### NP-style “guess & check”
If your encoding is a classic generate–test normal program:
1. **Guess** the candidate structure (choice/disjunction-in-body patterns via `not`).
2. **Check** constraints and derived properties in polynomial time.

This matches NP membership.

### Σ₂^p-style “guess with NP oracle”
If you use **disjunctive heads**, you typically move one level up:
- membership arguments align with **NP with NP-oracle** (Σ₂^p).

### Optimization lifts levels
When you add optimization:
- you are comparing models (“is there a strictly better one?”), which often introduces a coNP check inside an outer existential, lifting to Δ-levels as in the table.

---

## 5. How to argue hardness (lower bounds) in a reusable way

A common paper-friendly pattern:

1. Choose a known complete problem at the target level:
   - NP: SAT / 3SAT
   - Σ₂^p: QBF with prefix ∃∀ (or equivalent)
2. Give a polynomial reduction mapping an instance `J` to facts `I(J)` such that:
   - `J` is YES  iff  `P ∪ I(J)` has a stable model  
   (or iff atom `a` is bravely entailed, etc.)

You do *not* need to re-prove ASP’s completeness results from scratch—just show your encoding implements the reduction.

---

## 6. Data complexity vs combined complexity (don’t mix them silently)

When people say “ASP is NP-complete / Σ₂^p-complete”, they often mean **combined complexity** (program and data both input).

If your program `P` is fixed and only facts `I` vary, you are often closer to **data complexity**:
- many useful encodings have lower data complexity than their worst-case combined complexity.

If you need this distinction in your documentation, state it explicitly.

---

## 7. Quick “complexity checklist” for clingo encodings

1. What is the decision problem? Existence / brave / cautious / optimal?
2. Is the grounded program:
   - positive normal,
   - normal,
   - disjunctive,
   - using optimization?
3. Use the table to read off the baseline PH level.
4. If you use additional language features (theories, external atoms, epistemic operators), state that complexity may differ from the base table and treat it as an extension.
5. Provide one short paragraph:
   - membership argument (algorithm sketch),
   - hardness argument (reduction name + idea).



---

# 3. Theorem‑assisted workflow

# Theorem‑Assisted Workflow for clingo Encodings (Proof + Complexity)

This file is designed for inclusion in a “proof-aware” custom GPT for clingo.

---

## 1. Recommended documentation block to include in every encoding

Add a header comment in your `.lp` file:

- **Input facts:** list predicates and intended meaning.
- **Output predicates:** exactly which atoms define the solution.
- **Specification:** a short mathematical definition of solutions.
- **Correspondence claim:** “Stable models projected to output predicates = solutions.”
- **Reasoning task:** existence / brave / cautious / optimal.
- **Fragment:** positive normal / normal / disjunctive / optimization.

This forces proof obligations to become explicit.

---

## 2. Standard proof plan (copy/paste skeleton)

### 2.1 Define the projection
- `sol(X) := { out(t) | out(t) ∈ X }`
- Mention which auxiliaries are ignored.

### 2.2 Prove soundness
Break into micro-lemmas:
- Lemma G: “Generated structure is well-formed” (uniqueness / totality).
- Lemma D: “Derived auxiliaries match intended closure” (reachability, transitive closure, etc.).
- Lemma T: “All constraints match spec conditions”.

Conclude `sol(X)` satisfies the math definition.

### 2.3 Prove completeness
- For any solution `s`, build `X_s`.
- Show `X_s` satisfies rules and constraints.
- Show stability using reduct + positive closure for definitional parts.

---

## 3. Stability proof tricks that GPT should try first

### 3.1 Reduce stability to closure on a positive subprogram
If your auxiliaries are derived by a positive set of rules:
- show they are exactly `Cn(Q)` where `Q` is that positive subprogram.

### 3.2 Check tightness (normal programs)
If there are no positive cycles in dependencies:
- you can argue via completion-style reasoning (stable = supported).

### 3.3 Avoid circular “definitions”
If you define `p` in terms of `p` positively, supported models may appear without true justification.
Prefer stratified definitions or add explicit “breakers” (ranking, induction on size, etc.).

---

## 4. Complexity classification prompts (what GPT should ask itself)

When asked “what’s the complexity of this encoding?”, the assistant should:

1. Identify whether the question is:
   - “does a model exist?”,
   - “is atom a in some/all models?”,
   - “optimality?”.
2. Identify the fragment:
   - normal vs disjunctive, optimization present?
3. Return the complexity class from the standard table.
4. (If needed) sketch:
   - NP / Σ₂^p membership algorithm (“guess/check”),
   - matching hardness reduction strategy.

---

## 5. Common pitfalls when proving correctness (and how to catch them)

### 5.1 Auxiliary predicates leak into the solution notion
Fix: always define `sol(X)` by projection.

### 5.2 Over-constraining (incomplete encoding)
Symptom: a valid math solution cannot be realized as a stable model.
Fix: in completeness proof, construct `X_s`; if you cannot satisfy some rule, that rule is too strong.

### 5.3 Under-constraining (unsound encoding)
Symptom: a stable model exists that violates the spec.
Fix: in soundness, attempt to derive each spec condition; missing constraint usually becomes obvious.

### 5.4 Hidden disjunction via aggregates/encodings
Even without explicit disjunctive heads, some modeling patterns may simulate higher-level reasoning.
If you need formal classification, state assumptions (grounding, fragment, feature set).

---

## 6. “Proof artifacts” you can ask users to provide to speed up theorem-assisted work

Ask for:

- the exact `.lp` encoding (or relevant module),
- the intended spec in math/pseudocode,
- the list of output predicates,
- one positive and one negative test instance (facts) with expected outcomes.

With these, the assistant can produce:
- soundness/completeness proof skeletons,
- complexity classification,
- minimal counterexample search guidance.


