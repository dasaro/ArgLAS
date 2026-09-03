:- defeated(V1); not_defended(V1); not out(V1).
out(V1) :- att(V1,V2); defeated(V1); not supported(V1).
out(V1) :- att(V2,V1); not_defended(V1); not_defended(V2).
