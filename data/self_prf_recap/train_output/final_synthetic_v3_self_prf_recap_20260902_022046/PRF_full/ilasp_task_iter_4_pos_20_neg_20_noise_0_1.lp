in(V1) :- supported(V1).
:- out(V1); att(V1,V1); not not_defended(V1).
out(V1) :- att(V2,V1); not att(V1,V2); not att(V2,V2).
out(V1) :- att(V2,V2); not_defended(V1); not att(V1,V2).
