:- in(V1); defeated(V1).
:- att(V1,V2); supported(V2); not not_defended(V1).
out(V1) :- att(V1,V2); not_defended(V1); not att(V2,V1).
in(V1) :- att(V1,V2); not in(V2); not out(V1).
