:- defeated(V1); not out(V1); not not_defended(V1).
in(V1) :- out(V2); defeated(V1); supported(V2).
out(V1) :- att(V1,V2); not_defended(V2); not supported(V1).
