:- out(V2); att(V1,V2); supported(V2).
:- in(V1); not_defended(V1); supported(V1).
:- att(V1,V2); not not_defended(V1); not not_defended(V2).
out(V1) :- att(V1,V2); not in(V2); not supported(V1).
in(V1) :- att(V1,V2); defeated(V2); not not_defended(V1).
