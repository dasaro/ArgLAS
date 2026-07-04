% 3-valued (Caminada) complete-labelling core over in/1, out/1.
% Vocabulary identical to background_knowledge.lp (defeat/defeated/supported).
% Answer sets (projected to in/out) = complete labellings:
%   in  <-> all attackers out ("legally in")
%   out <-> some attacker in  ("legally out")
%   unlabelled (undec) <-> no attacker in AND not all attackers out
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
#weight(1).
#maxp(1).

#pos(g_4_8, {in(1), in(3), out(2), out(4)}, {in(2), in(4), out(1), out(3)}, {arg(1). arg(2). arg(3). arg(4). att(1,4). att(2,4). att(3,2). att(3,4). att(4,3).}).
#pos(g_4_87, {in(3), in(4), out(1), out(2)}, {in(1), in(2), out(3), out(4)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(2,1). att(3,2). att(4,1).}).
#pos(g_5_13, {in(1), in(3), out(2), out(4), out(5)}, {in(2), in(4), in(5), out(1), out(3)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,4). att(1,5). att(2,1). att(2,5). att(3,2). att(3,5). att(5,1).}).
#pos(g_5_31, {in(1), in(4), in(5), out(2), out(3)}, {in(2), in(3), out(1), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(2,1). att(3,2). att(3,5). att(4,3). att(5,2). att(5,3).}).
#pos(g_5_74, {in(4), in(5), out(1), out(2), out(3)}, {in(1), in(2), in(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,3). att(2,3). att(3,1). att(3,2). att(4,1). att(5,1). att(5,2). att(5,3).}).
#pos(g_5_99, {in(1), in(3), in(5), out(2), out(4)}, {in(2), in(4), out(1), out(3), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(2,3). att(4,2). att(4,3). att(5,4).}).
#pos(g_8_33, {in(1), in(3), in(4), in(7), in(8), out(2), out(5), out(6)}, {in(2), in(5), in(6), out(1), out(3), out(4), out(7), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,5). att(1,6). att(4,2). att(6,3). att(6,7). att(7,5). att(7,6). att(8,5).}).
#pos(g_8_78, {}, {in(1), in(2), in(3), in(4), in(5), in(6), in(7), in(8), out(1), out(2), out(3), out(4), out(5), out(6), out(7), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,8). att(2,3). att(2,8). att(3,1). att(3,2). att(3,6). att(4,2). att(4,3). att(4,5). att(4,7). att(5,1). att(5,3). att(5,4). att(5,7). att(5,8). att(6,1). att(6,5). att(6,7). att(7,3). att(7,4). att(8,1). att(8,4). att(8,7).}).
#pos(g_8_92, {in(3), in(4), in(6), in(8), out(1), out(2), out(5), out(7)}, {in(1), in(2), in(5), in(7), out(3), out(4), out(6), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,4). att(2,1). att(3,2). att(3,5). att(4,7). att(5,2). att(6,1). att(6,5).}).
#pos(g_8_98, {in(2), in(4), in(6), in(7), out(1), out(3), out(5), out(8)}, {in(1), in(3), in(5), in(8), out(2), out(4), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,7). att(2,1). att(2,5). att(2,8). att(4,1). att(4,5). att(5,4). att(6,3). att(7,3). att(8,4). att(8,5). att(8,6).}).
