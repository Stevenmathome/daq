# Minimal KiCad s-expression parser/serializer preserving quoted strings.
import re
class Q(str):
    """quoted string atom"""
    pass
_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)
def parse(text):
    stack=[[]]; pos=0; n=len(text)
    while pos<n:
        m=_tok.match(text,pos)
        if not m:
            if text[pos:].strip()=="" : break
            raise ValueError("parse error at %d: %r"%(pos,text[pos:pos+50]))
        pos=m.end()
        if m.group(1): stack.append([])
        elif m.group(2):
            l=stack.pop(); stack[-1].append(l)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"','"').replace('\\\\','\\')) if False else Q(m.group(3)))
        else:
            stack[-1].append(m.group(4))
    return stack[0][0]
def _atom(a):
    if isinstance(a,Q): return '"'+str(a)+'"'
    return str(a)
def dump(e, ind=0):
    if not isinstance(e,list): return _atom(e)
    if all(not isinstance(x,list) for x in e):
        return "("+" ".join(_atom(x) for x in e)+")"
    s="("+" ".join(_atom(x) for x in e if not isinstance(x,list)) if not isinstance(e[0],list) else "("
    # keep order: head atoms then children in order
    parts=[]
    head=[]
    for x in e:
        parts.append(x)
    out="("
    first=True
    for x in parts:
        if isinstance(x,list):
            out+="\n"+"\t"*(ind+1)+dump(x,ind+1)
        else:
            out+=("" if first else " ")+_atom(x)
        first=False
    out+="\n"+"\t"*ind+")"
    return out
def head(e): return e[0] if isinstance(e,list) and e else None
def find(e,name): 
    return [x for x in e if isinstance(x,list) and x and x[0]==name]
def find1(e,name):
    r=find(e,name); return r[0] if r else None
def prop(sym,name):
    for p in find(sym,'property'):
        if p[1]==name: return p
    return None
def pval(sym,name):
    p=prop(sym,name); return str(p[2]) if p else None
