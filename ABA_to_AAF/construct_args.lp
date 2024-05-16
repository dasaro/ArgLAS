% First step of representing an ABA framework as an AA framework
% Construct the arguments, each having a tree structure

% Encoding for the following ABA framework:
% L = {p, q, r, s, t}
% R = {r <- s,t; s <- p; t <- q}
% p_ = t, q_ = r (where _ means contrary)

% To get the arguments run command
% clingo 0 construct_args.lp --heuristic=domain --enum=domrec

% ---- EXAMPLE ABA ----
% as(p).
% as(q).
% holds(r) :- holds(s), holds(t).
% holds(s) :- holds(p).
% holds(t) :- holds(q).
% --- END OF EXAMPLE ---

% For each assumption either assume it or not
0{assume(X)}1 :- as(X).

% If we assume an assumption, then it holds
holds(X) :- assume(X).

% Construct arguments with one root each
1{root(X): holds(X)}1.

#heuristic assume(X).[1, false]
#heuristic root(X).[1, true]

#show root/1.
#show assume/1.
#show contr/2.