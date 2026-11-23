import pcbnew
MM=pcbnew.FromMM
PCB="/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_pcb"
b=pcbnew.LoadBoard(PCB)
for z in list(b.Zones()):
    if z.GetZoneName()=='VIN_RAW_pour': b.Delete(z)
z=pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet('/VIN_RAW')); z.SetAssignedPriority(10); z.SetZoneName('VIN_RAW_pour')
ol=z.Outline(); ol.NewOutline()
for x,y in [(97.0,134.2),(104.7,134.2),(104.7,138.1),(120.0,138.1),(120.0,143.4),(97.0,143.4)]: ol.Append(MM(x),MM(y))
z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); b.Add(z)
zs=list(b.Zones()); pcbnew.ZONE_FILLER(b).Fill(zs)
fp=z.GetFilledPolysList(pcbnew.F_Cu)
# narrowest vertical cross-section of copper between x=98 and 118 (current flows horizontally in the strip)
minw=99; at=None
for xi in range(980,1180,2):
    x=xi/10; w=0
    for yi in range(1342,1435):
        if fp.Contains(pcbnew.VECTOR2I(MM(x),MM(yi/10))): w+=0.1
    if w<minw: minw,at=w,x
print('VIN_RAW outlines',fp.OutlineCount(),'min vertical copper (mm)',round(minw,2),'at x',at)
pcbnew.SaveBoard(PCB,b)
