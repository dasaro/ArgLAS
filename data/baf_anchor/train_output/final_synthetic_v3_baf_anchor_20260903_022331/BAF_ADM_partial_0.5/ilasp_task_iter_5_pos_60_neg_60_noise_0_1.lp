:- not_defended(V1); supported(V1); not defeated(V1).
out(V1) :- att(V1,V2); not not_defended(V2); not supported(V1).
out(V1) :- defeated(V2); not_defended(V1); not in(V2).
out(V1) :- att(V2,V1); defeated(V1); supported(V1).
