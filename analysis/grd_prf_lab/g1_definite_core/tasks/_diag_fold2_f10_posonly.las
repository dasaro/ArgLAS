#pos(aaf_4_52_GRD_POS_1T, {}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(1,4). att(2,1). att(2,4). att(3,1). att(3,2). att(3,4). att(4,1). att(4,2).}).
#pos(aaf_4_67_GRD_POS_1T, {in(2)}, {}, {arg(1). arg(2). arg(3). arg(4). att(1,3). att(3,1). att(3,4). att(4,1). att(4,3).}).
#pos(aaf_5_100_GRD_POS_1T, {in(3), in(4), out(1), out(2), out(5)}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,5). att(2,3). att(3,1). att(4,2). att(4,5).}).
#pos(aaf_5_32_GRD_POS_1T, {}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,4). att(2,1). att(2,3). att(2,4). att(2,5). att(3,1). att(3,2). att(3,4). att(4,1). att(4,2). att(4,3). att(5,1). att(5,2). att(5,3). att(5,4).}).
#pos(aaf_5_6_GRD_POS_1T, {in(3), in(4), out(5)}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,5). att(2,1). att(2,5). att(3,5). att(4,5). att(5,1). att(5,2). att(5,4).}).
#pos(aaf_5_86_GRD_POS_1T, {}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,3). att(1,4). att(2,3). att(2,4). att(2,5). att(3,1). att(3,2). att(3,4). att(3,5). att(4,1). att(4,2). att(4,3). att(4,5). att(5,1). att(5,2). att(5,4).}).
#pos(aaf_6_57_GRD_POS_1T, {}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). att(1,2). att(1,3). att(1,4). att(1,5). att(1,6). att(2,1). att(2,4). att(2,5). att(2,6). att(3,1). att(3,2). att(3,5). att(3,6). att(4,1). att(5,2). att(5,3). att(5,4). att(5,6). att(6,1).}).
#pos(aaf_6_83_GRD_POS_1T, {in(1), in(2), in(3), in(4), out(5), out(6)}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). att(1,5). att(2,5). att(2,6). att(3,6). att(6,1). att(6,2).}).
#pos(aaf_7_73_GRD_POS_1T, {in(1), in(2), in(7), out(3), out(4), out(5), out(6)}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,3). att(1,4). att(1,5). att(1,6). att(2,3). att(2,4). att(2,6). att(3,1). att(3,2). att(3,4). att(3,6). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(6,2). att(6,4). att(6,5). att(7,3). att(7,4). att(7,5).}).
#pos(aaf_8_9_GRD_POS_1T, {}, {}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,3). att(1,4). att(1,7). att(2,1). att(2,4). att(2,5). att(2,7). att(3,2). att(3,4). att(4,1). att(4,2). att(4,7). att(5,3). att(5,6). att(5,7). att(5,8). att(6,2). att(6,5). att(6,7). att(7,1). att(7,2). att(7,3). att(8,3). att(8,5). att(8,6).}).
% G1 no-choice background: identical to background_knowledge.lp MINUS the
% two choice rules 0{in(X)}1 / 0{out(X)}1. The learned theory must DERIVE
% in/out; nothing can be "guessed".
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).

#modeh(in(var(arg))).
#modeh(out(var(arg))).
#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(arg(var(arg)),(positive)).
#modeb(att(var(arg), var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).
#modeb(supported(var(arg))).

#maxv(2).

