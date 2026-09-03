:- out(V1); supported(V1).
:- out(V1); not not_defended(V1).
out(V1) :- att(V1,V1); not defeated(V1).
out(V1) :- in(V2); att(V1,V2); not in(V1).
out(V1) :- in(V2); att(V1,V2); not att(V2,V1).
