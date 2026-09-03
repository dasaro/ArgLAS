:- in(V1); not not_defended(V1); not supported(V1).
:- out(V2); att(V1,V2); not not_defended(V2).
out(V1) :- not_defended(V2); supported(V1); not out(V2).
out(V1) :- defeated(V1); not_defended(V2); not defeated(V2).
