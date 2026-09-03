:- out(V1); not not_defended(V1).
:- in(V1); defeated(V1); not not_defended(V1).
in(V1) :- arg(V1); not defeated(V1); not not_defended(V1).
