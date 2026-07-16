:- arg(X), in(X), out(X).

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
#neg(n0, {out(c)}, {in(a), out(a), in(b), out(b), in(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). supported(c). not_defended(a). not_defended(b).}).
#neg(n1, {}, {in(a), out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). supported(c). not_defended(a). not_defended(b).}).
#neg(n2, {out(a), out(b), in(c)}, {in(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n3, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n4, {in(a), in(b), in(c)}, {out(a), out(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(c). defeated(a). defeated(b). not_defended(b).}).
#neg(n5, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(c). defeated(b). not_defended(b).}).
#neg(n6, {in(a), out(b), out(c)}, {out(a), in(b), in(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(a). supported(b). supported(c). not_defended(a). not_defended(b).}).
#neg(n7, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). supported(a). supported(c). not_defended(a). not_defended(b).}).
#neg(n8, {out(a), out(b), in(c)}, {in(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n9, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n10, {in(a), in(b), in(c)}, {out(a), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(c). defeated(a). defeated(b). not_defended(b).}).
#neg(n11, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(c). defeated(b). not_defended(b).}).
#neg(n12, {in(a), out(b), out(c)}, {out(a), in(b), in(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n13, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n14, {out(a), out(b), in(c)}, {in(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(b). supported(c). not_defended(b).}).
#neg(n15, {out(b), in(c)}, {in(a), out(a), in(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). not_defended(b).}).
#neg(n16, {in(a), in(b), in(c)}, {out(a), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n17, {in(a), in(c)}, {out(a), in(b), out(b), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n18, {in(a), out(b), out(c)}, {out(a), in(b), in(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n19, {in(a), out(b)}, {out(a), in(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(a,b). supported(a). supported(c). defeated(b). not_defended(b).}).
#neg(n20, {out(a)}, {in(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). supported(a). not_defended(b). not_defended(c).}).
#neg(n21, {}, {in(a), out(a), in(b), out(b), in(c), out(c)}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). supported(a). not_defended(b). not_defended(c).}).
