:- out(V1); not defeated(V1).
out(V1) :- out(V2); defeated(V1); not att(V2,V1).
out(V1) :- att(V1,V2); supported(V2); not not_defended(V2).
in(V1) :- att(V1,V2); not defeated(V1); not supported(V2).
out(V1) :- in(V2); att(V2,V1); not att(V1,V2).
