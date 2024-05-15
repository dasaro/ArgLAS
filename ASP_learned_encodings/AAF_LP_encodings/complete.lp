defeated(X) :- in(Y), att(Y,X). 
not_defended(X) :- att(Y,X), not defeated(Y).
out(X) :- not_defended(X).
in(X) :- arg(X), not out(X), not defeated(X).
#show in/1.
