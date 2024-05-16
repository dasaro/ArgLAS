#pos({in(b), out(a)},
     {out(b), in(a)},{
arg(a).
arg(b).
att(a,b).
att(b,a).
}).

#pos({in(a), in(b)},
     {out(a), out(b)},{
arg(a).
arg(b).
}).

#pos({in(a), out(b)},
     {out(a),in(b)},{
arg(a).
arg(b).
att(a,b).
}).

#pos({in(a),out(b),in(c),out(d)},
     {out(a),in(b),out(c),in(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b). 
att(b,c). 
att(d,c). 
att(c,d).
}).

#pos({in(a),out(b),out(c),in(d)},
     {out(a),in(b),in(c),out(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b). 
att(b,c). 
att(d,c). 
att(c,d).
}).

#pos({out(a),out(b),in(c),in(d)},
     {in(a),in(b),out(c),out(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b). 
att(b,c). 
att(c,a).
att(d,b).
att(b,d).
}).

#pos({in(a),out(b),out(c),out(d),in(e)},
     {out(a),in(b),in(c),in(d),out(e)},{
arg(a).
arg(b).
arg(c).
arg(d).
arg(e).
att(a,b). 
att(a,c). 
att(a,d).
att(b,e).
att(c,e).
att(d,e).
}).

#pos({out(a0),out(a1),out(a2),out(a3),out(a4),out(a5)},
     {in(a0),in(a1),in(a2),in(a3),in(a4),in(a5)},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a1,a0).
att(a2,a3).
att(a4,a5).
att(a2,a0).
att(a4,a0).
att(a5,a0).
att(a1,a2).
att(a3,a1).
att(a2,a4).
att(a3,a5).
att(a3,a4).
att(a1,a5).
}).

#neg({in(a0),in(a1),in(a2),in(a3),in(a4),in(a5)},
     {},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a1,a0).
att(a2,a3).
att(a4,a5).
att(a2,a0).
att(a4,a0).
att(a5,a0).
att(a1,a2).
att(a3,a1).
att(a2,a4).
att(a3,a5).
att(a3,a4).
att(a1,a5).
}).

#pos({in(a0),out(a1),out(a2),out(a3),in(a4),in(a5)},
     {out(a0),in(a1),in(a2),in(a3),out(a4),out(a5)},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a0,a1).
att(a1,a0).
att(a2,a0).
att(a5,a2).
att(a1,a4).
att(a0,a3).
att(a4,a1).
}).

#pos({out(a0),in(a1),out(a2),in(a3),out(a4),in(a5)},
     {in(a0),out(a1),in(a2),out(a3),in(a4),out(a5)},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a0,a1).
att(a1,a0).
att(a2,a0).
att(a5,a2).
att(a1,a4).
att(a0,a3).
att(a4,a1).
}).

#neg({out(a0),out(a1),out(a2),out(a3),out(a4),in(a5)},
     {},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a0,a1).
att(a1,a0).
att(a2,a0).
att(a5,a2).
att(a1,a4).
att(a0,a3).
att(a4,a1).
}).

#pos({out(a0),in(a1),out(a2),out(a3),in(a4),out(a5)},
     {in(a0),out(a1),in(a2),in(a3),out(a4),in(a5)},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a4,a2).
att(a0,a4).
att(a1,a0).
att(a2,a3).
att(a4,a5).
att(a0,a2).
att(a2,a1).
att(a0,a5).
att(a3,a5).
att(a5,a1).
att(a1,a3).
att(a3,a4).
}).

#neg({out(a0),out(a1),out(a2),out(a3),out(a4),out(a5)},
     {},{
arg(a0).
arg(a1).
arg(a2).
arg(a3).
arg(a4).
arg(a5).
att(a4,a2).
att(a0,a4).
att(a1,a0).
att(a2,a3).
att(a4,a5).
att(a0,a2).
att(a2,a1).
att(a0,a5).
att(a3,a5).
att(a5,a1).
att(a1,a3).
att(a3,a4).
}).

#neg({in(a),out(b),out(c),out(d),out(e)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
arg(e).
att(a,b). 
att(a,c). 
att(a,d).
att(b,e).
att(c,e).
att(d,e).
}).

#neg({out(a),out(b),out(c),out(d),out(e)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
arg(e).
att(a,b). 
att(a,c). 
att(a,d).
att(b,e).
att(c,e).
att(d,e).
}).

% Definitions

support(X,Z) :- support(X,Y), support(Y,Z).

supported(X) :- support(Y,X), in(Y).

valpref(X,Y) :- valpref(X,Z), valpref(Z,Y).

pref(X,Y) :- valpref(U,V), val(X,U), val(Y,V).
pref(X,Y) :- pref(X,Z), pref(Z,Y).

defeat(X,Y) :- att(Z,Y), support(X,Z). 
defeat(X,Y) :- att(X,Z), support(Z,Y). 
defeat(X,Y) :- att(X,Y), not pref(Y,X).

defeated(X) :- in(Y), defeat(Y,X).

not_defended(X) :- defeat(Y,X), not defeated(Y).

% Mode declarations

#modeh(in(var(arg))).
#modeh(out(var(arg))).

#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(arg(var(arg)), (positive)).
#modeb(att(var(arg), var(arg))).
#modeb(defeated(var(arg))).
#modeb(supported(var(arg))).
#modeb(not_defended(var(arg))).

#maxv(2).
