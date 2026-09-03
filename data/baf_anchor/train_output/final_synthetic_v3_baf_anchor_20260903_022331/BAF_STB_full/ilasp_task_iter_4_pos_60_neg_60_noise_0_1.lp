:- out(V1); not defeated(V1).
out(V1) :- att(V1,V2); not_defended(V1); not att(V2,V1).
in(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V1).
out(V1) :- att(V2,V1); att(V1,V2); not out(V2).
