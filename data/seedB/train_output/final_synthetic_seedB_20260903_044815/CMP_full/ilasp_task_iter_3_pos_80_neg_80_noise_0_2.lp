in(V1) :- supported(V1); not not_defended(V1).
out(V1) :- att(V2,V1); not defeated(V1); not not_defended(V2).
out(V1) :- att(V2,V1); not_defended(V1); not supported(V2).
out(V1) :- att(V2,V1); att(V1,V2); not supported(V1).
