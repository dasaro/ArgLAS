:- defeated(V1); not not_defended(V1).
:- in(V2); att(V1,V2); supported(V1).
out(V1) :- att(V2,V1); not out(V2); not att(V1,V2).
