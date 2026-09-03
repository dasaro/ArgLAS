:- not_defended(V1); supported(V1); not in(V1).
out(V1) :- out(V2); defeated(V1); not att(V2,V1).
in(V1) :- defeated(V2); supported(V1); not att(V2,V1).
in(V1) :- in(V2); supported(V1); not att(V1,V2).
out(V1) :- in(V2); att(V1,V2); not att(V2,V1).
