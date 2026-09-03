out(V1) :- out(V2); defeated(V1).
out(V1) :- att(V1,V2); not att(V2,V1); not supported(V1).
out(V1) :- att(V2,V1); not in(V2); not not_defended(V2).
in(V1) :- att(V2,V1); att(V1,V2); not defeated(V1).
