:- in(V1); not supported(V1).
:- not_defended(V1); not out(V1).
in(V1) :- arg(V1); not not_defended(V1).
