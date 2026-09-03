:- in(V2); out(V1); defeated(V2).
out(V1) :- out(V2); not_defended(V1); not att(V2,V1).
out(V1) :- att(V2,V1); not att(V1,V2); not supported(V1).
