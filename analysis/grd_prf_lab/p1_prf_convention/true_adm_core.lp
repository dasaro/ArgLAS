% TRUE admissible core in the pipeline's choice representation
% (background_knowledge.lp supplies choice rules + defeat/defeated/not_defended).
:- in(X), in(Y), att(X, Y).
:- in(X), not_defended(X).
