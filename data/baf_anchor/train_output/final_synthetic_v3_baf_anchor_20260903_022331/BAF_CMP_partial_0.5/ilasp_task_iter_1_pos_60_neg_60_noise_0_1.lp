out(V1) :- not_defended(V1).
:- supported(V1); not in(V1); not not_defended(V1).
:- att(V1,V2); defeated(V2); not out(V2).
