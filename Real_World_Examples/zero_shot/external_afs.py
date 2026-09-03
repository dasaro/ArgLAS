"""External stimulus AFs transcribed from the published papers (zero-shot evaluation).

Convention: (attacker, attacked); argument letters are the papers' labels (uppercase); use
lower(af) to obtain clingo-safe lowercase constants.  Cramer & Guillaume (2019) instantiate every attack as
"islander X says islander Y is not trustworthy" => X's argument attacks Y's argument; the
twelve AFs below were derived from the natural-language argument sets in the appendix of
the technical report (arXiv:1902.10552) and cross-checked against the semantics-prediction
columns of its Fig. 2 (see verify_external_afs.py).
"""
# ---- Cramer & Guillaume 2019 (JELIA / arXiv:1902.10552): 12 AFs, 60 arguments (numbered 1..60)
CG2019 = {
    "AF1":  {"args": ["G","H","I","J"], "num": {"G":1,"H":2,"I":3,"J":4},
             "att": [("G","H"),("H","I")]},
    "AF2":  {"args": ["T","U","V"], "num": {"T":5,"U":6,"V":7},
             "att": [("T","U"),("U","T"),("U","V")]},
    "AF3":  {"args": ["L","M","N","O","P"], "num": {"L":8,"M":9,"N":10,"O":11,"P":12},
             "att": [("L","M"),("L","O"),("M","N"),("M","O"),("N","L"),("N","O"),("O","P")]},
    "AF4":  {"args": ["R","S","T","U","V"], "num": {"R":13,"S":14,"T":15,"U":16,"V":17},
             "att": [("R","S"),("S","T"),("T","R"),("T","S"),("T","U"),("U","V")]},
    "AF5":  {"args": ["W","X","Y","Z","A","B"], "num": {"W":18,"X":19,"Y":20,"Z":21,"A":22,"B":23},
             "att": [("W","X"),("X","Y"),("X","A"),("Y","Z"),("Y","A"),("Z","W"),("A","B")]},
    "AF6":  {"args": ["C","D","E","F","G","H","I"], "num": {"C":24,"D":25,"E":26,"F":27,"G":28,"H":29,"I":30},
             "att": [("C","D"),("D","E"),("E","F"),("E","H"),("F","G"),("F","H"),("G","C"),("H","I")]},
    "AF7":  {"args": ["G","H","I","J","K"], "num": {"G":31,"H":32,"I":33,"J":34,"K":35},
             "att": [("G","H"),("G","I"),("G","J"),("H","K"),("I","K"),("J","K")]},
    "AF8":  {"args": ["T","U","V"], "num": {"T":36,"U":37,"V":38},
             "att": [("T","U"),("U","V"),("V","U")]},
    "AF9":  {"args": ["L","M","N","O"], "num": {"L":39,"M":40,"N":41,"O":42},
             "att": [("L","M"),("L","N"),("M","L"),("M","N"),("N","O")]},
    "AF10": {"args": ["R","S","T","U","V"], "num": {"R":43,"S":44,"T":45,"U":46,"V":47},
             "att": [("R","S"),("S","R"),("S","T"),("T","U"),("U","V"),("V","T")]},
    "AF11": {"args": ["W","X","Y","Z","A"], "num": {"W":48,"X":49,"Y":50,"Z":51,"A":52},
             "att": [("W","X"),("X","Y"),("X","Z"),("Y","W"),("Y","Z"),("Z","A")]},
    "AF12": {"args": ["C","D","E","F","G","H","I","J"], "num": {"C":53,"D":54,"E":55,"F":56,"G":57,"H":58,"I":59,"J":60},
             "att": [("C","D"),("D","E"),("E","F"),("E","I"),("F","G"),("F","I"),("G","H"),("H","C"),("I","J")]},
}
# ---- Cramer & Guillaume 2018 (COMMA): 3 AFs (Fig. 1-3 of the paper)
CG2018 = {
    "simple":   {"args": ["A","B","C"], "att": [("B","A"),("C","B")]},
    "floating": {"args": ["A","B","C","D"], "att": [("B","A"),("C","B"),("D","B"),("C","D"),("D","C")]},
    "cycle3":   {"args": ["A","B","C","D","E"], "att": [("B","A"),("C","B"),("D","B"),("E","B"),("C","D"),("D","E"),("E","C")]},  # Fig. 3 (= condition G of Guillaume et al. 2022)
}
# ---- Rahwan et al. 2010 (Cognitive Science): simple (Study 1, 2) and floating (Study 2) reinstatement
RAHWAN2010 = {
    "simple":   {"args": ["A","B","C"], "att": [("B","A"),("C","B")]},
    "floating": {"args": ["A","B","C","D"], "att": [("B","A"),("C","B"),("D","B"),("C","D"),("D","C")]},
}


def lower(af):
    """Same AF with lowercase (clingo-constant) argument names."""
    out = {"args": [a.lower() for a in af["args"]], "att": [(x.lower(), y.lower()) for x, y in af["att"]]}
    if "num" in af:
        out["num"] = {a.lower(): n for a, n in af["num"].items()}
    return out
