import pcbnew
MM=pcbnew.FromMM; T=pcbnew.ToMM
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
FPS=list(b.GetFootprints())
# library pad comparison
IO=pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
for ref in ('Q1','U3','U6'):
    f=b.FindFootprintByReference(ref); lib,name=f.GetFPIDAsString().split(':')
    lf=IO.FootprintLoad(f"/usr/share/kicad/footprints/{lib}.pretty",name)
    a=sorted((p.GetNumber(),p.GetFPRelativePosition().x,p.GetFPRelativePosition().y,p.GetSize().x,p.GetSize().y,p.GetShape()) for p in f.Pads())
    c=sorted((p.GetNumber(),p.GetFPRelativePosition().x,p.GetFPRelativePosition().y,p.GetSize().x,p.GetSize().y,p.GetShape()) for p in lf.Pads())
    print(ref,name,'pads identical to library' if a==c else 'PAD DIFF')
    if a!=c:
        for x,y in zip(a,c):
            if x!=y: print('  board',x,'lib',y)
# silkscreen ref placement for small parts
boxes=[]
for f in FPS:
    for p in f.Pads():
        bb=p.GetBoundingBox(); bb.Inflate(MM(0.2)); boxes.append(bb)
    for g in f.GraphicalItems():
        if g.GetLayer()==pcbnew.F_SilkS and g.GetClass()!='PCB_TEXT':
            boxes.append(g.GetBoundingBox())
for d in b.GetDrawings():
    if d.GetLayer()==pcbnew.F_SilkS: boxes.append(d.GetBoundingBox())
targets=[f for f in FPS if f.GetReference() in (['C%d'%i for i in range(1,27)]+['D8','D9','R35','Q8','F1'])]
others=[f.Reference().GetBoundingBox() for f in FPS if f not in targets and f.Reference().IsVisible()]
boxes+=others
edge=pcbnew.BOX2I(pcbnew.VECTOR2I(MM(12.8),MM(13.8)),pcbnew.VECTOR2I(MM(137.0),MM(129.9)))
def inter(a,c): return a.Intersects(c)
hidden=[]
for f in targets:
    r=f.Reference(); r.SetTextSize(pcbnew.VECTOR2I(MM(0.8),MM(0.8))); r.SetTextThickness(MM(0.15)); r.SetVisible(True)
    fb=f.GetBoundingBox(False,False); cx,cy=fb.GetCenter().x,fb.GetCenter().y
    w,h=fb.GetWidth()/2,fb.GetHeight()/2
    placed=False
    for ang in (0,90):
        r.SetTextAngleDegrees(ang)
        for dx,dy in ((0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)):
            for gap in (0.6,1.0,1.5,2.2):
                tb=r.GetBoundingBox()
                tw,th=tb.GetWidth()/2,tb.GetHeight()/2
                x=cx+dx*(w+tw+MM(gap)-MM(0.5)); y=cy+dy*(h+th+MM(gap)-MM(0.5))
                r.SetPosition(pcbnew.VECTOR2I(int(x),int(y)))
                tb=r.GetBoundingBox()
                if not edge.Contains(tb): continue
                if any(inter(tb,bx) for bx in boxes): continue
                boxes.append(tb); placed=True; break
            if placed: break
        if placed: break
    if not placed:
        r.SetVisible(False); hidden.append(f.GetReference())
print('hidden refs (kept on F.Fab/assembly drawing):',hidden)
pcbnew.SaveBoard(PCB,b)
