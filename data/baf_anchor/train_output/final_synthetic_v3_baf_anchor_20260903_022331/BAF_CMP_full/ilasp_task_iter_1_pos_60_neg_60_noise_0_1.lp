:- not_defended(V1); not out(V1); not defeated(V1).
:- att(V1,V2); not out(V1); not out(V2).
out(V1) :- not_defended(V1); supported(V2).
:- out(V2); supported(V1); not not_defended(V2).
out(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V2).
