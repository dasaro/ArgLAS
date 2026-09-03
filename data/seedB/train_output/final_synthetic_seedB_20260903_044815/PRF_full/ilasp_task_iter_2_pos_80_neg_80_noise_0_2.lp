out(V1) :- out(V2); not_defended(V1); not supported(V1).
in(V1) :- defeated(V2); not_defended(V1); supported(V1).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
in(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V1).
