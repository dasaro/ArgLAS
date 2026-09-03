:- defeated(V1); not not_defended(V1).
in(V1) :- supported(V1).
out(V1) :- att(V1,V2); defeated(V1); not att(V2,V1).
out(V1) :- in(V2); att(V2,V1); not_defended(V2).
