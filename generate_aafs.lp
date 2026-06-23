arg(1..n).

% Probabilistically include each attack relation
{ att(X,Y) : arg(X), arg(Y), X != Y }.
:- arg(X), arg(Y), X != Y, not att(X,Y), not att(Y,X).

size(Z) :- Z = #sum{ 1,X,Y : att(X,Y) }.

