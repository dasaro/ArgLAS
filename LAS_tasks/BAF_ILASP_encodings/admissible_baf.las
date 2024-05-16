% Examples

#pos({in(a), in(b), in(c)},
     {out(a), out(b), out(c)},{
arg(a).
arg(b).
arg(c).
}).

#pos({in(a), out(b), in(c)},
     {out(a), in(b), out(c)},{
arg(a).
arg(b).
arg(c).
}).

#pos({in(a), out(b)},
     {out(a), in(b)},{
arg(a).
arg(b).
att(a, b).
att(b, a).
}).

#pos({in(b), out(a)},
     {out(b), in(a)},{
arg(a).
arg(b).
att(a, b).
att(b, a).
}).

#pos({out(b), out(a)},
     {in(b), in(a)},{
arg(a).
arg(b).
att(a, b).
att(b, a).
}).

#pos({in(a),out(b),out(c)},
     {out(a),in(b),in(c)},{
arg(a).
arg(b).
arg(c).

att(a, b).
att(b, c).
}).

#pos({out(a),out(b),out(c),out(d)},
     {in(a),in(b),in(c),in(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a, b).
att(b, c).
att(c, d).
att(b,d).
}).

#pos({in(b),out(c),in(d)},
     {out(b),in(c),out(d)},{
arg(b).
arg(c).
arg(d).
att(b, c).
att(d, c).
}).

#pos({out(b),out(c),in(d)},
     {in(b),in(c),out(d)},{
arg(b).
arg(c).
arg(d).
att(b, c).
att(d, c).
}).

#neg({in(a), in(b), in(c), in(d)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b).
att(b,a).
att(b,c).
att(a,c).
att(c,d).
}).

#neg({in(a), in(b), out(c), out(d)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b).
att(b,a).
att(b,c).
att(a,c).
att(c,d).
}).

% Examples containing support

#pos({in(a), out(b), in(c)},
     {out(a), in(b), out(c)},{
arg(a).
arg(b).
arg(c).
att(a, b).
att(b, a).
support(c,a).
}).

#pos({out(a), out(b), in(c)},
     {in(a), in(b), out(c)},{
arg(a).
arg(b).
arg(c).
att(a, b).
att(b, a).
support(c,a).
}).

#pos({in(a), out(b), in(c)},
     {out(a), in(b), out(c)},{
arg(a).
arg(b).
arg(c).
att(a, b).
att(b, a).
support(a,c).
}).

#pos({out(a), in(b), out(c)},
     {in(a), out(b), in(c)},{
arg(a).
arg(b).
arg(c).
att(a, b).
att(b, a).
support(a,c).
}).

#pos({in(a), out(b), out(c)},
     {out(a), in(b), in(c)},{
arg(a).
arg(b).
arg(c).
att(a, b).
att(a, c).
support(c,b).
}).

#pos({in(a), out(b), out(c), in(d)},
     {out(a), in(b), in(c), out(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a, b).
att(a, c).
support(d,c).
support(c,b).
}).

#pos({in(a), out(b), out(c), in(d)},
     {out(a), in(b), in(c), out(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a, b).
att(a, c).
support(d,c).
support(b,c).
}).


#pos({out(a), out(b), out(c), in(d)},
     {in(a), in(b), in(c), out(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a, b).
att(a, c).
support(d,c).
support(b,c).
}).

#pos({out(a), out(b), out(c), out(d)},
     {in(a), in(b), in(c), in(d)},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a, b).
att(a, c).
support(d,c).
support(b,c).
}).

#neg({in(a), in(b), out(c), out(d)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b).
att(b,a).
att(b,c).
support(a,c).
support(d,b).
}).

#neg({out(a), in(b), in(c), out(d)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b).
att(b,a).
att(b,c).
support(a,c).
support(d,b).
}).

#neg({out(a), out(b), in(c), out(d)},
     {},{
arg(a).
arg(b).
arg(c).
arg(d).
att(a,b).
att(b,a).
att(b,c).
support(a,c).
support(d,b).
}).

% Definitions

support(X,Z) :- support(X,Y), support(Y,Z).

supported(X) :- support(Y,X), in(Y).

defeat(X,Y) :- att(Z,Y), support(X,Z). 
defeat(X,Y) :- att(X,Z), support(Z,Y). 
defeat(X,Y) :- att(X,Y).

defeated(X) :- in(Y), defeat(Y,X).

not_defended(X) :- defeat(Y,X), not defeated(Y).

% Mode declarations

#modeh(in(var(arg))).
#modeh(out(var(arg))).

#modeb(in(var(arg))).
#modeb(out(var(arg))).
#modeb(arg(var(arg)), (positive)).
#modeb(att(var(arg), var(arg))).
#modeb(supported(var(arg))).
#modeb(defeated(var(arg))).
#modeb(not_defended(var(arg))).

#maxv(2). 
