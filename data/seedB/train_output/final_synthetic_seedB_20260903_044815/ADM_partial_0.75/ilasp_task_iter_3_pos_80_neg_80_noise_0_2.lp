:- in(V2); not_defended(V1); not supported(V2).
:- in(V2); att(V1,V2); supported(V1).
out(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V1).
