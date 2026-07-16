% G1 no-choice background: identical to background_knowledge.lp MINUS the
% two choice rules 0{in(X)}1 / 0{out(X)}1. The learned theory must DERIVE
% in/out; nothing can be "guessed".
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
