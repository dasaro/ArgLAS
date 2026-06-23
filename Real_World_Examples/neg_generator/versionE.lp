arg(a).
arg(b).
arg(c).

0{ att(X,Y) }1 :- arg(X), arg(Y), X!=Y.
0{ undec(X) }1 :- arg(X).
:- undec(X), in(X).
:- undec(X), out(X).

:- in(a), in(b), in(c), att(a,b), att(b,a), att(c,b).
:- out(a), undec(b), in(c), att(a,b), att(b,a), att(c,a), att(c,b).
:- in(a), undec(b), undec(c), att(b,a), att(c,b).
:- undec(a), in(b), undec(c), att(b,a), att(b,c), att(c,b).
:- undec(a), undec(b), in(c), att(b,a), att(c,b).
:- undec(a), undec(b), undec(c).att(b,a), att(c,b).
:- undec(a), out(b), in(c).att(a,b), att(b,a), att(c,a), att(c,b).
:- undec(a), out(b), in(c).att(b,a), att(c,b).
:- undec(a), out(b), in(c).att(b,a), att(b,c), att(c,b).

#show in/1.
#show out/1.
#show undec/1.
#show arg/1.
#show att/2.
