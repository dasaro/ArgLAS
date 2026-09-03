:- att(V1,V2); not_defended(V1); not att(V2,V1).
:- in(V2); not_defended(V1); not att(V2,V1).
out(V1) :- in(V2); att(V1,V2); not att(V2,V1).
out(V1) :- att(V2,V1); supported(V2); not att(V1,V2).
