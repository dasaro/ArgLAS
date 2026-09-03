out(V1) :- not_defended(V1); supported(V1).
:- out(V1); not_defended(V2); not not_defended(V1).
out(V1) :- defeated(V2); not_defended(V1); not att(V2,V1).
out(V1) :- in(V2); att(V2,V1); att(V1,V2).
