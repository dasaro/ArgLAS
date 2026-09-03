out(V1) :- defeated(V1).
:- defeated(V2); not_defended(V1); not defeated(V1).
