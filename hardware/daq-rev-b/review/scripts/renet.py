import sys; sys.path.insert(0,'/workspace/pcb/tools')
import pcbnew, sexp
from sexp import find, find1
n=sexp.parse(open('/tmp/revb.net').read())
padnet={}
for net in find(find1(n,'nets'),'net'):
    name=str(find1(net,'name')[1])
    for node in find(net,'node'): padnet[(str(find1(node,'ref')[1]),str(find1(node,'pin')[1]))]=name
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
FPS=list(b.GetFootprints()); bad=0
for f in FPS:
    ref=f.GetReference()
    for p in list(f.Pads()):
        if p.GetNumber()=='': continue
        want=padnet.get((ref,p.GetNumber()))
        if want is None: continue
        if p.GetNetname()!=want:
            ni=b.FindNet(want)
            if ni is None:
                ni=pcbnew.NETINFO_ITEM(b,want); b.Add(ni)
            p.SetNet(ni); bad+=1
print('pads re-netted',bad)
zs=list(b.Zones()); pcbnew.ZONE_FILLER(b).Fill(zs); pcbnew.SaveBoard(PCB,b)
b=pcbnew.LoadBoard(PCB)
for ref in ('Q3','Q7'):
    f=b.FindFootprintByReference(ref); r=f.Reference(); o=b.FindFootprintByReference('Q1').Reference()
    q1=b.FindFootprintByReference('Q1')
    r.SetPosition(f.GetPosition()+(o.GetPosition()-q1.GetPosition()))
pcbnew.SaveBoard(PCB,b)
