in(X) :- not out(X), arg(X).
out(X) :- not in(X), arg(X).
defeated(X) :- att(Y,X), in(Y).
not_defended(X) :- att(Y,X), not defeated(Y).
:- in(X), in(Y), att(X,Y).
:- in(X), not_defended(X).
