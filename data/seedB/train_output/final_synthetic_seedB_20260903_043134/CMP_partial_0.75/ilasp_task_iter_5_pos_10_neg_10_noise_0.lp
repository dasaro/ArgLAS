out(V1) :- defeated(V1).
:- arg(V1); not in(V1); not not_defended(V1).
