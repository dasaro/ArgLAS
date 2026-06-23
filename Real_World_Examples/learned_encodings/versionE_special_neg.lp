 :- att(V1,V2); not defeated(V2).
 :- att(V1,V2); not not_defended(V1); not not_defended(V2).
 :- att(V1,V2); not_defended(V1); not att(V2,V1).
 :- att(V1,V2); not_defended(V1); not_defended(V2).
 