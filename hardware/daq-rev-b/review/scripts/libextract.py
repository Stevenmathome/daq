import sexp
from sexp import find, find1
_cache={}
def get(lib, name):
    path=f"/usr/share/kicad/symbols/{lib}.kicad_sym"
    if path not in _cache: _cache[path]=sexp.parse(open(path).read())
    root=_cache[path]
    for s in find(root,'symbol'):
        if str(s[1])==name:
            if find1(s,'extends'): raise ValueError("extends")
            s2=[x for x in s]; s2[1]=sexp.Q(f"{lib}:{name}")
            return s2
    raise KeyError(name)
