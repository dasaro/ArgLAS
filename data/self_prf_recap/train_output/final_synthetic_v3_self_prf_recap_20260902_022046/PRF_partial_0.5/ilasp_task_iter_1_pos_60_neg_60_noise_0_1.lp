:- out(V1); not defeated(V1).
:- in(V1); not_defended(V1); not att(V1,V1).
out(V1) :- not_defended(V1); supported(V2); not att(V1,V1).
out(V1) :- att(V1,V2); not not_defended(V1); not not_defended(V2).
in(V1) :- in(V2); defeated(V2); not_defended(V1).
