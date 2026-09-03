:- in(V1); not_defended(V1).
in(V1) :- not_defended(V2); supported(V1); not att(V1,V2).
out(V1) :- att(V1,V2); not not_defended(V2); not supported(V2).
