:- out(V1); supported(V1).
out(V1) :- att(V1,V2); not out(V2); not att(V2,V1).
