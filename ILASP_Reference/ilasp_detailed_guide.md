# ILASP (v4-style) bias & mode declarations — a slightly more detailed guide

This guide is written to be “drop-in” for a custom GPT: it focuses on **what each directive means**, the
common **underspecified concepts** (e.g., anti_reflexive vs. reflexive), and the **practical knobs**
(#maxv, #max_penalty, CLI flags) you will actually use.

**Primary references**
- ILASP online manual (doc.ilasp.com): *Mode Declarations*, *Meta-level ASP hypothesis space*, *Parameters to ILASP*, *Ordering Examples*.
- ILASP4 / CDILP paper (your attached PDF) for the formal view of penalties / noise / optimisation.

---

## 1) What the mode declarations are for (big picture)

ILASP learns a hypothesis program `H` such that, together with your **background knowledge** `B`, it
covers your examples. To keep learning finite (and fast), you must define a **hypothesis space** —
the set of rules ILASP is allowed to use in `H`.

A “mode bias” is the classic way to specify this hypothesis space: you say what can appear
in the **head** and **body** of learned rules (and how often).

---

## 2) `#mode{h,b,ha,c,o}` — what each one “stands for”

ILASP uses several “mode declaration” predicates. They are all *meta-level* declarations (not ordinary ASP facts).

### 2.1 `#modeh(...)` — head literals for normal rules
“h” = *head*.

Declares which **ordinary atoms** may appear in the **head** of learned rules (normal rules / constraints).

Examples:
```prolog
#modeh(owns(var(animal))).
#modeh(flies(var(bird))).
```

### 2.2 `#modeb(...)` — body literals for normal rules
“b” = *body*.

Declares which literals may appear in the **body** of learned rules.

Examples:
```prolog
#modeb(1, bird(var(animal))).
#modeb(1, not_penguin(var(animal)), (positive)).  % see "positive" option below
```

> Note: By default, ILASP may consider both `p(...)` and `not p(...)` in bodies, unless restricted.

### 2.3 `#modeha(...)` — “aggregate head” declarations (choice-rule heads)
“ha” = *head aggregate* (the manual calls them “aggregate head declarations”).

This is used to allow ILASP to learn **choice rules** (rules with heads like `0 { ... } 1`).

Typical usage:
```prolog
#modeha(select(var(item))).
```

This makes literals of the form `select(X)` eligible to occur **inside choice-rule heads**, e.g.:
```prolog
0 { select(X) } 1 :- candidate(X).
```

### 2.4 `#modec(...)` — condition declarations (conditional literals)
“c” = *condition*.

Conditional literals in ASP look like `p(X) : q(X)` inside a head or body.
ILASP represents those conditions via `#modec`, which is defined “like `#modeb`” but for the condition part.

Example:
```prolog
#modec(1, allowed(var(item))).
```

### 2.5 `#modeo(...)` — optimisation body declarations (for weak constraints)
“o” = *optimisation*.

Weak constraints have bodies (the part after `:~`) that drive preference learning.
`#modeo` says which literals can appear in the **body of learned weak constraints**.

Example:
```prolog
#modeo(1, cost(var(x), var(n))).
#modeo(1, late(var(job))).
```

---

## 3) The “first argument” (recall / usage bound)

Many mode declarations can be written with an initial integer:

```prolog
#modeb(2, p(var(t))).
```

This first argument is called **recall**: an **upper bound** on how many times that particular
mode declaration may be used **within a single learned rule**.

### 3.1 Intuition
- `#modeb(1, p(var(t)))`  
  → in any learned rule, you can use *at most one* `p(...)` body literal generated from this mode.
- `#modeb(2, p(var(t)))`  
  → in any learned rule, you can have up to two `p(...)` literals (possibly with different variables/terms).

This is a *search-space control*: it reduces combinatorial blowup.

### 3.2 If you omit recall
The online manual explains recall but does not explicitly state the default when recall is omitted.
Some ILASP materials treat omission as **unrestricted (effectively infinite) recall**.  
Practical recommendation: **write recall explicitly** to avoid surprises and to keep search manageable.

---

## 4) Placeholders and typing: `var(t)`, `const(t)`, `#constant(t,c)`

Mode templates can contain placeholders:

- `var(t)` means “a variable of type `t`”
- `const(t)` means “a constant of type `t`”

To allow constants for `const(t)`, you declare them:

```prolog
#constant(color, red).
#constant(color, blue).

#modeb(1, likes(var(person), const(color))).
```

ILASP will ensure consistent typing: it won’t reuse the same variable name as two different types inside one rule.

---

## 5) “Extra options” in mode declarations (anti_reflexive, symmetric, positive)

A mode declaration can optionally end with a tuple of *options*, e.g.:

```prolog
#modeb(1, same_row(var(cell), var(cell)), (anti_reflexive)).
```

These options are primarily **syntactic search-space restrictions**, not semantic axioms.

### 5.1 Reflexive / irreflexive / anti_reflexive (what people often mean)

**Mathematical definitions (semantic):**
- A binary relation `R` is **reflexive** if ∀x: R(x,x) holds.
- **Irreflexive** (sometimes called anti-reflexive) if ∀x: R(x,x) does *not* hold.

**ILASP option `anti_reflexive` (syntactic):**
- Intended for predicates of arity 2.
- It prevents ILASP from generating literals where the same variable occurs twice:
  `p(X,X)` is disallowed by that mode declaration.

So `anti_reflexive` does **not** enforce that `p(a,a)` is false in the learned program; it only
prevents a particular *shape* of literal from appearing in candidate rules.

### 5.2 Symmetric (semantic vs. ILASP’s use)

**Semantic symmetry:**
- `R` is symmetric if R(x,y) ⇒ R(y,x).

**ILASP option `symmetric` (syntactic equivalence):**
- Treats `p(X,Y)` and `p(Y,X)` as *equivalent for generation* so it generates only one of them.
- This avoids duplicate candidate rules that are “the same up to swapping arguments”.

Again: it doesn’t add the axiom `p(X,Y) :- p(Y,X).` — it’s a **generation** trick.

### 5.3 Antisymmetric / asymmetric (common confusion)

These are **not** listed as built-in mode options in the online manual.

**Semantic antisymmetric:**  
R(x,y) and R(y,x) ⇒ x=y.

**Semantic asymmetric:**  
R(x,y) ⇒ not R(y,x) (implies irreflexive).

If you want these properties, you typically encode them as **background constraints** or as a
**meta-level bias constraint** (see §8):
- Background constraint style:
  ```prolog
  :- p(X,Y), p(Y,X), X != Y.   % antisymmetry
  ```
- Or add a bias constraint inside `#bias("...")` to prune hypotheses that violate your shape constraints.

### 5.4 `positive` option
`positive` means: do **not** generate the *negation-as-failure* version of that predicate from this mode.
So if you declare:
```prolog
#modeb(1, q(var(t)), (positive)).
```
ILASP will allow `q(X)` but will not generate `not q(X)` from that mode declaration.

### 5.5 Extra *global* options aimed at choice rules (`#modeha`)
The manual also mentions a few extra controls that are particularly useful when your search space contains
many possible **choice-rule heads**:

```prolog
#disallow_multiple_head_variables.
#minhl(1).
#maxhl(2).
```

- `#disallow_multiple_head_variables.`  
  Prevents more than one distinct variable appearing in the head of a choice rule.  
  (This is a *search-space restriction* to avoid “exploding” choice heads.)

- `#minhl(M)` / `#maxhl(M)`  
  Bounds the **minimum/maximum number of literals** that may occur in the head of a learned choice rule.

These are handy when ILASP is generating huge numbers of multi-literal choice heads and you
know your target rules are small.



---

## 6) Global structure bounds: `#maxv` and `#max_penalty`

### 6.1 `#maxv(K)` — bound the number of variables per learned rule
Example:
```prolog
#maxv(2).
```

Means: any learned rule in the hypothesis may use **at most K distinct variables**.

This is extremely important for grounding / search size.

### 6.2 `#max_penalty(K)` — bound the size/cost budget for the hypothesis
Example:
```prolog
#max_penalty(25).
```

The online manual describes `#max_penalty` as an **upper bound on the size of the hypothesis returned**
(with a default of 15 in the manual text). In practice:

- ILASP searches for an *optimal* hypothesis, trading off hypothesis length/cost and (if using noise)
  penalties for uncovered examples.
- `#max_penalty` acts like a **budget** that prevents ILASP from exploring hypotheses that are too large/expensive.

> Heuristic: if ILASP says “no solution” but you suspect one exists, try increasing `#max_penalty`
> and/or the CLI limits in §7.

---

## 7) Useful ILASP command-line flags (practical workflow)

A typical run:
```bash
ILASP --version=4 task.las
```

### 7.1 Inspecting what ILASP thinks your hypothesis space is
- `-s` / `--search-space`  
  Print the **search space** generated from your mode bias.

- `-t` / `--task-program`  
  Print the **ASP meta-level task encoding** used internally (useful for debugging why a rule is or isn’t possible).

Often used together:
```bash
ILASP --version=4 -s -t task.las
```

### 7.2 Debugging and verbosity
- `-d` / `--debug`  
  Print intermediate hypotheses and internal progress (very helpful if learning stalls).

- `-q` / `--quiet`  
  Only print the final solution.

### 7.3 Controlling hypothesis complexity (CLI-level)
These are *additional* bounds beyond `#maxv`/`#max_penalty`:

- `--max-rule-length=N` (default 5)  
  Max number of literals in each learned rule.

- `-ml=N` (default 3)  
  Max number of body literals.

- `--max-wc-length=N` (default 3)  
  Max number of literals in each learned weak constraint body.

These are often the first knobs to turn if you’re learning weak constraints.

### 7.4 Running with a specific clingo and options
- `--clingo "path [options]"`  
  Use a particular clingo binary and pass it options.
  Example:
  ```bash
  ILASP --version=4 --clingo "/usr/bin/clingo --warn=none" task.las
  ```
  Caution: some clingo options can interfere with ILASP’s procedure.

### 7.5 Speeding up repeated runs
- `--cache-path=FILE`  
  Reuse cached structures between runs when you only add examples / tweak small parts.

### 7.6 Printing the PyLASP script
- `-p`  
  Prints the PyLASP script corresponding to your current configuration (useful if you plan to automate runs).

## 7.7 A note on *legacy* ordering-example syntax
The current online manual uses a 3-argument form:

```prolog
#brave_ordering(eg_a, eg_b, <).
#cautious_ordering(eg_a, eg_b, <).
```

You may still encounter older `.las` files that omit the comparison operator, e.g. `#brave_ordering(best, p1).`.
If you are standardising tasks (or building a custom GPT that should generate tasks), prefer the **explicit**
3-argument form from the online manual.



---

## 8) Debugging and advanced biasing: `#bias("...")` + `--override-default-sm`

ILASP can build the hypothesis space from an **ASP meta-program**:

```prolog
#bias("
   ... ASP program ...
").
```

### 8.1 Extending the default mode->hypothesis encoding
If you have any mode declarations, ILASP typically enables a default translation of modes into a
meta-level hypothesis generator. `#bias` can *add constraints* to prune hypotheses.

Example: disallow using `p/1` and `q/1` together in the same body:
```prolog
#bias(":- body(p(_)), body(q(_)).").
```

### 8.2 Seeing the full meta-encoding
Run with `-s -t` to view both the expanded search space and the meta-level encoding.

### 8.3 Fully overriding default behaviour
Sometimes you want to **disable** the default mode interpretation and supply your own meta-program.

Use:
```bash
ILASP --version=4 --override-default-sm task.las
```

---

## 9) Worked micro-example: interpreting `#modeb(1, same_row(var(cell), var(cell)), (anti_reflexive)).`

```prolog
#modeb(1, same_row(var(cell), var(cell)), (anti_reflexive)).
```

Read it as:

1. `#modeb`  
   → this declares a **body** literal schema.

2. `1` (recall)  
   → in any *single* learned rule, ILASP can use **at most one** body literal derived from this schema.

3. `same_row(var(cell), var(cell))`  
   → the body literal is `same_row(X,Y)` where `X` and `Y` are variables of type `cell`.

4. `(anti_reflexive)`  
   → ILASP will not generate the *syntactic* case `same_row(X,X)` from this schema.

So ILASP can generate `same_row(V1,V2)` but not `same_row(V1,V1)`.

---

## 10) Common pitfalls & rules of thumb

- **Always bound something**: at least `#maxv`, and usually use recall bounds on body modes.
- If you want a *semantic* constraint (antisymmetry, acyclicity, transitivity, etc.), encode it
  in **background knowledge** or as a **bias constraint**, not as a mode option.
- When learning weak constraints, you often need to increase:
  - `#max_penalty`
  - `--max-wc-length`
  - `--max-rule-length`
- Use `ILASP -s` early: if the rule you want is not in the printed search space, ILASP cannot learn it.

---

## 11) Quick reference table

| Directive | Meaning | Main use |
|---|---|---|
| `#modeh(...)` | allowed head atoms | learn normal rules |
| `#modeb(r, ...)` | allowed body atoms, with recall `r` | control rule bodies |
| `#modeha(...)` | allowed atoms inside choice-rule heads | learn choice rules |
| `#modec(...)` | allowed condition literals | learn conditional literals |
| `#modeo(r, ...)` | allowed literals in weak-constraint bodies | learn weak constraints |
| `#maxv(K)` | max variables per learned rule | keep search finite |
| `#max_penalty(K)` | hypothesis size/cost budget | allow larger hypotheses |
| `-s` | print generated search space | sanity-check learnability |
| `-t` | print meta-level task encoding | debug deep issues |
| `--override-default-sm` | override default mode translation | custom meta-bias |

---

### Where this guide matches (and differs from) the manual
- All named directives and options above are taken from the ILASP online manual.
- Concepts like *antisymmetry* are explained as semantic properties; **they are not listed as built-in mode options**,
  so you should encode them explicitly if needed.
