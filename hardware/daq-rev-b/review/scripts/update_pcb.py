import pcbnew, sexp, json
from sexp import find, find1
P="/workspace/pcb/DAQ/DAQ Rev B"
PCB=f"{P}/DAQ Rev B.kicad_pcb"
n=sexp.parse(open('/tmp/revb.net').read())
comps={}
for c in find(find1(n,'components'),'comp'):
    ref=str(find1(c,'ref')[1])
    fields={str(find1(f,'name')[1]):(str(f[2]) if len(f)>2 else '') for f in find(find1(c,'fields'),'field')}
    comps[ref]=dict(value=str(find1(c,'value')[1]), fp=str(find1(c,'footprint')[1]) if find1(c,'footprint') else '',
                    tstamp=str(find1(c,'tstamps')[1]), fields=fields)
padnet={}
for net in find(find1(n,'nets'),'net'):
    name=str(find1(net,'name')[1])
    for node in find(net,'node'):
        padnet[(str(find1(node,'ref')[1]),str(find1(node,'pin')[1]))]=name

b=pcbnew.LoadBoard(PCB)
def getnet(name):
    ni=b.FindNet(name)
    if ni is None:
        ni=pcbnew.NETINFO_ITEM(b,name); b.Add(ni)
    return ni
IO=pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
KEEP=[]
FPDIR="/usr/share/kicad/footprints"
def loadfp(fpid):
    lib,name=fpid.split(':')
    if lib=='teensy.pretty-master': path=f"{P}/lib/teensy.pretty"
    else: path=f"{FPDIR}/{lib}.pretty"
    f=IO.FootprintLoad(path,name); f.thisown=0; KEEP.append(f); f.SetFPID(pcbnew.LIB_ID(lib,name)); return f

# placement for new parts / moved parts: ref -> (x,y,rot)
PLACE=json.load(open('/workspace/pcb/tools/placement.json'))
# 1) remove all tracks & vias (full re-route with netclasses)
for t in list(b.GetTracks()): b.Delete(t)
existing=set(f.GetReference() for f in b.GetFootprints())
# 2) swap footprints whose lib id changed
for ref,c in comps.items():
    if ref not in existing: continue
    f=b.FindFootprintByReference(ref)
    cur=f.GetFPIDAsString()
    if cur!=c['fp']:
        nf=loadfp(c['fp'])
        nf.SetPosition(f.GetPosition()); nf.SetOrientation(f.GetOrientation())
        nf.SetReference(ref); nf.SetValue(c['value']); nf.SetPath(f.GetPath())
        nf.Reference().SetLayer(f.Reference().GetLayer())
        b.Remove(f); KEEP.append(f); b.Add(nf)
        print('swapped',ref,cur,'->',c['fp'])
# 3) add new footprints
for ref,c in comps.items():
    if ref in existing: continue
    nf=loadfp(c['fp']); nf.SetReference(ref); nf.SetValue(c['value'])
    nf.SetPath(pcbnew.KIID_PATH('/'+c['tstamp']))
    b.Add(nf); existing.add(ref); print('added',ref,c['fp'])
# 4) positions, values, fields, nets
for ref in sorted(existing):
    f=b.FindFootprintByReference(ref)
    if ref not in comps: print('EXTRA on PCB',ref); continue
    c=comps[ref]
    f.SetValue(c['value'])
    if ref in PLACE:
        x,y,r=PLACE[ref]; f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))); f.SetOrientationDegrees(r)
    for k in ('LCSC','MPN','Manufacturer'):
        v=c['fields'].get(k,'')
        fld=f.GetFieldByName(k)
        if fld is None:
            fld=pcbnew.PCB_FIELD(f,len(f.GetFields()),k); fld.SetLayer(pcbnew.F_Fab); fld.SetVisible(False); f.AddField(fld)
        fld.SetText(v); fld.SetVisible(False)
    for pad in f.Pads():
        num=pad.GetNumber()
        if num=='' : continue
        name=padnet.get((ref,num))
        if name is None:
            pad.SetNetCode(0)
        else:
            pad.SetNet(getnet(name))
b.BuildConnectivity()
pcbnew.SaveBoard(PCB,b)
print('saved; footprints',len(list(b.GetFootprints())))
