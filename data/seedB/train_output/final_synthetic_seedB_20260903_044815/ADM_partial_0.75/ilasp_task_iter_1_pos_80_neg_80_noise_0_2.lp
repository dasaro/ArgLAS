out(V1) :- defeated(V1); supported(V2); not att(V2,V1).
out(V1) :- out(V2); not_defended(V1); supported(V2).
in(V1) :- defeated(V2); not_defended(V1); not not_defended(V2).
out(V1) :- att(V2,V1); not out(V2); not supported(V2).
out(V1) :- att(V2,V1); supported(V2); not defeated(V1).
out(V1) :- att(V2,V1); att(V1,V2); not defeated(V2).
