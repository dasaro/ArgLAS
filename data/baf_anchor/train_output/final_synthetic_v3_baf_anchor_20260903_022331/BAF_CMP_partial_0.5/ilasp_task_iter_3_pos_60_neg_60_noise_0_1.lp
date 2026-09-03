:- in(V2); not_defended(V1); not defeated(V1).
:- defeated(V1); supported(V1); not not_defended(V1).
out(V1) :- in(V2); defeated(V1); not defeated(V2).
in(V1) :- att(V1,V2); not in(V2); not not_defended(V1).
out(V1) :- att(V2,V1); att(V1,V2); not out(V2).
