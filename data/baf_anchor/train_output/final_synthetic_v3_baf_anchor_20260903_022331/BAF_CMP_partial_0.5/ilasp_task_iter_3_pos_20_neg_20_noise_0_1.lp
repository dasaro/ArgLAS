out(V1) :- att(V2,V1); defeated(V2); not not_defended(V2).
out(V1) :- att(V2,V1); not_defended(V1); not in(V2).
