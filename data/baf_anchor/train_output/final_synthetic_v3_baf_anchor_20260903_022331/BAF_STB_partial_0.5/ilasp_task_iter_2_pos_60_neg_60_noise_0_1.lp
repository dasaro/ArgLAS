out(V1) :- att(V1,V2); defeated(V1); not att(V2,V1).
in(V1) :- att(V1,V2); not in(V2); not defeated(V1).
out(V1) :- att(V2,V1); defeated(V1); not_defended(V2).
in(V1) :- att(V2,V1); att(V1,V2); supported(V1).
