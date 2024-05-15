defeated(X) :- in(Y), att(Y,X). 
not_defended(X) :- att(Y,X), not defeated(Y).
out(V1) :- not_defended(V1).
in(V1) :- arg(V1); not defeated(V1).
#show in/1.