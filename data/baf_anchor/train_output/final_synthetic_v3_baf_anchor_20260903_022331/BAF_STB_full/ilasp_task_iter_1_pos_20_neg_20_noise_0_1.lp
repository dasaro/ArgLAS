:- not_defended(V1); not defeated(V1).
out(V1) :- att(V2,V1); defeated(V2); not out(V2).
