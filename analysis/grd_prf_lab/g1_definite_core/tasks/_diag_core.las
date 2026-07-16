#pos(aaf_4_67_GRD_POS_1T, {in(2)}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,3). att(3,1). att(3,4). att(4,1). att(4,3).}).
% G1 no-choice background: identical to background_knowledge.lp MINUS the
% two choice rules 0{in(X)}1 / 0{out(X)}1. The learned theory must DERIVE
% in/out; nothing can be "guessed".
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).

#modeh(in(var(arg))).
#modeh(out(var(arg))).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(arg(var(arg)),(positive)).
#modeb(att(var(arg), var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).
#modeb(supported(var(arg))).

#maxv(2).

