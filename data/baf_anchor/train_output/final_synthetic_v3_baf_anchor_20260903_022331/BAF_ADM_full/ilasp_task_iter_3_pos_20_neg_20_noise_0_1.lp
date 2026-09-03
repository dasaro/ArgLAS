:- in(V1); defeated(V1); supported(V1).
out(V1) :- att(V2,V1); not defeated(V2); not not_defended(V2).
out(V1) :- att(V2,V1); att(V1,V2); defeated(V1).
