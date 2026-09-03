:- not_defended(V1); supported(V1).
:- in(V1); defeated(V1).
in(V1) :- out(V2); att(V2,V1); not defeated(V1).
