:- defeated(V1); not not_defended(V1).
:- in(V1); not_defended(V1); not att(V1,V1).
in(V1) :- att(V2,V2); defeated(V1); supported(V2).
