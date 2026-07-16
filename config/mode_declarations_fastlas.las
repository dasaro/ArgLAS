% FastLAS mode bias (verifier formulation): learn a constraint theory
% `violated :- body` over the bg_fastlas.lp features. Oracle positives must
% NOT be violated; oracle negatives MUST be. Penalties make the hypothesis
% search prefer small theories (FastLAS requires an explicit #bias penalty).
#modeh(violated).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(undec(var(arg))).
#modeb(defended(var(arg))).
#modeb(attacked_by_in(var(arg))).
#modeb(attacked(var(arg))).
#modeb(not in(var(arg))).
#modeb(not out(var(arg))).
#modeb(not undec(var(arg))).
#modeb(not defended(var(arg))).
#modeb(not attacked_by_in(var(arg))).
#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(1).
