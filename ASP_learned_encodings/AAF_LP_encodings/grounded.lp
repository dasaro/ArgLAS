defeated(X) :- in(Y), att(Y,X). 
not_defended(X) :- att(Y,X), not defeated(Y).
in(X) :- arg(X), not not_defended(X).
out(X) :- not_defended(X).
#heuristic in(X). [1@1, false]
#show in/1.
