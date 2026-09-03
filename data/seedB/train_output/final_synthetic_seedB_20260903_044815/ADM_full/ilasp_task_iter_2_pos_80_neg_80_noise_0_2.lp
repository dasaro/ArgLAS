:- att(V1,V2); not not_defended(V1); not not_defended(V2).
:- in(V2); out(V1); not supported(V2).
out(V1) :- out(V2); not_defended(V1); not not_defended(V2).
out(V1) :- att(V2,V1); att(V1,V2); not_defended(V1).
