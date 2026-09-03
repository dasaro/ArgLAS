out(V1) :- att(V2,V1); supported(V1); not att(V1,V2).
out(V1) :- att(V2,V1); att(V1,V2); not supported(V1).
