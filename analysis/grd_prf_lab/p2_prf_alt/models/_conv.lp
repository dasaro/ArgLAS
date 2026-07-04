:- in(V1); defeated(V1).
:- att(V1,V2); not in(V2); not defeated(V2).
#heuristic in(X) : arg(X). [1, true]
