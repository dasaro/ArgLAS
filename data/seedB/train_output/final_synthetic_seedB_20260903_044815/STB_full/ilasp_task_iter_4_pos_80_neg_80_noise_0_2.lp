:- not_defended(V1); not defeated(V1).
:- att(V1,V2); not in(V1); not not_defended(V1).
out(V1) :- att(V2,V1); not att(V1,V2); not supported(V1).
