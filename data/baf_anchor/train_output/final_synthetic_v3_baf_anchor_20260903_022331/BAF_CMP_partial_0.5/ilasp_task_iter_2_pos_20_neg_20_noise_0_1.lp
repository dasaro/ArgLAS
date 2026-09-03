:- out(V1); att(V1,V2); not defeated(V1).
out(V1) :- not_defended(V2); supported(V1).
out(V1) :- att(V2,V1); not not_defended(V2); not supported(V2).
