out(V1) :- defeated(V1); supported(V2); not not_defended(V2).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
in(V1) :- att(V1,V2); not not_defended(V1); not supported(V2).
