:- not_defended(V2); supported(V1); not out(V2).
in(V1) :- not_defended(V2); supported(V1); not att(V2,V1).
out(V1) :- att(V1,V2); not not_defended(V1); not not_defended(V2).
in(V1) :- att(V2,V1); not in(V2); not out(V1).
