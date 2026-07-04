out(X) :- defeated(X).
in(X) :- arg(X), not out(X).
defeated(X) :- att(Y,X), in(Y).
not_defended(X) :- att(Y,X), not defeated(Y).
