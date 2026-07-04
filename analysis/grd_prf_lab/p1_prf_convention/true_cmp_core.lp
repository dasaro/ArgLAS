% TRUE complete core in the pipeline's choice representation.
:- in(X), in(Y), att(X, Y).
:- in(X), not_defended(X).
:- out(X), not not_defended(X).
