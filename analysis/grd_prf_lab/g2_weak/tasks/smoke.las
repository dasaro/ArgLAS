% Smoke test: can ILASP4 learn the grounded-selecting weak constraint from
% brave orderings on a single 3-argument AAF? a<->b, b->c.
% Complete labellings: {} (all undec), {in(a),out(b),in(c)}, {in(b),out(a),out(c)}.
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
0{ in(X) }1 :- arg(X).
0{ out(X) }1 :- arg(X).
:- in(X), not supported(X).
:- out(X), not defeated(X).
:- arg(X), not in(X), not out(X), defeated(X).
:- arg(X), not in(X), not out(X), supported(X).

#modeo(1, in(var(arg))).
#modeo(1, out(var(arg))).
#maxv(2).

#pos(l0, {}, {in(a), in(b), in(c), out(a), out(b), out(c)},
  {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(b,c).}).
#pos(l1, {in(a), out(b), in(c)}, {in(b), out(a), out(c)},
  {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(b,c).}).
#pos(l2, {in(b), out(a), out(c)}, {in(a), in(c), out(b)},
  {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(b,c).}).

#brave_ordering(o1, l0, l1, <).
#brave_ordering(o2, l0, l2, <).
