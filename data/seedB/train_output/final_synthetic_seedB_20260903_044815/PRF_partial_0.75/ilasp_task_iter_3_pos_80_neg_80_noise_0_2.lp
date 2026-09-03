:- att(V1,V2); not out(V1); not not_defended(V2).
:- att(V1,V2); supported(V1); not in(V1).
out(V1) :- out(V2); defeated(V1); not att(V2,V1).
out(V1) :- att(V1,V2); not att(V2,V1); not supported(V1).
