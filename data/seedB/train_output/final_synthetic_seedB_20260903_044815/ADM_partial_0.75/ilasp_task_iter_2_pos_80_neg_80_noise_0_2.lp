out(V1) :- not_defended(V1); not defeated(V1).
out(V1) :- defeated(V1); not not_defended(V1).
in(V1) :- defeated(V2); not_defended(V1); not out(V2).
