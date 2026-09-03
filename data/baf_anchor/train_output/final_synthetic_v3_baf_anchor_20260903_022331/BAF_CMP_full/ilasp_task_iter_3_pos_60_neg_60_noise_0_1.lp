out(V1) :- att(V1,V2); defeated(V1); not att(V2,V1).
in(V1) :- out(V2); att(V2,V1); not not_defended(V2).
in(V1) :- att(V2,V1); att(V1,V2); supported(V1).
