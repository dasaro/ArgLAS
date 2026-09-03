:- defeated(V2); not_defended(V1); not not_defended(V2).
out(V1) :- not_defended(V1); supported(V2).
out(V1) :- defeated(V1); not not_defended(V1); not supported(V1).
