import sys, csv, re, json, collections
sys.path.insert(0,'/workspace/pcb/tools')
import sexp, jlc
from sexp import find, find1
D="/workspace/pcb/DAQ/DAQ Rev B"
n=sexp.parse(open('/tmp/revb.net').read())
comps=[]
for c in find(find1(n,'components'),'comp'):
    fields={str(find1(f,'name')[1]):(str(f[2]) if len(f)>2 else '') for f in find(find1(c,'fields'),'field')}
    comps.append(dict(ref=str(find1(c,'ref')[1]),value=str(find1(c,'value')[1]),fp=str(find1(c,'footprint')[1]),**{k:fields.get(k,'') for k in ('LCSC','MPN','Manufacturer')}))
EXCL={'U1','H1','H2','H3','H4','SJ1','SJ2','SJ3'}   # Teensy 4.1: consigned / hand-solder on sockets
def natkey(r): m=re.match(r'([A-Z]+)(\d+)',r); return (m.group(1),int(m.group(2)))
groups=collections.OrderedDict()
for c in sorted(comps,key=lambda c:natkey(c['ref'])):
    if c['ref'] in EXCL: continue
    k=(c['fp'].split(':')[1],c['LCSC'])
    if c['ref'].startswith('J'): c=dict(c,value=c['MPN']+(' Phoenix MPT 2.54mm terminal' if 'MPT' in c['fp'] else ' 5.08mm terminal block 24A'))
    groups.setdefault(k,dict(refs=[],**c))['refs'].append(c['ref'])
# live stock
info={}
for k,g in groups.items():
    code=g['LCSC']
    try: info[code]=jlc.detail(code)
    except Exception as e: info[code]={'err':str(e)}
with open(f"{D}/fab/DAQ_RevB_BOM_JLCPCB.csv","w",newline='') as f:
    w=csv.writer(f); w.writerow(['Comment','Designator','Footprint','LCSC'])
    for k,g in groups.items(): w.writerow([g['value'],','.join(g['refs']),k[0],g['LCSC']])
with open(f"{D}/fab/DAQ_RevB_BOM_full.csv","w",newline='') as f:
    w=csv.writer(f); w.writerow(['Qty','Designator','Value','Footprint','LCSC','MPN','Manufacturer','JLC library type','JLC stock (live)','Unit price USD (qty1 tier)','JLC description'])
    for k,g in groups.items():
        i=info.get(g['LCSC'],{})
        lt={'base':'Basic','expand':'Extended'}.get(i.get('componentLibraryType'),i.get('componentLibraryType',''))
        w.writerow([len(g['refs']),','.join(g['refs']),g['value'],k[0],g['LCSC'],g['MPN'],g['Manufacturer'],lt,i.get('stockCount',''),i.get('price1',''),i.get('describe','')])
    w.writerow([2,'U1 (sockets)','Teensy 4.1 + 2x HC-PM254-8.5H-1x24PZ female header','teensy:Teensy41','C41376163 (sockets)','Teensy 4.1','PJRC','Consigned / hand-solder','','',''])
json.dump(info,open('/workspace/pcb/tools/stock_snapshot.json','w'),indent=1)
# CPL with rotation corrections (matthewlai/JLCKicadTools DB)
ROT=[(r'^SOT-23',-90),(r'^TSSOP-',270),(r'^SOIC-',270),(r'^CP_Elec_6\.3x7\.7',180)]
fpmap={c['ref']:c['fp'].split(':')[1] for c in comps}
rows=[]
for r in csv.DictReader(open('/tmp/pos.csv')):
    ref=r['Ref']
    if ref in EXCL: continue
    fpn=fpmap[ref]; corr=0
    for pat,v in ROT:
        if re.match(pat,fpn): corr=v;break
    rot=(float(r['Rot'])+corr)%360
    rows.append([ref,f"{float(r['PosX']):.4f}mm",f"{float(r['PosY']):.4f}mm",'Top' if r['Side']=='top' else 'Bottom',f"{rot:g}",fpn,corr,r['Rot']])
rows.sort(key=lambda x:natkey(x[0]))
with open(f"{D}/fab/DAQ_RevB_CPL_JLCPCB.csv","w",newline='') as f:
    w=csv.writer(f); w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for x in rows: w.writerow(x[:5])
with open('/workspace/pcb/tools/cpl_debug.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['ref','x','y','layer','jlc_rot','fp','corr','kicad_rot']); w.writerows(rows)
for k,g in groups.items():
    i=info.get(g['LCSC'],{}); print(f"{','.join(g['refs'])[:40]:40s} {g['LCSC']:10s} {i.get('componentLibraryType','?'):7s} stock={i.get('stockCount','?')} ${i.get('price1','?')} {i.get('componentModelEn','')}")
