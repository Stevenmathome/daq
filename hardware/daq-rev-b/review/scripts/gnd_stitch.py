import pcbnew, math, sys
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
MM=pcbnew.FromMM; toMM=pcbnew.ToMM
gnd=b.FindNet('GND')
VIA_D=0.6; VIA_DR=0.3; CLR=0.25
# obstacles: (layerset, shape) for all non-GND copper + holes
obs=[]
for fp in b.GetFootprints():
    for p in fp.Pads():
        obs.append(('pad',p))
for t in b.GetTracks(): obs.append(('trk',t))
edge=b.GetBoardEdgesBoundingBox()
def ok(x,y,allow_gnd_pad=None):
    pos=pcbnew.VECTOR2I(MM(x),MM(y))
    r=VIA_D/2
    # board edge margin
    if x<12+1.2 or x>150.5-1.2 or y<13+1.2 or y>144.5-1.2: return False
    for kind,o in obs:
        same = o.GetNetCode()==gnd.GetNetCode()
        if kind=='pad':
            # holes always need hole clearance
            if o.HasHole():
                d=o.GetEffectiveShape(pcbnew.F_Cu).GetClearance if False else None
            for lay in (pcbnew.F_Cu,pcbnew.B_Cu):
                if not o.IsOnLayer(lay): continue
                sh=o.GetEffectiveShape(lay)
                need = (0.25 if same else CLR)
                if sh.Collide(pos, MM(r+need)): return False
        else:
            if o.GetClass()=='PCB_VIA':
                if (o.GetPosition()-pos).EuclideanNorm() < MM(r+o.GetWidth(pcbnew.F_Cu)/2e6+0.25): return False
                continue
            need = 0.0 if same else CLR
            if same: need=0.1
            sh=o.GetEffectiveShape(o.GetLayer())
            if sh.Collide(pos, MM(r+need)): return False
    # keep out of non-GND zones (12V / VIN pours)
    for z in b.Zones():
        if z.GetNetCode()!=gnd.GetNetCode() and z.GetIsRuleArea()==False:
            if z.Outline().Collide(pos, MM(r+0.3)): return False
    return True
added=[]
def addvia(x,y):
    v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y))); v.SetWidth(pcbnew.F_Cu,MM(VIA_D)); v.SetWidth(pcbnew.B_Cu,MM(VIA_D)); v.SetDrill(MM(VIA_DR)); v.SetNet(gnd); b.Add(v)
    obs.append(('trk',v)); added.append((x,y))
# 1) fanout: each SMD GND pad on F.Cu
cnt=0
FANOUT=len(sys.argv)>1 and sys.argv[1]=='fanout'
for fp in (b.GetFootprints() if FANOUT else []):
    for p in fp.Pads():
        if p.GetNetCode()!=gnd.GetNetCode() or p.HasHole(): continue
        if not p.IsOnLayer(pcbnew.F_Cu): continue
        cx,cy=toMM(p.GetPosition().x),toMM(p.GetPosition().y)
        sx,sy=toMM(p.GetBoundingBox().GetWidth())/2,toMM(p.GetBoundingBox().GetHeight())/2
        done=False
        for dist in (0.55,0.8,1.1,1.5,2.0):
            for ang in range(0,360,30):
                a=math.radians(ang)
                x=cx+math.cos(a)*(sx+dist); y=cy+math.sin(a)*(sy+dist)
                x=round(x,3); y=round(y,3)
                if not ok(x,y): continue
                t=pcbnew.PCB_TRACK(b); t.SetStart(p.GetPosition()); t.SetEnd(pcbnew.VECTOR2I(MM(x),MM(y))); t.SetWidth(MM(0.4)); t.SetLayer(pcbnew.F_Cu); t.SetNet(gnd)
                tsh=t.GetEffectiveShape(); bad=False
                for kind,o in obs:
                    if o.GetNetCode()==gnd.GetNetCode(): continue
                    if o.IsOnLayer(pcbnew.F_Cu) and o.GetEffectiveShape(pcbnew.F_Cu).Collide(tsh, MM(0.2)): bad=True;break
                if bad: continue
                addvia(x,y); b.Add(t); obs.append(('trk',t)); done=True; cnt+=1; break
            if done: break
        if not done: print('no fanout for',fp.GetReference(),p.GetNumber())
print('fanout vias',cnt)
# 2) stitching grid
g=0
y=16.0
while y<142:
    x=15.0
    while x<148:
        if ok(x,y): addvia(x,y); g+=1
        x+=7.0
    y+=7.0
print('grid vias',g)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB,b)
