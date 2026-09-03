:- out(V1); not not_defended(V1).
:- in(V1); not_defended(V1).
:- defeated(V1); not out(V1).
