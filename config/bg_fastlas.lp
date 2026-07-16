% FastLAS learning background (verifier formulation, ported from the
% Real_World_Examples/fastlas_exp lab). A labelling is GIVEN as context facts
% (in/out; undec is derived), and target-independent structural features are
% computed from it. NO choice rules: FastLAS learns normal rules, so BG+H must
% stay deterministic per context (one answer set per example).
attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y).
undec(X) :- arg(X), not in(X), not out(X).
