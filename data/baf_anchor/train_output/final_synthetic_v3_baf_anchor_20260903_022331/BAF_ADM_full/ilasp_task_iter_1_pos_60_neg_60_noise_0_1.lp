:- defeated(V1); not not_defended(V1).
out(V1) :- not_defended(V1).
in(V1) :- att(V2,V1); att(V1,V2); supported(V1).
