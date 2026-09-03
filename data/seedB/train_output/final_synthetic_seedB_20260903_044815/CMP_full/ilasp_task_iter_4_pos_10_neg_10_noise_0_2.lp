:- out(V1); not_defended(V2); not out(V2).
in(V1) :- att(V2,V1); not in(V2); not not_defended(V2).
