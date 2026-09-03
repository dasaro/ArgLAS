:- att(V1,V2); not not_defended(V1); not not_defended(V2).
:- out(V1); not defeated(V1); not not_defended(V1).
out(V1) :- out(V2); att(V1,V2); not_defended(V1).
in(V1) :- att(V2,V1); not_defended(V2); not defeated(V1).
in(V1) :- att(V2,V1); not in(V2); not out(V1).
out(V1) :- att(V2,V1); supported(V2); not defeated(V2).
