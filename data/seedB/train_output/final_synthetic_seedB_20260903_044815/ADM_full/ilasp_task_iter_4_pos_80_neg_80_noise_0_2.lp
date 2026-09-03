out(V1) :- defeated(V1); not not_defended(V1).
out(V1) :- out(V2); not_defended(V1); supported(V2).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
