:- att(V1,V1); supported(V1).
:- defeated(V1); not att(V1,V1); not not_defended(V1).
:- in(V1); defeated(V1); not att(V1,V1).
in(V1) :- att(V1,V1); not_defended(V2); not not_defended(V1).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
out(V1) :- att(V2,V1); not in(V1); not att(V1,V2).
