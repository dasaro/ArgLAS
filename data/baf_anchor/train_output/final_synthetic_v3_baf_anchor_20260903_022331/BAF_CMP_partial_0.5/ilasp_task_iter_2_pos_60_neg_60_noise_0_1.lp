:- supported(V1); not defeated(V1).
:- in(V1); not_defended(V1); not defeated(V1).
:- defeated(V2); not_defended(V1); not not_defended(V2).
:- supported(V1); not in(V1); not not_defended(V1).
:- att(V1,V2); not defeated(V2); not not_defended(V1).
out(V1) :- out(V2); supported(V1); not att(V2,V1).
out(V1) :- in(V2); att(V1,V2); not_defended(V2).
in(V1) :- att(V2,V1); not att(V1,V2); not not_defended(V1).
out(V1) :- in(V2); att(V2,V1); supported(V1).
