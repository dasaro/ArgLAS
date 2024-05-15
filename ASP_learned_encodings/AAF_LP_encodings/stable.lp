defeated(X) :- in(Y), att(Y,X).
out(X) :- defeated(X).
in(X) :- arg(X), not out(X).
#show in/1.