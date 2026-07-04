defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
not_supported(X) :- att(Y, X), not out(Y).
supported(X) :- arg(X), not not_supported(X).
:- arg(X), in(X), out(X).

#modeh(false).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(not in(var(arg))).
#modeb(not out(var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(not supported(var(arg))).
#modeb(not defeated(var(arg))).

#maxv(2).

#bias("penalty(1, head).").
#bias("penalty(1, body(X)) :- in_body(X).").

#pos(g0, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). in(c).}).
#pos(g1, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(c).}).
#pos(g2, {}, {false}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). in(c).}).
#pos(g3, {}, {false}, {arg(a). in(a).}).
#pos(g4, {}, {false}, {arg(a). arg(b). att(a,b). in(a). out(b).}).
#pos(g5, {false}, {}, {arg(x). arg(y). att(y,x). in(x).}).
#pos(g6, {false}, {}, {arg(x). arg(y). att(y,x). in(x). in(y).}).
#pos(g7, {false}, {}, {arg(x).}).
#pos(g8, {false}, {}, {arg(x). arg(y). att(y,x). out(y).}).
#pos(g9, {false}, {}, {arg(x). out(x).}).
#pos(g10, {false}, {}, {arg(x). arg(y). att(y,x). out(x). out(y).}).
#pos(g11, {false}, {}, {arg(x). arg(y). att(y,x). in(y).}).
#pos(g12, {false}, {}, {arg(x). arg(y). att(y,x). in(x). in(y).}).
