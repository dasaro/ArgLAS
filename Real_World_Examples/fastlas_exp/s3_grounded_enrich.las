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
#modeb(fp_in(var(arg))).
#modeb(fp_out(var(arg))).


#bias("penalty(1, head) :- in_head(X).").
#bias("penalty(1, body(X)) :- in_body(X).").
#maxv(2).

#pos(p0, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(c,in). fp_in(c).}).
#pos(n1, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in). lab(c,in). fp_in(c).}).
#pos(n2, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in). lab(c,out). fp_in(c).}).
#pos(n3, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in). fp_in(c).}).
#pos(n4, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out). lab(c,in). fp_in(c).}).
#pos(n5, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out). lab(c,out). fp_in(c).}).
#pos(n6, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out). fp_in(c).}).
#pos(n7, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(c,in). fp_in(c).}).
#pos(n8, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(c,out). fp_in(c).}).
#pos(n9, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). fp_in(c).}).
#pos(n10, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in). lab(c,in). fp_in(c).}).
#pos(n11, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in). lab(c,out). fp_in(c).}).
#pos(n12, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in). fp_in(c).}).
#pos(n13, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out). lab(c,in). fp_in(c).}).
#pos(n14, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out). lab(c,out). fp_in(c).}).
#pos(n15, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out). fp_in(c).}).
#pos(n16, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(c,in). fp_in(c).}).
#pos(n17, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(c,out). fp_in(c).}).
#pos(n18, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). fp_in(c).}).
#pos(n19, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). lab(c,in). fp_in(c).}).
#pos(n20, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). lab(c,out). fp_in(c).}).
#pos(n21, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). fp_in(c).}).
#pos(n22, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). lab(c,in). fp_in(c).}).
#pos(n23, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). lab(c,out). fp_in(c).}).
#pos(n24, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). fp_in(c).}).
#pos(n25, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(c,out). fp_in(c).}).
#pos(n26, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). fp_in(c).}).
#pos(p27, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n28, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n29, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n30, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n31, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n32, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n33, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n34, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n35, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n36, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n37, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n38, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n39, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n40, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n41, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n42, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n43, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n44, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n45, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n46, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n47, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n48, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n49, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n50, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n51, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n52, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n53, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). fp_in(c). fp_in(a). fp_out(b).}).
#pos(p54, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n55, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n56, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n57, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n58, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n59, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n60, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n61, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n62, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n63, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n64, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n65, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n66, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n67, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n68, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n69, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n70, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n71, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n72, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n73, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n74, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n75, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n76, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n77, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n78, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(c,in). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n79, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(c,out). fp_in(c). fp_in(a). fp_out(b).}).
#pos(n80, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). fp_in(c). fp_in(a). fp_out(b).}).
#pos(p81, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n82, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n83, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n84, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n85, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n86, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n87, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n88, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n89, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n90, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n91, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n92, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n93, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n94, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n95, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n96, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n97, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n98, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n99, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n100, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n101, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n102, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n103, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n104, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n105, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(c,in). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n106, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(c,out). fp_in(a). fp_in(c). fp_out(b).}).
#pos(n107, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). fp_in(a). fp_in(c). fp_out(b).}).
#pos(p108, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). fp_in(a).}).
#pos(n109, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in). lab(c,in). fp_in(a).}).
#pos(n110, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in). lab(c,out). fp_in(a).}).
#pos(n111, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in). fp_in(a).}).
#pos(n112, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out). lab(c,in). fp_in(a).}).
#pos(n113, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out). lab(c,out). fp_in(a).}).
#pos(n114, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out). fp_in(a).}).
#pos(n115, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,in). fp_in(a).}).
#pos(n116, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,out). fp_in(a).}).
#pos(n117, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in). lab(c,in). fp_in(a).}).
#pos(n118, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in). lab(c,out). fp_in(a).}).
#pos(n119, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in). fp_in(a).}).
#pos(n120, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out). lab(c,in). fp_in(a).}).
#pos(n121, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out). lab(c,out). fp_in(a).}).
#pos(n122, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out). fp_in(a).}).
#pos(n123, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(c,in). fp_in(a).}).
#pos(n124, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(c,out). fp_in(a).}).
#pos(n125, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). fp_in(a).}).
#pos(n126, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in). lab(c,in). fp_in(a).}).
#pos(n127, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in). lab(c,out). fp_in(a).}).
#pos(n128, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in). fp_in(a).}).
#pos(n129, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out). lab(c,in). fp_in(a).}).
#pos(n130, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out). lab(c,out). fp_in(a).}).
#pos(n131, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out). fp_in(a).}).
#pos(n132, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(c,in). fp_in(a).}).
#pos(n133, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(c,out). fp_in(a).}).
#pos(n134, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). fp_in(a).}).
