:- defeated(V1); not not_defended(V1).
:- out(V1); not not_defended(V1).
out(V1) :- att(V2,V1); not_defended(V1); not in(V2).
