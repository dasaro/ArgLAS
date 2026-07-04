# Gold-standard proofs: anthem + Vampire

`anthem verify --equivalence external <learned>.lp <aspartix>.lp aaf.ug`

anthem 2 (potassco/anthem, built from source in ../tools/anthem-src) translates both
mini-gringo programs to many-sorted first-order theories (private predicates
defeated/not_defended renamed apart) and Vampire 5.0.1 discharges the generated
forward/backward conjectures. External equivalence is w.r.t. inputs arg/1, att/2 and
outputs in/1, out/1 under the assumption att ⊆ arg×arg (the theorem's "encoding of an
AAF as arg/att facts"); since defeated/not_defended have identical definitions in both
programs and are functionally determined by in/att, output equivalence entails the
thesis's full answer-set equality.

Results (Vampire, default resources):
- Theorem 4.1.1 (stable):      Theorem — proved in 241 ms
- Theorem 4.1.2 (admissible):  Theorem — proved in 277 ms
- Theorem 4.1.3 (complete):    Theorem — proved in 220 ms
- Example1 stable variant (in :- arg, not defeated): Theorem — proved

This is the third independent verification level, and the strongest: unlike the
Z3/Fages route (which relies on our own tightness check and completion transcription),
anthem implements the published io-programs theory (Fandinno–Lifschitz et al.) and
checks tightness itself.

## BAF proofs (§4.3) — via a shared-input closure reduction

Direct attempt: anthem REJECTS the natural formulation — "the following program contains
private recursion" — the support transitive closure is a private recursive predicate, which
the external-equivalence theory cannot completion-eliminate (`--bypass-tightness` does not
lift this; the rejection is principled: two private closures could denote different spurious
completion models).

Sound reduction instead (three-step argument):
1. **anthem+Vampire prove** (tight programs, no bypass, `baf2_*.lp` + `baf2.ug`): for EVERY
   relation supp with support ⊆ supp and supp∘support ⊆ supp, the learned STB/ADM/CMP
   programs are externally equivalent to the guess encodings, all with defeat defined from
   supp. Results: stable 384 ms, admissible 344 ms, complete 515 ms — all **Theorem**.
2. **Instantiation**: the actual transitive closure supp* satisfies the assumptions, so the
   equivalence holds at supp = supp*.
3. **Reformulation faithfulness**: the thesis's in-place recursive `support` background is
   answer-set-equivalent (on in/out) to the supp-reformulated background — validated by
   clingo on 2,400 randomized checks (0 mismatches), plus the independent 3,256-BAF
   exhaustive check of the original formulation in ../check_baf.py.

Net: §4.3's omitted proofs are now machine-checked, with the maximality of step 1 as a
bonus (the equivalence holds for every transitive superset, not just the closure).
