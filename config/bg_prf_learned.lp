defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
0{ in(X) }1 :- arg(X).
0{ out(X) }1 :- arg(X).
% Fixed subset-maximality convention for PRF (NOT learned; symmetric to how
% ASPARTIX preferred.lp realizes preferred = admissible + Domain/domRec enumeration).
#heuristic in(X) : arg(X). [1, true]
