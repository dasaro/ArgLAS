 :- att(V2,V1); att(V1,V2); not not_defended(V2).
out(V1) :- defeated(V2); not_defended(V1); not att(V1,V2).

