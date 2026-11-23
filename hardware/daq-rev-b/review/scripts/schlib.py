import sexp, math
from sexp import find, find1, pval
def lib_pins(libsym):
    """return {number:(x,y,name,unit)} from embedded lib symbol (lib coords, y up)"""
    pins={}
    for sub in find(libsym,'symbol'):
        nm=str(sub[1]); parts=nm.rsplit('_',2); unit=int(parts[-2]) if len(parts)>=3 and parts[-2].isdigit() else 0
        for p in find(sub,'pin'):
            at=find1(p,'at'); num=str(find1(p,'number')[1]); name=str(find1(p,'name')[1])
            pins[num]=(float(at[1]),float(at[2]),name,unit)
    return pins
def xform(sym, x, y):
    at=find1(sym,'at'); ax,ay=float(at[1]),float(at[2]); r=int(float(at[3])) if len(at)>3 else 0
    m=find1(sym,'mirror'); m=str(m[1]) if m else None
    px,py=x,-y
    if m=='x': py=-py
    if m=='y': px=-px
    # rotate (screen y-down), KiCad positive angle = CCW on screen
    for _ in range((r//90)%4):
        px,py=py,-px
    return round(ax+px,3), round(ay+py,3)
def pin_positions(e):
    libs={str(s[1]):s for s in find(find1(e,'lib_symbols'),'symbol')}
    out={}
    for s in find(e,'symbol'):
        lid=str(find1(s,'lib_id')[1]); ref=pval(s,'Reference')
        for num,(x,y,name,u) in lib_pins(libs[lid]).items():
            out[(ref,num)]=(xform(s,x,y),name)
    return out
