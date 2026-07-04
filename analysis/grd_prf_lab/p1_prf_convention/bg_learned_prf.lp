defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
0{ in(X) }1 :- arg(X).
0{ out(X) }1 :- arg(X).
% PRF eval convention (route P1): the SAME subset-maximal-in enumeration that
% ASPARTIX/preferred.lp uses on the oracle side, applied as a FIXED block on the
% learned side. Requires clingo args: --heuristic=Domain --enum=domRec
#heuristic in(X) : arg(X). [1, true]
