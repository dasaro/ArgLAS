:- out(V1); not defeated(V1).
:- att(V1,V2); not not_defended(V1); not not_defended(V2).
in(V1) :- in(V2); defeated(V1); not_defended(V2).
