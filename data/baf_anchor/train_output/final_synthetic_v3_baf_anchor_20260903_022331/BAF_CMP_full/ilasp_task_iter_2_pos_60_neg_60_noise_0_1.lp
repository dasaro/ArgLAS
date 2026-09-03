in(V1) :- att(V1,V2); defeated(V2); not not_defended(V1).
out(V1) :- att(V2,V1); not not_defended(V2); not supported(V2).
