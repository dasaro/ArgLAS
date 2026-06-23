 :- in(V1); not_defended(V1).
in(V1) :- att(V2,V1); not att(V1,V2); not defeated(V1).

