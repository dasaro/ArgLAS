# clingo Python API + Propagators + Restart Strategies cheatsheet (v5.8)

This is a **practical**, copy/paste-oriented cheatsheet for **clingo 5.8.x** covering:

- **Python API**: `Control`, multishot, solving/model iteration, symbols, externals, backend/observer, AST, configuration, statistics, and building apps.
- **Propagators**: `Propagator`, watches, clauses/nogoods, `check_mode`/`undo_mode`, threading notes.
- **Restart strategies** (clasp via clingo CLI): `--restarts` schedules and related knobs.

> Docs baseline for Python API: `https://potassco.org/clingo/python-api/5.8/`

---

## Table of contents
1. Python API (core)
2. Propagators (Python)
3. Restart strategies (clasp options via clingo)

---


# clingo Python API cheatsheet (from the official Potassco online docs, v5.8)

This is a **practical**, copy/paste-oriented cheatsheet covering the most-used parts of clingo’s Python API:
- **Grounding & solving** (`Control`, `SolveHandle`, `Model`)
- **Symbols** (`Function`, `Number`, `parse_term`)
- **Multishot & externals**
- **Symbolic atoms & theory atoms**
- **Backend/Observer** (programmatic ground rule injection / inspection)
- **AST parsing** (`clingo.ast.parse_string/parse_files`)
- **Configuration & statistics**
- **Building a custom clingo-based app** (`clingo.application`)

> Docs baseline: `https://potassco.org/clingo/python-api/5.8/`

---

## 0) Imports you’ll use all the time

```python
import clingo
from clingo import Control
from clingo.symbol import Function, Number, String, Tuple_, parse_term
```

---

## 1) `Control`: the central object (add → ground → solve)

### Minimal “one-shot” solve
```python
from clingo import Control

ctl = Control()
ctl.add("base", [], "a. b :- a. #show a/0. #show b/0.")
ctl.ground([("base", [])])

res = ctl.solve(on_model=lambda m: print(m.symbols(shown=True)))
print(res)  # SAT / UNSAT / UNKNOWN
```

### Notes you *want* to remember
- `Control(arguments=[...])` accepts *grounder + solver* options; and you must **not** call other `Control` methods while a solve is active.
- `add(program)` is shorthand for `add("base", [], program)`.

---

## 2) Multishot workflow (ground in steps, solve repeatedly)

### Classic pattern: `#program` parts
```python
from clingo import Control
from clingo.symbol import Number

ctl = Control()
ctl.add("base", [], r"""
#program base.
{ a(1..3) }.

#program step(t).
b(t) :- a(t).
#show b/1.
""")

ctl.ground([("base", [])])

for t in range(1, 4):
    ctl.ground([("step", [Number(t)])])
    print("t =", t, "=>", ctl.solve(on_model=lambda m: print(m.symbols(shown=True))))
```

---

## 3) Solving APIs: `solve(...)`, `SolveHandle`, async, and model iteration

### A) Standard callback style: `on_model=...`
```python
def on_model(m):
    print("Answer:", " ".join(map(str, m.symbols(shown=True))))
ctl.solve(on_model=on_model)
```

### B) Iterating models: `yield_=True`
```python
with ctl.solve(yield_=True) as h:
    for m in h:
        print("Model:", m)
    print("Result:", h.get())
```

### C) Asynchronous solve: `async_=True`
```python
with ctl.solve(async_=True, on_model=print) as h:
    # do something else...
    h.wait()          # blocks until a result is ready (or search finishes)
    print(h.get())    # final SolveResult (blocks if needed)
```

### D) Iteration + async together
```python
with ctl.solve(yield_=True, async_=True) as h:
    while True:
        h.resume()
        _ = h.wait()        # can use timeout=0 to poll
        m = h.model()
        if m is None:
            print("Done:", h.get())
            break
        print("Next:", m)
```

### SolveHandle quick reference
- `resume()` : discard current model and continue search
- `model()` : current model (or `None`)
- `last()`  : last computed model (or `None`)
- `wait(timeout=None)` : wait for next result / finish
- `get()` : final `SolveResult`
- `cancel()` : cancel search
- `core()` : unsat core subset of assumptions (when relevant)

---

## 4) `Model`: inspect what you got (atoms, costs, optimization)

### Common model queries
```python
def on_model(m):
    shown = m.symbols(shown=True)
    atoms = m.symbols(atoms=True)      # all atoms (ignores #show)
    print("shown:", shown)
    print("cost :", m.cost, "prio:", m.priority, "opt-proven:", m.optimality_proven)
    print("model#", m.number, "thread:", m.thread_id)
```

### `Model.symbols(...)` flags
- `shown=True`: what clingo would print (respecting `#show`)
- `atoms=True`: all atoms in the model
- `terms=True`: all `#show` terms
- `theory=True`: include symbols added via `Model.extend(...)`
- `complement=True`: complement w.r.t. atoms known to the grounder

### Fast membership test
```python
if m.contains(Function("p", [Number(1)])):
    print("p(1) is in the model")
```

### Extending printed output (for app integrations)
```python
m.extend([Function("extra", [Number(7)])])
```

---

## 5) Symbols: `Function/Number/String/Tuple_` and `parse_term`

### Constructing symbols
```python
x  = Number(42)
s  = String("hi")
t  = Tuple_([Number(1), Number(2)])
f  = Function("p", [Number(1), Number(2)])   # p(1,2)
c  = Function("a")                           # constant a
```

### Parse a term (with evaluation of arithmetic)
```python
parse_term("p(1+2)")   # -> p(3)
```

Symbols are ordered/comparable like in gringo; they can be dictionary keys.

---

## 6) Symbolic atoms: inspect the grounded atom base

### `ctl.symbolic_atoms`
Useful for:
- mapping symbols ↔ **program literals**
- querying whether atoms are facts/external/etc.

```python
from clingo.symbol import Function

sa = ctl.symbolic_atoms
atom = sa[Function("a")]          # lookup by symbol
if atom is not None:
    print(atom.symbol, atom.literal, atom.is_fact, atom.is_external)
```

`SymbolicAtom` fields you’ll use:
- `.symbol` : the `Symbol` representation
- `.literal`: the **program literal** (int)
- `.is_fact`, `.is_external`

---

## 7) Externals (multishot control knobs)

If you declared `#external e(t).` (or created one via backend), you can set its truth value before each `solve`.

```python
from clingo.symbol import Function, Number

e1 = Function("e", [Number(1)])

ctl.assign_external(e1, True)     # fix true
ctl.assign_external(e1, False)    # fix false
ctl.assign_external(e1, None)     # leave free

ctl.solve()
ctl.release_external(e1)          # release when done with it
```

---

## 8) Backend: add ground rules/facts programmatically

Use `with ctl.backend() as b:` to **inject ground statements**.

### Add a fact `a.`
```python
from clingo.symbol import Function

with ctl.backend() as b:
    atm_a = b.add_atom(Function("a"))
    b.add_rule([atm_a])           # head=[atm_a], body=[]
```

### Common backend methods (high level)
- `add_atom(symbol=None) -> int` : create/get a program atom id
- `add_rule(head, body=[], choice=False)`
- `add_weight_rule(head, lower, body_weighted_lits)`
- `add_minimize(priority, [(lit, weight), ...])`
- `add_project([atom_id, ...])`
- `add_external(atom_id, value=TruthValue.False_/True_/Free/Release)`
- `add_heuristic(atom, type_, bias, priority, condition)`
- `add_assume([lit, ...])`
- theory helpers (`add_theory_term_*`, `add_theory_atom_*`)

> Tip: backend APIs operate on **program literals/atoms** (ints), not solver literals.

---

## 9) Observer: inspect what grounding produced

Register an observer to receive callbacks about rules/atoms passed to the solver.

```python
class Obs:
    def rule(self, choice, head, body):
        print("rule:", choice, head, body)

ctl.register_observer(Obs())
ctl.ground([("base", [])])
```

Observer methods are optional; implement only what you need (e.g., `rule`, `weight_rule`, `external`, `output_atom`, `output_term`, `theory_*`, …).

---

## 10) Theory atoms: inspect `#theory` constructs after grounding

You can iterate over theory atoms:
```python
for ta in ctl.theory_atoms:
    print(ta)                 # human readable string
    print("term:", ta.term)
    print("elements:", ta.elements)
```

Theory element basics:
- `.terms` : tuple of theory terms
- `.condition` : list of program literals
- `.condition_id` : temporary program literal (useful with propagators)

---

## 11) AST parsing: `clingo.ast.parse_string/parse_files`

### Parse to AST nodes (one callback per statement)
```python
from clingo.ast import parse_string

asts = []
parse_string("a. b :- a.", asts.append)
for st in asts:
    print(st)          # round-trippable gringo representation (usually)
```

### Parse files
```python
from clingo.ast import parse_files

asts = []
parse_files(["prog.lp"], asts.append)
```

Notes:
- `parse_files` follows clingo’s CLI file handling; `"-"` is stdin; empty list reads stdin.
- You can pass a `Control` object to allow parsing ASPIF and directly add ground statements.

---

## 12) Configuration: programmatic access to clasp options

`ctl.configuration` exposes a **hierarchical** option tree.

```python
ctl = Control()
print(ctl.configuration.keys)
print(ctl.configuration.solve.keys)

# enumerate all models (equivalent to --models=0)
ctl.configuration.solve.models = 0
```

Useful patterns:
- `cfg.keys` to list subgroups/options
- `cfg.description("opt")` to see doc strings
- array groups: `cfg.solver[0].something = "..."`

---

## 13) Statistics: `--stats`, `on_statistics`, and `ctl.statistics`

### Enable statistics and attach callback
```python
from clingo.control import Control

def on_stats(step, accu):
    accu["my_counter"] = 123

ctl = Control(["--stats"])
ctl.add("base", [], "{a}.")
ctl.ground([("base", [])])
ctl.solve(on_statistics=on_stats)

print(ctl.statistics["user_accu"]["my_counter"])
```

---

## 14) Build a custom clingo-based CLI tool (`clingo.application`)

### Skeleton
```python
from clingo.application import Application, clingo_main

class App(Application):
    program_name = "myapp"
    version = "0.1"

    def main(self, control, files):
        for f in files:
            control.load(f)
        control.ground([("base", [])])
        control.solve(on_model=print)

if __name__ == "__main__":
    raise SystemExit(clingo_main(App()))
```

### Adding custom options
Implement `register_options(self, options)` and use `options.add(...)` / `options.add_flag(...)`.
Your parser callback stores the option value somewhere and returns True/False.

---

## 15) Propagators and restart strategies
See the integrated sections **“Propagators in clingo (Python API)”** and **“Restart strategies (clasp options via clingo)”** below.

---

## 16) Propagators in clingo (Python API)

This focuses on **clingo 5.8.x Python propagators** and **clasp restart-related CLI options** (as exposed through `clingo`).

---

## 1) Propagators in clingo (Python API)

A **propagator** lets you plug custom propagation / lazy constraints / custom branching into clingo’s underlying CDCL solver. You register a Python object that implements (some of) `init/propagate/undo/check/decide`, and clingo calls it during search.

### When to use propagators
- **Lazy constraints** (cutting planes / callbacks): validate a candidate assignment/model and add nogoods/clauses to rule it out.
- **Custom propagation** that’s awkward/inefficient in pure ASP (e.g., global constraints, external domain reasoning).
- **Custom decisions** (branching heuristic) via `decide`.

If your constraint fits naturally into ASP (or a supported theory), prefer normal encodings / theory solving—propagators are powerful but easier to get wrong.

---

## 2) The moving parts (types + concepts)

### Literals: “program literal” vs “solver literal”
- Your grounded ASP program yields **program literals** (clingo’s internal ids for atoms/conditions).
- Propagators work with **solver literals** (SAT-level integers).
- Use `PropagateInit.solver_literal(<program_lit_or_cond_id>)` to map to a solver literal.

### Watching literals
To avoid being called “all the time”, you **watch solver literals**:
- In `init`, `init.add_watch(lit)` can add watches for **all threads**, or a specific thread via `thread_id=...`.
- During propagation, `control.add_watch(lit)` watches only **the current solver thread**.

When a watched literal changes, clingo calls your `propagate(..., changes)` with the list of watched solver literals whose assignment just changed.

### Adding constraints: “clause” vs “nogood”
- `PropagateControl.add_clause([l1,l2,...])` adds a SAT clause (disjunction). It supports:
  - `tag=True`: clause is **volatile** (only current solving step)
  - `lock=True`: exclude from solver’s deletion policy
- `PropagateControl.add_nogood(iterable_of_lits)` is equivalent to adding the *negated* clause.

After adding a clause/nogood, call `control.propagate()` to push its unit implications immediately.

---

## 3) Minimal “shape” of a propagator

### Registering
```python
import clingo

class MyProp(clingo.Propagator):
    def init(self, init): ...
    def propagate(self, control, changes): ...
    def undo(self, thread_id, assignment, changes): ...
    def check(self, control): ...
    def decide(self, thread_id, assignment, fallback): ...

ctl = clingo.Control()
ctl.add("base", [], "a. b :- a.")
ctl.ground([("base", [])])
ctl.register_propagator(MyProp())
ctl.solve()
```

---

## 4) Lifecycle callbacks (what to do where)

### `init(self, init: PropagateInit)`
Called **before each solving step** to set up watches, static clauses, auxiliary literals, etc.

Useful API on `init`:
- `init.symbolic_atoms` to inspect atoms and get their program literals.
- `init.solver_literal(program_lit)` mapping.
- `init.add_watch(lit, thread_id=None)` and `init.remove_watch(...)`.
- `init.add_clause(clause)` to add clauses *statically* during init.
- `init.add_literal(freeze=True)` and `init.freeze_literal(lit)`:
  - **Freeze** literals you want to keep; otherwise they may be simplified away.
  - Note: adding literals makes later `add_clause/propagate` more expensive → batch additions.
- `init.check_mode` / `init.undo_mode` (see below).
- `init.number_of_threads` tells you how many solver threads will run.

### `propagate(self, control: PropagateControl, changes: Sequence[int])`
Called when watched solver literals changed. Typical pattern:
1. Inspect the current partial assignment via `control.assignment`.
2. If you detect a violated condition, add a clause/nogood.
3. Immediately call `control.propagate()` so unit propagation happens now.
4. **If** either `add_clause` or `propagate` returns `False`, stop immediately and return.

Key `control` API:
- `control.assignment`: partial assignment of the current thread
- `control.thread_id`: which thread you’re in
- `control.add_clause(..., tag=False, lock=False)`
- `control.add_nogood(...)`
- `control.propagate()`
- `control.add_watch / remove_watch / has_watch`

Threading note: `propagate` can be called from multiple solving threads; use `thread_id` to keep per-thread state or proper synchronization.

### `undo(self, thread_id: int, assignment: Assignment, changes: Sequence[int])`
Called on backtracking when assignments to watched literals are undone.
- Purpose: **update your internal state**; do **not** change the solver state here.
- Errors inside `undo` can terminate the program.

### `check(self, control: PropagateControl)`
Called depending on `check_mode` (below). Use it for lazy constraints that you only want to validate:
- on propagation fixpoints,
- on total assignments (candidate models),
- or both.

### `decide(self, thread_id: int, assignment: Assignment, fallback: int) -> int`
Optional decision hook (custom branching). If you don’t override it, clingo uses its default heuristic wiring.

---

## 5) `check_mode` and `undo_mode` (very important)

Set these in `init`:

### `init.check_mode` ∈ {`Off`, `Fixpoint`, `Total`, `Both`}
- `Off`: never call `check`
- `Fixpoint`: call `check` at propagation fixpoints
- `Total`: call `check` on total assignments (candidate models)
- `Both`: do both

Practical guidance:
- **Lazy constraints over full models** → `Total` (or `Both` if you also want earlier pruning).
- **Consistency conditions you can test on partials** → `Fixpoint`/`Both`.

### `init.undo_mode` ∈ {`Default`, `Always`}
- `Default`: call `undo` for decision levels with non-empty changes
- `Always`: also call `undo` when `check` has been called

Rule of thumb:
- If `check` updates state you need to rewind reliably, consider `Always`.

---

## 6) Assignment inspection essentials

From an `Assignment` you can query literals:
- `value(lit) -> True/False/None`
- `is_true(lit)`, `is_false(lit)`
- `level(lit)` decision level (only meaningful if assigned)

For more advanced state reasoning, clingo also exposes a chronological **trail** object (useful for incremental explanations / backtracking-aware bookkeeping).

---

## 7) “Volatile” vs “frozen/static” constraints & literals

### Volatile (per solve step / per thread)
- `PropagateControl.add_literal()` adds a **positive volatile literal** valid only in the current solving step and solver thread; it is deleted afterwards.
- Clauses with `tag=True` apply only in the current solving step.

### Static / kept
- In init, `init.add_literal(freeze=True)` and `init.freeze_literal(lit)` keep literals from being removed during preprocessing.
- In propagation, `lock=True` on `add_clause` excludes the clause from the regular deletion policy.

---

## 8) Tiny working example (pattern)

This shows the common pattern “add clause + propagate, stop on false”.

```python
import clingo

class EqProp(clingo.Propagator):
    def init(self, init):
        # watch program atoms a and b (convert to solver literals)
        atoms = init.symbolic_atoms
        a = init.solver_literal(atoms[clingo.Function("a")].literal)
        b = init.solver_literal(atoms[clingo.Function("b")].literal)
        self.a, self.b = a, b
        init.add_watch(a)
        init.add_watch(b)

    def propagate(self, control, changes):
        ass = control.assignment
        # enforce a <-> b by adding implications when one becomes true
        if ass.is_true(self.a) and not ass.is_true(self.b):
            if not control.add_clause([ self.b ]) or not control.propagate():
                return
        if ass.is_true(self.b) and not ass.is_true(self.a):
            if not control.add_clause([ self.a ]) or not control.propagate():
                return

ctl = clingo.Control()
ctl.add("base", [], "a. {b}.")     # just to have atoms
ctl.ground([("base", [])])
ctl.register_propagator(EqProp())
ctl.solve()
```

---

## 17) Restart strategies (clasp options via clingo)

### 17.1 The main switch: `--restarts,-r sched`

(Original section kept below.)

## 9) Restart strategies (clasp options via clingo)

clingo uses **clasp** for solving, and you can pass clasp options directly to `clingo`.

### The main switch: `--restarts,-r sched`
Choose and parameterize a restart policy. `sched` can be:

| sched form | meaning (conflict budget before restart) |
|---|---|
| `no` | disable restarts |
| `F,n` | fixed: restart every `n` conflicts |
| `*,n,f` | geometric: restart after `n * f^i` conflicts (i = #restarts so far) |
| `+,n,m` | arithmetic: restart after `n + m*i` conflicts |
| `L,n` | Luby/universal sequence with base unit `n` |
| `D,n,f` | dynamic “glucose-like”: restart triggered when recent clause “quality” deviates by factor `f` |

**Nested restarts**: geometric/arithmetic forms can take an optional `lim>0` to repeat sequences in a nested fashion.

### Examples (copy/paste)
```bash
# no restarts
clingo prog.lp --restarts=no

# fixed every 1000 conflicts
clingo prog.lp --restarts=F,1000

# geometric: 100, 150, 225, ...
clingo prog.lp --restarts=*,100,1.5

# arithmetic: 100, 150, 200, ...
clingo prog.lp --restarts=+,100,50

# Luby with base 100
clingo prog.lp --restarts=L,100

# dynamic (glucose-like), window=100, factor=0.7
clingo prog.lp --restarts=D,100,0.7
```

---

## 10) Restart “extras” and related knobs

These are additional restart-related options shown in the clingo/clasp extended help:

### Restart on model (often useful for optimization)
- `--restart-on-model`: restart search after finding a model; “mainly useful during optimization”.

### Updating restart sequence when a model is found
- `--reset-restarts=<arg>` where `<arg> ∈ {no|repeat|disable}` (help text: “Update restart seq. on model”).

### Local / counter / blocking restarts
- `--[no-]local-restarts`: “Use Ryvchin et al.'s local restarts”
- `--counter-restarts=<rate>[,<bump>]`: “counter implication restarts” with restart interval in *number of restarts* and a bump factor
- `--block-restarts=<n>[,<R>][,<c>][,<a>]`: glucose-style *blocking* restarts with window size, blocking factor `R`, initial conflict cutoff `c`, and moving average type `a`

### Shuffle after restarts
- `--shuffle=<n1>,<n2>|no`: “Shuffle problem after n1+(n2*i) restarts”.

---

## 11) Practical tuning workflow (restart side)
1. Start by trying a prefabricated configuration (`--configuration=tweety|trendy|...`) before hand-tuning.
2. Then try a few restart schedules (`L,n`, `*,n,f`, `D,n,f`) and compare:
   - `Conflicts`, `Choices`, `Restarts`, time (use `--stats`).
3. If optimizing, try `--restart-on-model`.

---

### Notes on provenance
- Propagator API names and meanings are based on the clingo Python API documentation and the clingo guide.
- Restart options are based on the `clingo --help=3` / extended clasp help output (what clingo exposes on the CLI).
