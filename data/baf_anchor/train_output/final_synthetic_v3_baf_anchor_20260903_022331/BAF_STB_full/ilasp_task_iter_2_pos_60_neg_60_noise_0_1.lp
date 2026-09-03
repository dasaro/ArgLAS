:- not_defended(V1); not defeated(V1).
:- out(V1); not_defended(V2); not not_defended(V1).
out(V1) :- att(V1,V2); defeated(V1); not out(V2).
