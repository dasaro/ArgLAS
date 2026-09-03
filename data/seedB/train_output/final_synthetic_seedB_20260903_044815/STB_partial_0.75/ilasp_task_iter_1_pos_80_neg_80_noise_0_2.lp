:- out(V1); supported(V1).
:- att(V1,V2); not not_defended(V1); not not_defended(V2).
out(V1) :- out(V2); not_defended(V1); not defeated(V1).
in(V1) :- att(V1,V2); not in(V2); not not_defended(V1).
in(V1) :- in(V2); att(V2,V1); defeated(V2).
