import pcbnew
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB); T=pcbnew.ToMM
g=b.FindNet('GND').GetNetCode()
nodes=[]; par={}
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
def union(a,c): par[find(a)]=find(c)
polys=[]
zones=list(b.Zones())
for zi,z in enumerate(zones):
    if z.GetNetCode()!=g: continue
    for lay in (pcbnew.F_Cu,pcbnew.B_Cu):
        if not z.IsOnLayer(lay): continue
        fp=z.GetFilledPolysList(lay)
        for i in range(fp.OutlineCount()):
            sp=pcbnew.SHAPE_POLY_SET(); sp.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)): sp.AddHole(fp.Hole(i,h))
            key=('Z',z.GetZoneName() or 'GND_bot',lay,i); par[key]=key; polys.append((key,lay,sp,fp.Outline(i).BBox()))
items=[]
FPS=list(b.GetFootprints())
for f in FPS:
    for p in list(f.Pads()):
        if p.GetNetCode()==g: items.append((('P',f.GetReference(),p.GetNumber()),p))
for t in list(b.GetTracks()):
    if t.GetNetCode()==g: items.append((('T' if t.GetClass()=='PCB_TRACK' else 'V',T(t.GetStart().x),T(t.GetStart().y)),t))
for k,o in items: par[k]=k
for k,o in items:
    for lay in (pcbnew.F_Cu,pcbnew.B_Cu):
        if not o.IsOnLayer(lay): continue
        sh=o.GetEffectiveShape(lay)
        for pk,pl,sp,bb in polys:
            if pl!=lay: continue
            if sp.Collide(sh,0): union(k,pk)
        for k2,o2 in items:
            if k2<=k or not o2.IsOnLayer(lay): continue
            if o2.GetEffectiveShape(lay).Collide(sh,0): union(k,k2)
cl={}
for k in par: cl.setdefault(find(k),[]).append(k)
print('clusters',len(cl))
for r,m in sorted(cl.items(), key=lambda x:len(x[1])):
    print(len(m), m[:8])
