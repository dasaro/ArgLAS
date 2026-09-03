:- defeated(V1); not not_defended(V1).
out(V1) :- not_defended(V1); supported(V2); not att(V2,V1).
in(V1) :- att(V2,V1); not defeated(V1); not supported(V2).
