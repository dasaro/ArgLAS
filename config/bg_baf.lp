% BAF learning background B_BAF (Experiment F1) — thesis §4.3 / §4.5 form,
% machine-verified in analysis/zlatina_theorems/check_baf.py and check_unified.py.
% Relative to background_knowledge.lp (B_AAF): adds the support closure and the
% two support-extended defeat rules; supported/1 is redefined the thesis way
% ("supported by an accepted argument") — note this DIFFERS from the AAF
% supported/1 ("all attackers out", used by the grounded target), which is why
% GRD is out of scope for BAF cells.
support(X,Z) :- support(X,Y), support(Y,Z).
supported(X) :- support(Y,X), in(Y).
defeat(X,Y) :- att(X,Y).
defeat(X,Y) :- att(Z,Y), support(X,Z).
defeat(X,Y) :- att(X,Z), support(Z,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
:- arg(X), in(X), out(X).
0{ in(X) }1 :- arg(X).
0{ out(X) }1 :- arg(X).
