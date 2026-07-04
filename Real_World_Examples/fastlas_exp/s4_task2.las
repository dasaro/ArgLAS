attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y).

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

#pos(g0, {}, {violated}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). in(c).}).
#pos(b1, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). undec(b). in(c).}).
#pos(b2, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). undec(b). in(c).}).
#pos(b3, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). in(b). in(c).}).
#pos(b4, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). out(b). in(c).}).
#pos(b5, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). out(c).}).
#pos(b6, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). undec(a). undec(b). undec(c).}).
#pos(g7, {}, {violated}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). in(c).}).
#pos(b8, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(b). in(c).}).
#pos(b9, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). undec(a). out(b). in(c).}).
#pos(b10, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(b). in(c).}).
#pos(b11, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). undec(b). in(c).}).
#pos(b12, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). out(c).}).
#pos(b13, {violated}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). undec(c).}).
#pos(g14, {}, {violated}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). in(c).}).
#pos(b15, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(b). in(c).}).
#pos(b16, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). undec(a). out(b). in(c).}).
#pos(b17, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(b). in(c).}).
#pos(b18, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). undec(b). in(c).}).
#pos(b19, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). out(c).}).
#pos(b20, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). undec(c).}).
#pos(g21, {}, {violated}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). in(c).}).
#pos(b22, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(b). in(c).}).
#pos(b23, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). undec(a). out(b). in(c).}).
#pos(b24, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(b). in(c).}).
#pos(b25, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). undec(b). in(c).}).
#pos(b26, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). out(c).}).
#pos(b27, {violated}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). undec(c).}).
#pos(g28, {}, {violated}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). undec(c).}).
#pos(b29, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). undec(b). undec(c).}).
#pos(b30, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). undec(a). undec(b). undec(c).}).
#pos(b31, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(b). undec(c).}).
#pos(b32, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(b). undec(c).}).
#pos(b33, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). in(c).}).
#pos(b34, {violated}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). undec(b). out(c).}).
