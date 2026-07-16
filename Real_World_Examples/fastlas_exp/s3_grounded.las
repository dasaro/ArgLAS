% --- structural features over the observed labelling lab/2 ---
defeat(X, Y) :- att(X, Y).
defeated(X) :- lab(Y, in), defeat(Y, X).
not_supported(X) :- att(Y, X), not lab(Y, out).
supported(X) :- arg(X), not not_supported(X).

% --- legality: the labelling is bad if any label is not justified, OR a decidable
%     argument was left undecided (grounded completeness). ---
undec(X) :- arg(X), not lab(X, in), not lab(X, out).
bad :- lab(X, in),  not just_in(X).
bad :- lab(X, out), not just_out(X).
bad :- undec(X), just_in(X).
bad :- undec(X), just_out(X).
ok :- not bad.


#modeh(just_in(var(arg))).
#modeh(just_out(var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(att(var(arg), var(arg))).
#modeb(not supported(var(arg))).
#modeb(not defeated(var(arg))).


#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(2).

#pos(p0, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(c,in).}).
#pos(p1, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(p2, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(p3, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(p4, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in).}).
#pos(n5, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(c,in).}).
#pos(n6, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(c,in).}).
#pos(n7, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). lab(c,in).}).
#pos(n8, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). lab(c,in).}).
#pos(n9, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(c,out).}).
#pos(n10, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a).}).
#pos(n11, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n12, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). lab(c,in).}).
#pos(n13, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n14, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(c,in).}).
#pos(n15, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n16, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out).}).
#pos(n17, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n18, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). lab(c,in).}).
#pos(n19, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n20, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(c,in).}).
#pos(n21, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n22, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out).}).
#pos(n23, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n24, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). lab(c,in).}).
#pos(n25, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n26, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(c,in).}).
#pos(n27, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n28, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out).}).
#pos(n29, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out).}).
#pos(n30, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b).}).
#pos(n31, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in).}).
#pos(n32, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out).}).
#pos(n33, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,in).}).
#pos(n34, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,out).}).
