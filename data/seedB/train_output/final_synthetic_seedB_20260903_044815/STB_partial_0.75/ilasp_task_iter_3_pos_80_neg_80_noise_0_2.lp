:- out(V2); att(V1,V2); supported(V2).
in(V1) :- out(V2); defeated(V2); supported(V1).
in(V1) :- in(V2); att(V1,V2); defeated(V2).
out(V1) :- att(V2,V1); att(V1,V2); not not_defended(V2).
