#pos(aaf_4_19_P0, {in(1), in(2), out(3), out(4)}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,4). att(2,3). att(2,4). att(3,2). att(3,4). att(4,2). att(4,3).}).
#pos(aaf_4_19_P1, {in(1), in(3), out(2), out(4)}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,4). att(2,3). att(2,4). att(3,2). att(3,4). att(4,2). att(4,3).}).
#neg(aaf_4_19_N0, {in(1), out(4)}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,4). att(2,3). att(2,4). att(3,2). att(3,4). att(4,2). att(4,3).}).
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
0{ in(X) }1 :- arg(X).
0{ out(X) }1 :- arg(X).

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

