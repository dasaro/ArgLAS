% GRD learning/eval background: background_knowledge.lp WITHOUT the choice rules.
% With 0{in}1/0{out}1 the grounded task is unsatisfiable (every labelling is an answer
% set; minimality is not first-order expressible) and the unique-model eval degenerates.
defeat(X, Y) :- att(X, Y).
defeated(X) :- in(Y), defeat(Y, X).
not_defended(X) :- defeat(Y, X), not defeated(Y).
supported(X) :- arg(X), out(Y):att(Y, X).
:- arg(X), in(X), out(X).
