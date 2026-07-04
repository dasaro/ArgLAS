out(X) :- defeated(X).
out(X) :- arg(X), not in(X).
in(X) :- arg(X), not out(X), not not_defended(X).
defeated(X) :- att(Y,X), in(Y).
not_defended(X) :- att(Y,X), not defeated(Y).
