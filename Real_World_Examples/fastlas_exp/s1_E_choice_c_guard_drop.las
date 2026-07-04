defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
not_supported(X) :- att(Y, X), not out(Y).
supported(X) :- arg(X), not not_supported(X).
:- arg(X), in(X), out(X).
0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- false.

#modeh(in(var(arg))).
#modeh(out(var(arg))).
#modeh(false).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(att(var(arg), var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).
#modeb(supported(var(arg))).

#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(2).

#pos(p0, {in(c)}, {in(a), out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a).}).
#pos(p1, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#pos(p2, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#pos(p3, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b).}).
#pos(p4, {in(a)}, {out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,c). att(c,b).}).
#neg(n0, {}, {in(a), out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a).}).
#neg(n1, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#neg(n2, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#neg(n3, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#neg(n4, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#neg(n5, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#neg(n6, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#neg(n7, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b).}).
#neg(n8, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b).}).
#neg(n9, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b).}).
#neg(n10, {}, {in(a), out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,c). att(c,b).}).
