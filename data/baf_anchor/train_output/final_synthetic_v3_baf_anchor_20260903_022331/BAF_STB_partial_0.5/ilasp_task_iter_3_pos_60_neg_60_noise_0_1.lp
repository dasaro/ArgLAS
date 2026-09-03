out(V1) :- not_defended(V1); not defeated(V1).
:- in(V1); att(V1,V2); supported(V2).
out(V1) :- att(V2,V1); supported(V2).
:- out(V1); not defeated(V1); not supported(V1).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
out(V1) :- in(V2); not_defended(V1); not defeated(V2).
