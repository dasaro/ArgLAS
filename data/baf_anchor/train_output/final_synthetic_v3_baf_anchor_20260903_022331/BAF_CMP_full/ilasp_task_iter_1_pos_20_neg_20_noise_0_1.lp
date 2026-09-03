in(V1) :- in(V2); not_defended(V1); not defeated(V1).
out(V1) :- in(V2); not_defended(V1); not not_defended(V2).
out(V1) :- defeated(V1); not not_defended(V1); not supported(V1).
