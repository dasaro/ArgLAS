% Second step of representing an ABA framework as an AAF
% Generate the attacks between arguments based on their structure

% construct_args.lp constructs the arguments for the following ABA framework:
% L = {p, q, r, s, t}
% R = {r <- s,t; s <- p; t <- q}
% p_ = t, q_ = r (where _ means contrary)
% The arguments are {p} |- p; {q} |- q; {p} |- s; {q} |- t; {p, q} |- r;

% The roots of the arguments that are not assumptions
root(3, s).
root(4, t).
root(5, r).

% Assumptions for each argument
as(1, p).
as(2, q).
as(3, p).
as(4, q).
as(5, p).
as(5, q).

% Contraries
contr(p, t).
contr(q, r).

att(X, Y) :- contr(P, Q), root(X, Q), as(Y, P).

#show att/2.