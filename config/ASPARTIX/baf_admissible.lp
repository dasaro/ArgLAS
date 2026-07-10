%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% BAF admissible extensions (support-extended defeat)
% Guess-style oracle used to LABEL BAF pools (Experiment F1).
% Formulation machine-verified against the learned encoding:
%   analysis/zlatina_theorems/check_baf.py (3,256 BAFs, 0 counterexamples)
%   analysis/zlatina_theorems/anthem/baf2_adm_* (anthem+Vampire proof)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Support closure and support-extended defeat (thesis §4.3)
support(X,Z) :- support(X,Y), support(Y,Z).
defeat(X,Y) :- att(X,Y).
defeat(X,Y) :- att(Z,Y), support(X,Z).
defeat(X,Y) :- att(X,Z), support(Z,Y).

%% Guess a set S \subseteq A
in(X) :- not out(X), arg(X).
out(X) :- not in(X), arg(X).

%% S has to be conflict-free w.r.t. defeat
:- in(X), in(Y), defeat(X,Y).

%% The argument x is defeated by the set S
defeated(X) :- in(Y), defeat(Y,X).

%% The argument x is not defended by S
not_defended(X) :- defeat(Y,X), not defeated(Y).

%% All arguments x \in S need to be defended by S
:- in(X), not_defended(X).

#show in/1.
%#show out/1.
