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
#modeb(att(var(arg), var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).
#modeb(not supported(var(arg))).
#modeb(not defeated(var(arg))).

#maxv(2).

#bias("penalty(1, head).").
#bias("penalty(1, body(X)) :- in_body(X).").

#pos(e0, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). in(b). in(c).}).
#pos(e1, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). in(b). out(c).}).
#pos(e2, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). in(b).}).
#pos(e3, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). out(b). in(c).}).
#pos(e4, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). out(b). out(c).}).
#pos(e5, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). out(b).}).
#pos(e6, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). in(c).}).
#pos(e7, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a). out(c).}).
#pos(e8, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(a).}).
#pos(e9, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). in(b). in(c).}).
#pos(e10, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). in(b). out(c).}).
#pos(e11, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). in(b).}).
#pos(e12, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). out(b). in(c).}).
#pos(e13, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). out(b). out(c).}).
#pos(e14, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). out(b).}).
#pos(e15, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). in(c).}).
#pos(e16, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a). out(c).}).
#pos(e17, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(a).}).
#pos(e18, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(b). in(c).}).
#pos(e19, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(b). out(c).}).
#pos(e20, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(b).}).
#pos(e21, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(b). in(c).}).
#pos(e22, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(b). out(c).}).
#pos(e23, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(b).}).
#pos(e24, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). in(c).}).
#pos(e25, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). out(c).}).
#pos(e26, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a).}).
#pos(e27, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(b). in(c).}).
#pos(e28, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(b). out(c).}).
#pos(e29, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(b).}).
#pos(e30, {}, {false}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). in(c).}).
#pos(e31, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b). out(c).}).
#pos(e32, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(b).}).
#pos(e33, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). in(c).}).
#pos(e34, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a). out(c).}).
#pos(e35, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(a).}).
#pos(e36, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). in(b). in(c).}).
#pos(e37, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). in(b). out(c).}).
#pos(e38, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). in(b).}).
#pos(e39, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(b). in(c).}).
#pos(e40, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(b). out(c).}).
#pos(e41, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(b).}).
#pos(e42, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). in(c).}).
#pos(e43, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a). out(c).}).
#pos(e44, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(a).}).
#pos(e45, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(b). in(c).}).
#pos(e46, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(b). out(c).}).
#pos(e47, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(b).}).
#pos(e48, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(b). in(c).}).
#pos(e49, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(b). out(c).}).
#pos(e50, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(b).}).
#pos(e51, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). in(c).}).
#pos(e52, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b). out(c).}).
#pos(e53, {false}, {}, {arg(a). arg(b). arg(c). att(b,a). att(c,b).}).
#pos(e54, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(b). in(c).}).
#pos(e55, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(b). out(c).}).
#pos(e56, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(b).}).
#pos(e57, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). in(c).}).
#pos(e58, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b). out(c).}).
#pos(e59, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(b).}).
#pos(e60, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). in(c).}).
#pos(e61, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a). out(c).}).
#pos(e62, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(a).}).
#pos(e63, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). in(b). in(c).}).
#pos(e64, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). in(b). out(c).}).
#pos(e65, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). in(b).}).
#pos(e66, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(b). in(c).}).
#pos(e67, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(b). out(c).}).
#pos(e68, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(b).}).
#pos(e69, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). in(c).}).
#pos(e70, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a). out(c).}).
#pos(e71, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(a).}).
#pos(e72, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(b). in(c).}).
#pos(e73, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(b). out(c).}).
#pos(e74, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(b).}).
#pos(e75, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(b). in(c).}).
#pos(e76, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(b). out(c).}).
#pos(e77, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(b).}).
#pos(e78, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). in(c).}).
#pos(e79, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b). out(c).}).
#pos(e80, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). att(b,a). att(c,b).}).
#pos(e81, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(b). in(c).}).
#pos(e82, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(b). out(c).}).
#pos(e83, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(b).}).
#pos(e84, {}, {false}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). in(c).}).
#pos(e85, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b). out(c).}).
#pos(e86, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(b).}).
#pos(e87, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). in(c).}).
#pos(e88, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a). out(c).}).
#pos(e89, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(a).}).
#pos(e90, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). in(b). in(c).}).
#pos(e91, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). in(b). out(c).}).
#pos(e92, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). in(b).}).
#pos(e93, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(b). in(c).}).
#pos(e94, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(b). out(c).}).
#pos(e95, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(b).}).
#pos(e96, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). in(c).}).
#pos(e97, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a). out(c).}).
#pos(e98, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(a).}).
#pos(e99, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(b). in(c).}).
#pos(e100, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(b). out(c).}).
#pos(e101, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(b).}).
#pos(e102, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(b). in(c).}).
#pos(e103, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(b). out(c).}).
#pos(e104, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(b).}).
#pos(e105, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). in(c).}).
#pos(e106, {false}, {}, {arg(a). arg(b). arg(c). att(a,b). out(c).}).
#pos(e107, {false}, {}, {arg(a). arg(b). arg(c). att(a,b).}).
#pos(e108, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(b). in(c).}).
#pos(e109, {}, {false}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(b). out(c).}).
#pos(e110, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(b).}).
#pos(e111, {}, {false}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(b). in(c).}).
#pos(e112, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(b). out(c).}).
#pos(e113, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(b).}).
#pos(e114, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). in(c).}).
#pos(e115, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a). out(c).}).
#pos(e116, {}, {false}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(a).}).
#pos(e117, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). in(b). in(c).}).
#pos(e118, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). in(b). out(c).}).
#pos(e119, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). in(b).}).
#pos(e120, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). out(b). in(c).}).
#pos(e121, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). out(b). out(c).}).
#pos(e122, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). out(b).}).
#pos(e123, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). in(c).}).
#pos(e124, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a). out(c).}).
#pos(e125, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(a).}).
#pos(e126, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(b). in(c).}).
#pos(e127, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(b). out(c).}).
#pos(e128, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(b).}).
#pos(e129, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(b). in(c).}).
#pos(e130, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(b). out(c).}).
#pos(e131, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(b).}).
#pos(e132, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). in(c).}).
#pos(e133, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b). out(c).}).
#pos(e134, {false}, {}, {arg(a). arg(b). arg(c). att(b,c). att(c,b).}).
