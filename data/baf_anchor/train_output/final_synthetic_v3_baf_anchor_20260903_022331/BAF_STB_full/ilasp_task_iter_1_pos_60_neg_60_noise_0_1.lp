:- defeated(V1); not out(V1); not supported(V1).
out(V1) :- in(V2); att(V2,V1).
in(V1) :- att(V2,V1); not att(V1,V2); not defeated(V1).
