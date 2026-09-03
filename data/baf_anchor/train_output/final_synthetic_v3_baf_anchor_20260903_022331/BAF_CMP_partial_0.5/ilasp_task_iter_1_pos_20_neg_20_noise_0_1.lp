out(V1) :- not_defended(V1).
:- att(V1,V2); supported(V2); not defeated(V2).
:- out(V1); not defeated(V1); not not_defended(V1).
out(V1) :- att(V1,V2); not not_defended(V2); not supported(V2).
