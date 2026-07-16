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

#pos(g_4_78, {}, {in(1), in(2), in(3), in(4), out(1), out(2), out(3), out(4)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(2,1). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,1). att(4,2).}).
#pos(c_4_78_1, {in(2), out(1), out(3), out(4)}, {in(1), in(3), in(4), out(2)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(2,1). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,1). att(4,2).}).
#brave_ordering(g_4_78, c_4_78_1, <).
#pos(c_4_78_2, {in(3), out(1), out(2), out(4)}, {in(1), in(2), in(4), out(3)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(2,1). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,1). att(4,2).}).
#brave_ordering(g_4_78, c_4_78_2, <).
#pos(g_4_81, {in(1), in(3), out(2), out(4)}, {in(2), in(4), out(1), out(3)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,4). att(2,3). att(2,4). att(3,2). att(3,4). att(4,2). att(4,3).}).
#pos(g_4_100, {}, {in(1), in(2), in(3), in(4), out(1), out(2), out(3), out(4)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(1,4). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,3).}).
#pos(c_4_100_1, {in(1), out(2), out(3), out(4)}, {in(2), in(3), in(4), out(1)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(1,4). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,3).}).
#brave_ordering(g_4_100, c_4_100_1, <).
#pos(c_4_100_2, {in(3), out(1), out(2), out(4)}, {in(1), in(2), in(4), out(3)}, {arg(1). arg(2). arg(3). arg(4). att(1,2). att(1,3). att(1,4). att(2,3). att(2,4). att(3,1). att(3,2). att(3,4). att(4,3).}).
#brave_ordering(g_4_100, c_4_100_2, <).
#pos(g_5_15, {in(1), in(2), out(3), out(4), out(5)}, {in(3), in(4), in(5), out(1), out(2)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(1,4). att(1,5). att(2,3). att(2,4). att(2,5). att(3,4). att(3,5). att(4,2). att(4,3). att(4,5). att(5,2). att(5,3). att(5,4).}).
#pos(g_5_17, {}, {in(1), in(2), in(3), in(4), in(5), out(1), out(2), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(1,4). att(1,5). att(2,4). att(3,2). att(3,5). att(4,1). att(4,2). att(4,3). att(4,5). att(5,1). att(5,2). att(5,3). att(5,4).}).
#pos(c_5_17_1, {in(1), in(2), out(3), out(4), out(5)}, {in(3), in(4), in(5), out(1), out(2)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(1,4). att(1,5). att(2,4). att(3,2). att(3,5). att(4,1). att(4,2). att(4,3). att(4,5). att(5,1). att(5,2). att(5,3). att(5,4).}).
#brave_ordering(g_5_17, c_5_17_1, <).
#pos(c_5_17_2, {in(4), out(1), out(2), out(3), out(5)}, {in(1), in(2), in(3), in(5), out(4)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(1,4). att(1,5). att(2,4). att(3,2). att(3,5). att(4,1). att(4,2). att(4,3). att(4,5). att(5,1). att(5,2). att(5,3). att(5,4).}).
#brave_ordering(g_5_17, c_5_17_2, <).
#pos(c_5_17_3, {in(5), out(1), out(2), out(3), out(4)}, {in(1), in(2), in(3), in(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(1,4). att(1,5). att(2,4). att(3,2). att(3,5). att(4,1). att(4,2). att(4,3). att(4,5). att(5,1). att(5,2). att(5,3). att(5,4).}).
#brave_ordering(g_5_17, c_5_17_3, <).
#pos(g_5_18, {in(5)}, {in(1), in(2), in(3), in(4), out(1), out(2), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(2,1). att(2,4). att(3,1). att(3,2). att(4,2).}).
#pos(c_5_18_1, {in(1), in(4), in(5), out(2), out(3)}, {in(2), in(3), out(1), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(2,1). att(2,4). att(3,1). att(3,2). att(4,2).}).
#brave_ordering(g_5_18, c_5_18_1, <).
#pos(c_5_18_2, {in(3), in(4), in(5), out(1), out(2)}, {in(1), in(2), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(2,1). att(2,4). att(3,1). att(3,2). att(4,2).}).
#brave_ordering(g_5_18, c_5_18_2, <).
#pos(c_5_18_3, {in(4), in(5), out(2)}, {in(1), in(2), in(3), out(1), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,3). att(2,1). att(2,4). att(3,1). att(3,2). att(4,2).}).
#brave_ordering(g_5_18, c_5_18_3, <).
#pos(g_5_35, {}, {in(1), in(2), in(3), in(4), in(5), out(1), out(2), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,2). att(1,5). att(2,3). att(2,4). att(3,1). att(3,4). att(4,1). att(5,4).}).
#pos(g_5_78, {}, {in(1), in(2), in(3), in(4), in(5), out(1), out(2), out(3), out(4), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,4). att(2,1). att(2,3). att(3,1). att(3,5). att(4,3). att(4,5). att(5,2). att(5,3).}).
#pos(c_5_78_1, {in(1), in(5), out(2), out(3), out(4)}, {in(2), in(3), in(4), out(1), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,4). att(2,1). att(2,3). att(3,1). att(3,5). att(4,3). att(4,5). att(5,2). att(5,3).}).
#brave_ordering(g_5_78, c_5_78_1, <).
#pos(c_5_78_2, {in(2), in(4), out(1), out(3), out(5)}, {in(1), in(3), in(5), out(2), out(4)}, {arg(1). arg(2). arg(3). arg(4). arg(5). att(1,4). att(2,1). att(2,3). att(3,1). att(3,5). att(4,3). att(4,5). att(5,2). att(5,3).}).
#brave_ordering(g_5_78, c_5_78_2, <).
#pos(g_6_14, {}, {in(1), in(2), in(3), in(4), in(5), in(6), out(1), out(2), out(3), out(4), out(5), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). att(1,2). att(1,5). att(1,6). att(2,3). att(2,4). att(2,6). att(3,1). att(3,2). att(3,4). att(3,5). att(4,5). att(5,3). att(5,4). att(6,2). att(6,3). att(6,5).}).
#pos(g_6_91, {}, {in(1), in(2), in(3), in(4), in(5), in(6), out(1), out(2), out(3), out(4), out(5), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). att(1,3). att(1,6). att(2,1). att(2,4). att(2,5). att(2,6). att(3,1). att(3,2). att(3,4). att(3,6). att(4,1). att(4,3). att(4,5). att(4,6). att(5,2). att(5,3). att(5,6). att(6,2). att(6,4).}).
#pos(g_6_92, {in(4), in(5), in(6), out(1), out(2), out(3)}, {in(1), in(2), in(3), out(4), out(5), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). att(1,2). att(2,1). att(2,6). att(3,6). att(4,1). att(5,2). att(5,3). att(6,2).}).
#pos(g_7_15, {}, {in(1), in(2), in(3), in(4), in(5), in(6), in(7), out(1), out(2), out(3), out(4), out(5), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(2,1). att(2,4). att(2,7). att(3,1). att(3,4). att(3,5). att(4,7). att(5,1). att(5,2). att(5,6). att(5,7). att(6,2). att(6,3). att(6,4). att(6,5). att(7,2). att(7,3). att(7,6).}).
#pos(g_7_28, {in(6), in(7), out(3), out(4)}, {in(1), in(2), in(3), in(4), in(5), out(1), out(2), out(5), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,5). att(2,4). att(2,5). att(3,1). att(4,7). att(5,1). att(5,2). att(6,3). att(6,4). att(7,3).}).
#pos(c_7_28_1, {in(1), in(6), in(7), out(2), out(3), out(4), out(5)}, {in(2), in(3), in(4), in(5), out(1), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,5). att(2,4). att(2,5). att(3,1). att(4,7). att(5,1). att(5,2). att(6,3). att(6,4). att(7,3).}).
#brave_ordering(g_7_28, c_7_28_1, <).
#pos(c_7_28_2, {in(5), in(6), in(7), out(1), out(2), out(3), out(4)}, {in(1), in(2), in(3), in(4), out(5), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,5). att(2,4). att(2,5). att(3,1). att(4,7). att(5,1). att(5,2). att(6,3). att(6,4). att(7,3).}).
#brave_ordering(g_7_28, c_7_28_2, <).
#pos(g_7_73, {in(1), in(2), in(7), out(3), out(4), out(5), out(6)}, {in(3), in(4), in(5), in(6), out(1), out(2), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,3). att(1,4). att(1,5). att(1,6). att(2,3). att(2,4). att(2,6). att(3,1). att(3,2). att(3,4). att(3,6). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(6,2). att(6,4). att(6,5). att(7,3). att(7,4). att(7,5).}).
#pos(g_7_74, {in(6)}, {in(1), in(2), in(3), in(4), in(5), in(7), out(1), out(2), out(3), out(4), out(5), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,3). att(1,5). att(3,4). att(3,7). att(5,1). att(5,2). att(5,4). att(5,7). att(7,4). att(7,5).}).
#pos(c_7_74_1, {in(1), in(2), in(6), in(7), out(3), out(4), out(5)}, {in(3), in(4), in(5), out(1), out(2), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,3). att(1,5). att(3,4). att(3,7). att(5,1). att(5,2). att(5,4). att(5,7). att(7,4). att(7,5).}).
#brave_ordering(g_7_74, c_7_74_1, <).
#pos(c_7_74_2, {in(3), in(5), in(6), out(1), out(2), out(4), out(7)}, {in(1), in(2), in(4), in(7), out(3), out(5), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,3). att(1,5). att(3,4). att(3,7). att(5,1). att(5,2). att(5,4). att(5,7). att(7,4). att(7,5).}).
#brave_ordering(g_7_74, c_7_74_2, <).
#pos(g_7_89, {in(6), out(1), out(2), out(3), out(4), out(5), out(7)}, {in(1), in(2), in(3), in(4), in(5), in(7), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,4). att(2,3). att(2,4). att(2,5). att(2,7). att(3,2). att(3,4). att(4,1). att(4,2). att(4,3). att(4,5). att(5,4). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(7,2). att(7,4).}).
#pos(g_7_92, {}, {in(1), in(2), in(3), in(4), in(5), in(6), in(7), out(1), out(2), out(3), out(4), out(5), out(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(2,3). att(2,4). att(2,5). att(2,6). att(2,7). att(3,1). att(3,2). att(3,4). att(3,6). att(3,7). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(5,6). att(5,7). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6).}).
#pos(c_7_92_1, {in(5), out(1), out(2), out(3), out(4), out(6), out(7)}, {in(1), in(2), in(3), in(4), in(6), in(7), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(2,3). att(2,4). att(2,5). att(2,6). att(2,7). att(3,1). att(3,2). att(3,4). att(3,6). att(3,7). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(5,6). att(5,7). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6).}).
#brave_ordering(g_7_92, c_7_92_1, <).
#pos(c_7_92_2, {in(6), out(1), out(2), out(3), out(4), out(5), out(7)}, {in(1), in(2), in(3), in(4), in(5), in(7), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(2,3). att(2,4). att(2,5). att(2,6). att(2,7). att(3,1). att(3,2). att(3,4). att(3,6). att(3,7). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(5,6). att(5,7). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6).}).
#brave_ordering(g_7_92, c_7_92_2, <).
#pos(c_7_92_3, {in(7), out(1), out(2), out(3), out(4), out(5), out(6)}, {in(1), in(2), in(3), in(4), in(5), in(6), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(2,3). att(2,4). att(2,5). att(2,6). att(2,7). att(3,1). att(3,2). att(3,4). att(3,6). att(3,7). att(4,1). att(4,2). att(4,3). att(4,5). att(4,6). att(5,1). att(5,2). att(5,3). att(5,4). att(5,6). att(5,7). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6).}).
#brave_ordering(g_7_92, c_7_92_3, <).
#pos(g_8_66, {}, {in(1), in(2), in(3), in(4), in(5), in(6), in(7), in(8), out(1), out(2), out(3), out(4), out(5), out(6), out(7), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,5). att(1,7). att(1,8). att(2,3). att(2,6). att(2,7). att(2,8). att(3,1). att(3,2). att(3,4). att(3,5). att(3,7). att(3,8). att(4,1). att(4,2). att(4,3). att(4,6). att(4,7). att(4,8). att(5,1). att(5,2). att(5,3). att(5,4). att(5,7). att(5,8). att(6,1). att(6,2). att(6,3). att(6,5). att(6,7). att(6,8). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6). att(7,8). att(8,1). att(8,2). att(8,3). att(8,4). att(8,5). att(8,6).}).
#pos(c_8_66_1, {in(7), out(1), out(2), out(3), out(4), out(5), out(6), out(8)}, {in(1), in(2), in(3), in(4), in(5), in(6), in(8), out(7)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,5). att(1,7). att(1,8). att(2,3). att(2,6). att(2,7). att(2,8). att(3,1). att(3,2). att(3,4). att(3,5). att(3,7). att(3,8). att(4,1). att(4,2). att(4,3). att(4,6). att(4,7). att(4,8). att(5,1). att(5,2). att(5,3). att(5,4). att(5,7). att(5,8). att(6,1). att(6,2). att(6,3). att(6,5). att(6,7). att(6,8). att(7,1). att(7,2). att(7,3). att(7,4). att(7,5). att(7,6). att(7,8). att(8,1). att(8,2). att(8,3). att(8,4). att(8,5). att(8,6).}).
#brave_ordering(g_8_66, c_8_66_1, <).
#pos(g_8_69, {}, {in(1), in(2), in(3), in(4), in(5), in(6), in(7), in(8), out(1), out(2), out(3), out(4), out(5), out(6), out(7), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(1,8). att(2,1). att(2,3). att(2,5). att(2,8). att(3,1). att(3,2). att(3,4). att(3,5). att(3,7). att(3,8). att(4,3). att(4,7). att(4,8). att(5,2). att(5,3). att(5,7). att(5,8). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(6,8). att(7,1). att(7,2). att(7,4). att(7,6). att(7,8). att(8,1). att(8,4). att(8,5). att(8,6). att(8,7).}).
#pos(c_8_69_1, {in(1), in(5), out(2), out(3), out(4), out(6), out(7), out(8)}, {in(2), in(3), in(4), in(6), in(7), in(8), out(1), out(5)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(1,8). att(2,1). att(2,3). att(2,5). att(2,8). att(3,1). att(3,2). att(3,4). att(3,5). att(3,7). att(3,8). att(4,3). att(4,7). att(4,8). att(5,2). att(5,3). att(5,7). att(5,8). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(6,8). att(7,1). att(7,2). att(7,4). att(7,6). att(7,8). att(8,1). att(8,4). att(8,5). att(8,6). att(8,7).}).
#brave_ordering(g_8_69, c_8_69_1, <).
#pos(c_8_69_2, {in(6), out(1), out(2), out(3), out(4), out(5), out(7), out(8)}, {in(1), in(2), in(3), in(4), in(5), in(7), in(8), out(6)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,4). att(1,6). att(1,7). att(1,8). att(2,1). att(2,3). att(2,5). att(2,8). att(3,1). att(3,2). att(3,4). att(3,5). att(3,7). att(3,8). att(4,3). att(4,7). att(4,8). att(5,2). att(5,3). att(5,7). att(5,8). att(6,1). att(6,2). att(6,3). att(6,4). att(6,5). att(6,7). att(6,8). att(7,1). att(7,2). att(7,4). att(7,6). att(7,8). att(8,1). att(8,4). att(8,5). att(8,6). att(8,7).}).
#brave_ordering(g_8_69, c_8_69_2, <).
#pos(g_8_100, {in(3), in(4), in(8), out(1), out(2), out(5), out(6), out(7)}, {in(1), in(2), in(5), in(6), in(7), out(3), out(4), out(8)}, {arg(1). arg(2). arg(3). arg(4). arg(5). arg(6). arg(7). arg(8). att(1,2). att(1,3). att(1,5). att(1,8). att(2,3). att(3,1). att(3,6). att(4,1). att(4,2). att(4,5). att(4,6). att(5,1). att(5,6). att(6,3). att(6,5). att(6,8). att(7,5). att(8,5). att(8,7).}).
