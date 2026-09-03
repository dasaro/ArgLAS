:- out(V1); not defeated(V1).
out(V1) :- not_defended(V1).
out(V1) :- att(V2,V1); defeated(V1); not supported(V2).
