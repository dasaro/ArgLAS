

#modeh(in(var(arg))).
#modeh(out(var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).
#modeb(att(var(arg), var(arg))).
#modeb(in(var(arg))).
#modeb(out(var(arg))).

#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(1).

#pos(p0, {in(c)}, {in(a), out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). supported(c). not_defended(a). not_defended(b).}).
#pos(p1, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#pos(p2, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#pos(p3, {in(a), out(b), in(c)}, {out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#pos(p4, {in(a)}, {out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). supported(a). not_defended(b). not_defended(c).}).
