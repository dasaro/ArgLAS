out(X) :- defeated(X).
out(X) :- arg(X), not in(X).
in(X) :- arg(X), not out(X), not not_defended(X).
supp(X,Y) :- support(X,Y).
supp(X,Z) :- supp(X,Y), support(Y,Z).
defeat(X,Y) :- att(Z,Y), supp(X,Z).
defeat(X,Y) :- att(X,Z), supp(Z,Y).
defeat(X,Y) :- att(X,Y).
defeated(X) :- in(Y), defeat(Y,X).
not_defended(X) :- defeat(Y,X), not defeated(Y).
