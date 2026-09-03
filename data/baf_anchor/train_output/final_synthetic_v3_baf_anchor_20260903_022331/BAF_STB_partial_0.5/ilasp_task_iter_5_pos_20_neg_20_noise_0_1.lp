:- not_defended(V1); not defeated(V1).
:- in(V1); defeated(V1).
in(V1) :- att(V1,V2); supported(V2); not att(V2,V1).
