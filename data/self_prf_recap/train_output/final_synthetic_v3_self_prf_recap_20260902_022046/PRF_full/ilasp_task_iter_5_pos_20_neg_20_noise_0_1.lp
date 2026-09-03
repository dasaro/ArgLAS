:- out(V1); supported(V1); not not_defended(V1).
out(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V2).
