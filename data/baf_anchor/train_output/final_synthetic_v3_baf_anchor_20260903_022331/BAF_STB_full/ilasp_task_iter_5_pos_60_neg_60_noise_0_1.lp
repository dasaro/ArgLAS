:- defeated(V1); not not_defended(V1).
:- out(V1); not defeated(V1); not supported(V1).
out(V1) :- out(V2); att(V1,V2); not_defended(V1).
