out(X) :- not_defended(X).
in(X) :- arg(X), not out(X), not defeated(X).
defeated(X) :- att(Y,X), in(Y).
not_defended(X) :- att(Y,X), not defeated(Y).
