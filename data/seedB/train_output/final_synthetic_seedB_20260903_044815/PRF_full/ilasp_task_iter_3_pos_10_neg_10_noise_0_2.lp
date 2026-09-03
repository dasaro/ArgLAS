out(V1) :- defeated(V1); not not_defended(V1).
in(V1) :- in(V2); not_defended(V1); not att(V2,V1).
