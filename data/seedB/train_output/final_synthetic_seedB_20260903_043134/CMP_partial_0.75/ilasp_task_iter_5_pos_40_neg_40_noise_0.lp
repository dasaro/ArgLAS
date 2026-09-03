:- out(V1); not not_defended(V1).
out(V1) :- not_defended(V1).
:- in(V1); defeated(V1).
