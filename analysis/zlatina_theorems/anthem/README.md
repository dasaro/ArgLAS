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
