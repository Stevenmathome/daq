import pcbnew
MM=pcbnew.FromMM; T=pcbnew.ToMM
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
net=b.FindNet('+12V'); nc=net.GetNetCode()
FPS=list(b.GetFootprints())
pads=[p for f in FPS for p in f.Pads()]
trk=list(b.GetTracks())
def ok(x,y):
    pos=pcbnew.VECTOR2I(MM(x),MM(y))
    for p in pads:
        need=0.35 if p.GetNetCode()!=nc else (0.3 if p.HasHole() else -1)
        if need<0: continue
        for lay in (pcbnew.F_Cu,pcbnew.B_Cu):
            if p.IsOnLayer(lay) and p.GetEffectiveShape(lay).Collide(pos,MM(0.4+need)): return False
    for t in trk:
        if t.GetClass()=='PCB_VIA':
            if (t.GetPosition()-pos).EuclideanNorm()<MM(0.8+0.3): return False
        elif t.GetNetCode()!=nc and t.GetEffectiveShape().Collide(pos,MM(0.4+0.35)): return False
    return True
n=0
for x in (139.2,140.4,141.6,142.4):
    for y in (137.6,138.8,140.0,141.2,142.4):
        if ok(x,y):
            v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y))); v.SetWidth(pcbnew.F_Cu,MM(0.8)); v.SetWidth(pcbnew.B_Cu,MM(0.8)); v.SetDrill(MM(0.4)); v.SetNet(net); b.Add(v); trk.append(v); n+=1
print('added 12V stitch vias',n, 'total 12V vias', sum(1 for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetCode()==nc))
zs=list(b.Zones()); pcbnew.ZONE_FILLER(b).Fill(zs); pcbnew.SaveBoard(PCB,b)
