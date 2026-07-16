attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y).
legal :- not violated.

#modeh(violated).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(undec(var(arg))).
#modeb(defended(var(arg))).
#modeb(attacked_by_in(var(arg))).
#modeb(attacked(var(arg))).
#modeb(att(var(arg), var(arg))).
#modeb(not defended(var(arg))).
#modeb(not attacked_by_in(var(arg))).
#modeb(not attacked(var(arg))).
#modeb(not in(var(arg))).
#modeb(not out(var(arg))).
#modeb(not undec(var(arg))).

#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(1).

#pos(p0, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). in(c).}).
#neg(n0, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). undec(b). in(c).}).
#neg(n1, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). undec(b). in(c).}).
#neg(n2, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). in(b). in(c).}).
#neg(n3, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). out(b). in(c).}).
#neg(n4, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). out(c).}).
#neg(n5, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). undec(c).}).
#pos(p1, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). in(c).}).
#neg(n6, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(b). in(c).}).
#neg(n7, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). undec(a). out(b). in(c).}).
#neg(n8, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(b). in(c).}).
#neg(n9, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). undec(b). in(c).}).
#neg(n10, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). out(c).}).
#neg(n11, {legal}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). undec(c).}).
#pos(p2, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). in(c).}).
#neg(n12, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(b). in(c).}).
#neg(n13, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). undec(a). out(b). in(c).}).
#neg(n14, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(b). in(c).}).
#neg(n15, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). undec(b). in(c).}).
#neg(n16, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). out(c).}).
#neg(n17, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). undec(c).}).
#pos(p3, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). in(c).}).
#neg(n18, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(b). in(c).}).
#neg(n19, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). undec(a). out(b). in(c).}).
#neg(n20, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(b). in(c).}).
#neg(n21, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). undec(b). in(c).}).
#neg(n22, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). out(c).}).
#neg(n23, {legal}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). undec(c).}).
#pos(p4, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). undec(c).}).
#neg(n24, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). undec(b). undec(c).}).
#neg(n25, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). undec(a). undec(b). undec(c).}).
#neg(n26, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(b). undec(c).}).
#neg(n27, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(b). undec(c).}).
#neg(n28, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). in(c).}).
#neg(n29, {legal}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). out(c).}).
