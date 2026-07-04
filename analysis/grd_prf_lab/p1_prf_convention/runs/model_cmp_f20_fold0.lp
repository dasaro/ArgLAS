out(V1) :- defeated(V1).
:- out(V1); not not_defended(V1).
