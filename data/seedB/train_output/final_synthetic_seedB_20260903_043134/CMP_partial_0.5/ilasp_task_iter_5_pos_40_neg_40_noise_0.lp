:- defeated(V1); not not_defended(V1).
out(V1) :- not_defended(V1).
:- att(V1,V2); not in(V1); not not_defended(V1).
