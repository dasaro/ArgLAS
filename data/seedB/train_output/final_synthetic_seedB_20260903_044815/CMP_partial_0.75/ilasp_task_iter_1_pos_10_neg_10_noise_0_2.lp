:- att(V1,V2); not out(V2); not att(V2,V1).
in(V1) :- arg(V1); not not_defended(V1).
