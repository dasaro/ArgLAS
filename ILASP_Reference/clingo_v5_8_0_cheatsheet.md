# Clingo v5.8.0 Cheat Sheet (compact)

This is a compact reference for the **gringo/clingo input language** (ASP) plus a few common advanced constructs used with **clasp/clingo** (optimization, heuristics) and **asprin** (preferences).

---

## 0) Run / ground / inspect

```bash
# Solve (1 model by default; use 0 to enumerate all models)
clingo program.lp
clingo 0 program.lp

# Show the grounded program (text output)
clingo --text program.lp
gringo --text program.lp

# Pipe grounder to clasp (classic workflow)
gringo program.lp | clasp 0
```

Common patterns:
- Encode in `*.lp`, invoke `clingo <nmodels> file.lp`.
- Use `--text` when debugging grounding.

---

## 1) Building blocks: terms, atoms, literals

### Terms
- **Constants**: `a`, `foo`, `bar42`, integers `0`, `-3`, quoted strings `"hello"`.
- **Variables**: start uppercase: `X`, `Person`, `_` is anonymous.
- **Function terms**: `f(X,3)`.
- **Tuples**: `(X,Y)`; and term tuples are written comma-separated in some constructs.

Special constants:
- `#inf`, `#sup` (used in ordering / comparisons).

### Atoms and literals
- **Atom**: `p(t1,...,tn)` where `p/n` is the predicate and arity.
- **Classical (strong) negation**: `-p(X)` (a different atom than `p(X)`).
- **Default negation**: `not p(X)` (negation-as-failure).
- **Double negation**: `not not p(X)` (often used to express support / optionality).

---

## 2) Rules, facts, constraints

### Syntax
- **Fact**: `p(a).`
- **Rule**: `Head :- Body.`
- **Body** is a comma-separated conjunction of literals, comparisons, aggregates, etc.
- **Disjunction** in the head uses `;`:
  ```prolog
  a; b :- c.
  ```
- **Integrity constraint** (no head):
  ```prolog
  :- a, not b.
  ```

### Safety (very important)
A rule is **safe** if every variable appears in some *positive* body literal that binds it (built-ins and some term contexts do *not* bind variables). When in doubt, add a domain predicate like `dom(X)` in the body.

### Semantics (what “an answer set” means, at a glance)
- clingo **grounds** your program first (variables are replaced by all safe instantiations).
- The solver then computes **stable models / answer sets** of the grounded program.
- Default negation `not p` is interpreted via the stable-model test (closed-world reasoning), while classical negation `-p` is part of the atom itself.


---

## 3) Syntactic sugar: pooling and intervals

### Pooling with `;`
- A pooled term expands into multiple instances:
  - `p(a;b).` is shorthand for `p(a). p(b).`
  - Pooling can occur inside terms and arguments.

### Intervals `L..U`
- Numeric interval `1..5` expands over integers:
  ```prolog
  p(1..3).  % expands to p(1). p(2). p(3).
  ```

---

## 4) Choice rules and cardinality constraints

### Unrestricted choice
```prolog
{ q(X) : p(X) }.
```
Meaning: for every `X` with `p(X)`, `q(X)` may be chosen true or false.

### Bounded choice / cardinality
```prolog
1 { hotel(1..5) } 1.     % exactly one hotel
l { a(X) : dom(X) } u.   % between l and u chosen
```
Notes:
- Bounds can be omitted; default is `0` and “unbounded above”.
- Choice rules are implemented as **head aggregates**.

---

## 5) Conditions and conditional literals

A **condition** uses `:` and acts like a local conjunction that filters instantiations.

Examples:
```prolog
{ q(X) : p(X) }.                 % conditional literal in a choice
sum(S) :- S = #sum { W,X : item(X,W) }.
```

---

## 6) Comparisons and arithmetic

### Comparisons (built-ins)
```prolog
X = Y
X != Y
X < Y   X <= Y   X > Y   X >= Y
```

### Arithmetic in terms
- Usual operators: `+ - * / \` (division/modulo conventions depend on the integer arithmetic supported by clingo).
- When arithmetic may be undefined (e.g., division by 0), guard it:
  ```prolog
  z(Z) :- X/Y = Z, Y != 0, x(X), y(Y).
  ```

---

## 7) Aggregates (core + advanced)

General form (body context):
```prolog
#count { T : Lits }      #sum { W,T : Lits }      #min { T : Lits }      #max { T : Lits }      #avg { T : Lits }
```

### Guards / bounds
```prolog
18 <= #sum { H,C : enroll(C), hours(C,H) } <= 20.
```

### Binding aggregate results with `=`
```prolog
courses(N) :- N = #count { C : enroll(C) }.
hours(N)   :- N = #sum   { H,C : enroll(C), hours(C,H) }.
```

### Safety & local variables
- Variables inside `{ ... }` that occur only in the aggregate element are **local** to that element.
- If a variable must range over something, add an explicit domain predicate in the condition.

---

## 8) Optimization: weak constraints and #minimize/#maximize

### Weak constraints
A weak constraint has the form:
```prolog
:~ Body. [W@P, T1, ..., Tk]
```
- `W` is an integer weight.
- `@P` is an optional priority (defaults to `0`).
- `(T1,...,Tk)` is an optional tuple for tie-breaking (included at most once per satisfied instance).

Semantics: answer sets are compared by **lexicographic** optimization over priorities (higher `P` is more important), minimizing total weight per priority.

### Optimization statements
Instead of writing many weak constraints, use:
```prolog
#minimize { W@P,Tuple : Body }.
#maximize { W@P,Tuple : Body }.
```
A `#minimize` statement corresponds to a set of weak constraints; a `#maximize` is the same with inverted weights.

#### Example pattern
```prolog
1 { hotel(1..5) } = 1.
noisy :- hotel(X), main_street(X).

#maximize { Stars@1,X : hotel(X), star(X,Stars) }.
#minimize { Cost/Stars@2,X : hotel(X), cost(X,Cost), star(X,Stars) }.
:~ noisy. [1@3]
```

---

## 9) asprin (preferences beyond linear objectives)

asprin extends clingo with a **preference specification** language.

### Preference statements and optimize directive
A preference statement has the form:
```prolog
#preference(S, T){ e1; ...; en } : B.
```
and an optimization directive has the form:
```prolog
#optimize(S) : B.
```
`B` is used only to instantiate variables (and must be evaluable during grounding).

### Subset-minimization example
```prolog
dom(1..3).
{ a(X) : dom(X) }.

#preference(p1,subset){ a(X) : dom(X) }.
#optimize(p1).
```

### Weighted (less(weight)) mapping from #minimize
Native clingo minimization:
```prolog
#minimize { C,X,Y : cycle(X,Y), cost(X,Y,C) }.
```
asprin encoding with `less(weight)`:
```prolog
#preference(myminimize,less(weight)){
  C,X,Y :: cycle(X,Y), cost(X,Y,C)
}.
#optimize(myminimize).
```

### Library preference types (common ones)
`subset`, `superset`, `less(cardinality)`, `more(cardinality)`, `less(weight)`, `more(weight)`, `minmax`, `maxmin`, `aso`, `poset`, `cp`, ...

---
## 10) Meta-statements you’ll actually use
 Meta-statements you’ll actually use

### Comments
```prolog
% single-line
%* multi-line *%
```

### Output control: `#show`
```prolog
#show p/n.                  % show only selected predicates (if any show-atoms exists)
#show t : L1,...,Ln.        % show term t when condition holds
#show.                      % show nothing (useful before show-terms to hide all atoms)
```

### Constants: `#const`
```prolog
#const n = 42.
```
Override from CLI:
```bash
clingo -c n=10 program.lp
```

### External atoms: `#external`
```prolog
#external q(X) : p(X).
```
Use-case: multi-shot / incremental solving where some atoms are provided externally.

### Program parts: `#program`
```prolog
#program base.
#program step(t).
```
Rules up to the next `#program` belong to the current part; default part is `base/0`.

### Include files: `#include`
```prolog
#include "common.lp".
```

---

## 11) External functions via Lua/Python (`#script`, `@fun`)

### Embed script
```prolog
#script (python)
import clingo
N = clingo.Number
def gcd(a,b): ...
#end.
```

### Call external function during grounding
External calls are prefixed by `@`:
```prolog
gcd(X,Y,@gcd(X,Y)) :- p(X,Y).
```

Notes:
- External functions are assumed **deterministic**.
- If an external function errors, the current rule/condition instance can be dropped by the grounder.

Returning multiple values is possible (e.g., returning a list/range to generate many instances).

---

## 12) Heuristic directives (solver control)

Heuristic directives can influence the search:
```prolog
#heuristic a. [10,level]
#heuristic b. [1,sign]
#heuristic c : b. [1,sign]
#heuristic c : not b. [-1,sign]
```
Modifiers like `true` / `false` can set both sign and level in one directive.

---

## 13) Theory atoms / extensions (example: clingo-dl)

Example of a theory atom (difference constraints):
```prolog
&diff {x-y} <= -4.
```
Some extensions support a `--strict` mode altering the relation between the theory atom and the constraint it represents.

---

## 14) Debugging grounding issues (fast checklist)

- “atom is undefined”: predicate used in a body but never defined or declared external → check typos / missing rules.
- “term undefined”: arithmetic undefined (e.g., division by 0) or external function error → guard with conditions like `Y!=0`.
- If something mysteriously disappears: remember that some instantiations containing undefined terms are **discarded**.

---

## 15) Minimal template (copy/paste)

```prolog
% Domain
dom(1..n).

% Guess
{ pick(X) : dom(X) }.

% Define
ok(X) :- pick(X), not bad(X).

% Constraints
:- pick(X), pick(Y), X != Y, conflict(X,Y).

% Aggregates
num_picked(N) :- N = #count { X : pick(X) }.

% Optimization (optional)
#minimize { 1@1,X : pick(X) }.

% Output
#show pick/1.
#show num_picked/1.
```
