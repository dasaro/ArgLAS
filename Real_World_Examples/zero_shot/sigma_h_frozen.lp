% sigma_H -- the consensus human acceptance policy of the AIJ paper (Fig. humansem),
% FROZEN on 2026-09-03 before any external (out-of-corpus) data was examined.
%
% A three-valued labelling of an argumentation framework (facts arg/1, att/2) is
% LEGAL under sigma_H iff none of the five `violated` rules fires.  Everything below is
% reproduced verbatim from the committed learning code:
%   generator + features : Real_World_Examples/fastlas_exp/fl_discover.py (_GEN, _FEATS, _FEATS_ENR)
%   auxiliary predicates : Real_World_Examples/fastlas_exp/aux9_combined.py (AUX9_BG)
%   rules                : Real_World_Examples/fastlas_exp/results/consensus.json
%                          (final_base consensus_rules[0..3] + the final_aux smoke/fire rule),
%                          i.e. exactly the rule set audited in
%                          Real_World_Examples/fastlas_exp/results/sigma_h_principle_audit.json.
% Verify with:  python3 Real_World_Examples/zero_shot/check_frozen.py
%
% Usage:  clingo 0 sigma_h_frozen.lp <af.lp>      (enumerates the legal labellings)

% ---- labelling generator (undec = neither in nor out) ----
0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- in(X), out(X).

% ---- target-independent features over the given labelling ----
attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y).
undec(X) :- arg(X), not in(X), not out(X).
reach(X, Y) :- att(X, Y).
reach(X, Z) :- att(X, Y), reach(Y, Z).
in_cycle(X) :- reach(X, X).

% ---- auxiliary predicates (reinstatement / degree salience) ----
% --- aux3: reinstatement / defense structure (over att + given in/out) ---
att_not_killed_by_in(X) :- att(Y, X), not attacked_by_in(Y).
reinstated(X) :- attacked(X), not att_not_killed_by_in(X).
att_unattacked(X) :- att(Y, X), not attacked(Y).
floating(X) :- attacked(X), not att_unattacked(X).
undefended_in(X) :- in(X), att(Y, X), not out(Y).
% --- aux2: degree-salience (purely structural, from arg/att only) ---
unattacked(X) :- arg(X), not attacked(X).
has_many_attackers(X) :- att(Y, X), att(Z, X), Y != Z.
has_unattacked_attacker(X) :- att(Y, X), unattacked(Y).

% ---- sigma_H: a labelling is illegal if any rule fires ----
% rule 1  Justification        [20/20 folds]
violated :- not attacked_by_in(V0), not defended(V0), in(V0), arg(V0).
% rule 2a Commitment (acyclic) -- defeated must be rejected   [16/20]
violated :- undec(V0), attacked_by_in(V0), not in_cycle(V0), arg(V0).
% rule 2b Commitment (acyclic) -- defended must be accepted   [10/20]
violated :- not in(V0), defended(V0), not in_cycle(V0), arg(V0).
% rule 3  Cycle caution        [15/20]
violated :- not defended(V0), in_cycle(V0), in(V0), arg(V0).
% rule 4  Smoke/fire (candidate) [5/20, auxiliary vocabulary]
violated :- reinstated(V0), has_many_attackers(V0), arg(V0).
:- violated.

#show in/1.
#show out/1.
