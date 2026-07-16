%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  Encoding for preferred extensions
%  
%  Uses clingo heuristics to compute preferred extensions.
%
%  Clingo call:
%
%  > ./clingo --heuristic=Domain --enum=domRec --out-hide af_instance.dl preferred.lp 0
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


%%% We first define complete labellings


%% Guess a label for each argument
in(X) | out(X) | undec(X) :- arg(X).

%% If all attackers are out the argument is in
in(X):-arg(X), out(Y):att(Y,X).

%% An argument attacked by an in argument is out
out(X):-in(Y), att(Y,X).

%% If an argument is in then all of its attackers must be out
:- in(X),not out(Y), att(Y,X).

%% If an argument is out then one of its attackers must be in
:- out(X),not in (Y): att(Y,X).

%% Each argument has exactly one label
:- in(X),out(X).
:- undec(X),out(X).
:- undec(X),in(X).

%%% We now apply heuristics to get the complete labeling with subset-maximal in(.) set (and  thus also maximal out())

#heuristic in(X):arg(X). [1,true]

#show in/1.