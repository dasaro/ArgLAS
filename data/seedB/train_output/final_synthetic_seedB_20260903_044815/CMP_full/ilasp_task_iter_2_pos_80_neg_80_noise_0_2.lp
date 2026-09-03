:- att(V1,V2); not in(V2); not not_defended(V2).
:- att(V1,V2); not_defended(V1); not out(V1).
out(V1) :- att(V1,V2); not att(V2,V1); not not_defended(V2).
