% Grounded CHECKER oracle for labelled-instance (discrimination) evaluation.
% Computes the grounded labelling in reserved predicates g_in/g_out (no
% feedback from the injected in/out label facts), rejects the instance
% (UNSAT -> empty model set) unless the injected labelling is a SUBSET of
% the grounded labelling (the same acceptance test the pool generator's
% verify_extension uses), and otherwise emits the full grounded labelling
% so that full_exact_model comparison against the learned side is total.
g_in(X) :- arg(X), g_out(Y) : att(Y,X).
g_out(X) :- arg(X), g_in(Y), att(Y,X).
:- in(X), not g_in(X).
:- out(X), not g_out(X).
in(X) :- g_in(X).
out(X) :- g_out(X).
