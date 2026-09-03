:- out(V1); not defeated(V1); not not_defended(V1).
out(V1) :- att(V2,V1); not out(V2); not supported(V1).
in(V1) :- att(V2,V1); supported(V1); not in(V2).
