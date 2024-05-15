defeated(X) :- in(Y), att(Y,X). 
not_defended(X) :- att(Y,X), not defeated(Y).
out(X) :- defeated(X).
out(X) :- arg(X), not in(X).
in(X) :- arg(X), not out(X), not not_defended(X).
#show in/1.
