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
