% Totality completion for learned-side evaluation: every argument is labelled
% in or out. Loaded by arglas.solver_runtime.solve_models when the resolved
% completion_rules setting (semantics_config.json) is true for the stage.
in(X) :- arg(X), not out(X).
out(X) :- arg(X), not in(X).
