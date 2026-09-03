:- defeated(V1); not not_defended(V1).
in(V1) :- defeated(V2); supported(V1); not att(V2,V1).
out(V1) :- out(V2); not_defended(V1); not att(V1,V2).
