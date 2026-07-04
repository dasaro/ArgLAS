out(X) :- not_defended(X).
in(X) :- arg(X), not out(X), not defeated(X).
defeat(X,Y) :- att(Z,Y), supp(X,Z).
defeat(X,Y) :- att(X,Z), supp(Z,Y).
defeat(X,Y) :- att(X,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
