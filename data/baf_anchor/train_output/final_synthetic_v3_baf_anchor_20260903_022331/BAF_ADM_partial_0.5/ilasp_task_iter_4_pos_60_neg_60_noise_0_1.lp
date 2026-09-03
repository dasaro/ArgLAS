:- out(V1); supported(V1); not defeated(V1).
out(V1) :- att(V1,V2); defeated(V1); not supported(V2).
out(V1) :- att(V1,V2); not_defended(V1); not in(V2).
in(V1) :- att(V2,V1); supported(V1); not defeated(V2).
