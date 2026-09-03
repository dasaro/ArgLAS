:- in(V1); defeated(V1); not not_defended(V1).
in(V1) :- in(V2); defeated(V2); not_defended(V1).
