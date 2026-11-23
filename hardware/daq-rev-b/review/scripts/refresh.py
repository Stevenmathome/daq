import pcbnew
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
IO=pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
KEEP=[]
refs=['Q%d'%i for i in range(1,8)]+['U3','U4','U5','U6','U7','U8']
for ref in refs:
    f=b.FindFootprintByReference(ref); KEEP.append(f)
    lib,name=f.GetFPIDAsString().split(':')
    nf=IO.FootprintLoad(f"/usr/share/kicad/footprints/{lib}.pretty",name); nf.thisown=0; KEEP.append(nf)
    nf.SetFPID(pcbnew.LIB_ID(lib,name))
    nf.SetPosition(f.GetPosition()); nf.SetOrientation(f.GetOrientation())
    nf.SetReference(ref); nf.SetValue(f.GetValue()); nf.SetPath(f.GetPath())
    nf.Reference().SetPosition(f.Reference().GetPosition()); nf.Reference().SetTextAngle(f.Reference().GetTextAngle())
    nf.Value().SetPosition(f.Value().GetPosition())
    for k in ('LCSC','MPN','Manufacturer'):
        fld=pcbnew.PCB_FIELD(nf,len(nf.GetFields()),k); fld.SetText(f.GetFieldText(k)); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); nf.AddField(fld)
    nets={p.GetNumber():p.GetNetCode() for p in f.Pads()}
    for p in nf.Pads(): p.SetNetCode(nets[p.GetNumber()])
    b.Remove(f); b.Add(nf)
zs=list(b.Zones()); pcbnew.ZONE_FILLER(b).Fill(zs)
pcbnew.SaveBoard(PCB,b); print('refreshed',len(refs))
