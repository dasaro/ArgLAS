out(V1) :- defeated(V1).
in(V1) :- att(V2,V1); att(V1,V2); not defeated(V1).
