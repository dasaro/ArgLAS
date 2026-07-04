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
#pos(n1, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n2, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in). lab(c,out).}).
#pos(n3, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,in).}).
#pos(n4, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out). lab(c,in).}).
#pos(n5, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n6, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(b,out).}).
#pos(n7, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(c,in).}).
#pos(n8, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in). lab(c,out).}).
#pos(n9, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,in).}).
#pos(n10, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in). lab(c,in).}).
#pos(n11, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in). lab(c,out).}).
#pos(n12, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,in).}).
#pos(n13, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n14, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out). lab(c,out).}).
#pos(n15, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(b,out).}).
#pos(n16, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(c,in).}).
#pos(n17, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out). lab(c,out).}).
#pos(n18, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(a,out).}).
#pos(n19, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). lab(c,in).}).
#pos(n20, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in). lab(c,out).}).
#pos(n21, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,in).}).
#pos(n22, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). lab(c,in).}).
#pos(n23, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out). lab(c,out).}).
#pos(n24, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(b,out).}).
#pos(n25, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). lab(c,out).}).
#pos(n26, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a).}).
#pos(p27, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(n28, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n29, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,out).}).
#pos(n30, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,in).}).
#pos(n31, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n32, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(b,out).}).
#pos(n33, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(c,in).}).
#pos(n34, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in). lab(c,out).}).
#pos(n35, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,in).}).
#pos(n36, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,in).}).
#pos(n37, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,out).}).
#pos(n38, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,in).}).
#pos(n39, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n40, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,out).}).
#pos(n41, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(b,out).}).
#pos(n42, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(c,in).}).
#pos(n43, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out). lab(c,out).}).
#pos(n44, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(a,out).}).
#pos(n45, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in). lab(c,in).}).
#pos(n46, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in). lab(c,out).}).
#pos(n47, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,in).}).
#pos(n48, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). lab(c,in).}).
#pos(n49, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out). lab(c,out).}).
#pos(n50, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(b,out).}).
#pos(n51, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(c,in).}).
#pos(n52, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). lab(c,out).}).
#pos(n53, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#pos(p54, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(n55, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n56, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in). lab(c,out).}).
#pos(n57, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,in).}).
#pos(n58, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n59, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(b,out).}).
#pos(n60, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(c,in).}).
#pos(n61, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in). lab(c,out).}).
#pos(n62, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,in).}).
#pos(n63, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,in).}).
#pos(n64, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in). lab(c,out).}).
#pos(n65, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,in).}).
#pos(n66, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n67, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out). lab(c,out).}).
#pos(n68, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(b,out).}).
#pos(n69, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(c,in).}).
#pos(n70, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out). lab(c,out).}).
#pos(n71, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(a,out).}).
#pos(n72, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in). lab(c,in).}).
#pos(n73, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in). lab(c,out).}).
#pos(n74, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,in).}).
#pos(n75, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). lab(c,in).}).
#pos(n76, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out). lab(c,out).}).
#pos(n77, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(b,out).}).
#pos(n78, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(c,in).}).
#pos(n79, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). lab(c,out).}).
#pos(n80, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#pos(p81, {ok}, {bad}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(n82, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n83, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in). lab(c,out).}).
#pos(n84, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,in).}).
#pos(n85, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n86, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(b,out).}).
#pos(n87, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(c,in).}).
#pos(n88, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in). lab(c,out).}).
#pos(n89, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,in).}).
#pos(n90, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in). lab(c,in).}).
#pos(n91, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in). lab(c,out).}).
#pos(n92, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,in).}).
#pos(n93, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n94, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out). lab(c,out).}).
#pos(n95, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(b,out).}).
#pos(n96, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(c,in).}).
#pos(n97, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out). lab(c,out).}).
#pos(n98, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(a,out).}).
#pos(n99, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in). lab(c,in).}).
#pos(n100, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in). lab(c,out).}).
#pos(n101, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,in).}).
#pos(n102, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). lab(c,in).}).
#pos(n103, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out). lab(c,out).}).
#pos(n104, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(b,out).}).
#pos(n105, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(c,in).}).
#pos(n106, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b). lab(c,out).}).
#pos(n107, {bad}, {ok}, {arg(a). arg(b). arg(c). att(a,b).}).
#pos(p108, {ok}, {bad}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in).}).
#pos(n109, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in). lab(c,in).}).
#pos(n110, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in). lab(c,out).}).
#pos(n111, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,in).}).
#pos(n112, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out). lab(c,in).}).
#pos(n113, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out). lab(c,out).}).
#pos(n114, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(b,out).}).
#pos(n115, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,in).}).
#pos(n116, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,in). lab(c,out).}).
#pos(n117, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in). lab(c,in).}).
#pos(n118, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in). lab(c,out).}).
#pos(n119, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,in).}).
#pos(n120, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out). lab(c,in).}).
#pos(n121, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out). lab(c,out).}).
#pos(n122, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(b,out).}).
#pos(n123, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(c,in).}).
#pos(n124, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out). lab(c,out).}).
#pos(n125, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(a,out).}).
#pos(n126, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in). lab(c,in).}).
#pos(n127, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in). lab(c,out).}).
#pos(n128, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,in).}).
#pos(n129, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out). lab(c,in).}).
#pos(n130, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out). lab(c,out).}).
#pos(n131, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(b,out).}).
#pos(n132, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(c,in).}).
#pos(n133, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). lab(c,out).}).
#pos(n134, {bad}, {ok}, {arg(a). arg(b). arg(c). att(b,c). att(c,b).}).
