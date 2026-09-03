out(V1) :- defeated(V1).
in(V1) :- att(V1,V2); defeated(V2); not defeated(V1).
