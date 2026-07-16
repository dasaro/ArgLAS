in(X) :- not out(X), arg(X).
out(X) :- not in(X), arg(X).
supp(X,Y) :- support(X,Y).
supp(X,Z) :- supp(X,Y), support(Y,Z).
defeat(X,Y) :- att(Z,Y), supp(X,Z).
defeat(X,Y) :- att(X,Z), supp(Z,Y).
defeat(X,Y) :- att(X,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
:- in(X), in(Y), defeat(X,Y).
:- in(X), not_defended(X).
