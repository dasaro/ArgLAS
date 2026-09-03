out(V1) :- not_defended(V1); not defeated(V1).
:- not_defended(V2); supported(V1); not defeated(V2).
:- att(V1,V2); supported(V1); not not_defended(V2).
:- att(V1,V2); not not_defended(V1); not not_defended(V2).
out(V1) :- out(V2); att(V1,V2); not_defended(V1).
