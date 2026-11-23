import sexp, schlib, libextract, uuid, copy, json, re
from sexp import Q, find, find1, pval, prop
SCH='/workspace/pcb/DAQ/DAQ Rev B/DAQ Rev B.kicad_sch'
ROOT='/177402f4-82fb-44da-be7d-55fb471d0f6e'
e=sexp.parse(open(SCH).read())
U=lambda: Q(str(uuid.uuid4()))
libs=find1(e,'lib_symbols')
def has_lib(name): return any(str(s[1])==name for s in find(libs,'symbol'))
def add_lib(s):
    if not has_lib(str(s[1])): libs.append(s)

# ---------- custom AO4407A P-FET (SO-8: S=1,2,3 G=4 D=5-8) ----------
def make_pfet():
    s=copy.deepcopy(libextract.get('Transistor_FET','Q_PMOS_GSD'))
    s[1]=Q('DAQ_RevB:AO4407A')
    for p in find(s,'property'):
        if p[1]=='Value': p[2]=Q('AO4407A')
        if p[1]=='Footprint': p[2]=Q('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
        if p[1]=='Datasheet': p[2]=Q('https://www.lcsc.com/datasheet/C2841482.pdf')
        if p[1]=='Description': p[2]=Q('-30V -14A P-channel MOSFET, SO-8 (S=1,2,3 G=4 D=5-8)')
        if p[1]=='ki_fp_filters': p[2]=Q('SOIC*3.9x4.9mm*P1.27mm*')
    for sub in find(s,'symbol'):
        sub[1]=Q(str(sub[1]).replace('Q_PMOS_GSD','AO4407A'))
        newpins=[]
        for p in find(sub,'pin'):
            num=find1(p,'number'); n=str(num[1])
            if n=='1': num[1]=Q('4')
            elif n=='2':
                num[1]=Q('1')
                for extra in ('2','3'):
                    q=copy.deepcopy(p); find1(q,'number')[1]=Q(extra); q.insert(4,['hide','yes']); newpins.append(q)
            elif n=='3':
                num[1]=Q('5')
                for extra in ('6','7','8'):
                    q=copy.deepcopy(p); find1(q,'number')[1]=Q(extra); q.insert(4,['hide','yes']); newpins.append(q)
        sub.extend(newpins)
    return s
pfet=make_pfet()
open('/tmp/pfet_sym.sexp','w').write(sexp.dump(pfet))
add_lib(pfet)
for lib,n in [('Device','Polyfuse'),('Device','C'),('Device','C_Polarized'),('Device','D_Zener'),('Device','D_Schottky'),('power','PWR_FLAG')]:
    add_lib(libextract.get(lib,n))

def eff(size=1.27, hide=False, justify=None):
    x=['effects',['font',['size',str(size),str(size)]]]
    if justify: x.append(['justify']+justify.split())
    if hide: x.append(['hide','yes'])
    return x
def mkprop(name,val,x,y,hide=True,ang=0):
    return ['property',Q(name),Q(val),['at',str(x),str(y),str(ang)],eff(hide=hide)]

pwr_n=[int(re.sub(r'\D','',pval(s,'Reference'))) for s in find(e,'symbol') if pval(s,'Reference').startswith('#PWR')]
flg_n=[0]
counter={'pwr':max(pwr_n)+1,'flg':1}
new_syms=[]
def place(lib_id, ref, value, x, y, rot=0, fp='', fields=None, in_bom=True, mirror=None, ref_off=(2.54,-1.27), val_off=(2.54,1.27)):
    libsym=[s for s in find(libs,'symbol') if str(s[1])==lib_id][0]
    pins=schlib.lib_pins(libsym)
    s=['symbol',['lib_id',Q(lib_id)],['at',str(x),str(y),str(rot)]]
    if mirror: s.append(['mirror',mirror])
    s+= [['unit','1'],['exclude_from_sim','no'],['in_bom','yes' if in_bom else 'no'],['on_board','yes'],['dnp','no'],['uuid',U()]]
    hide_ref = ref.startswith('#')
    s.append(mkprop('Reference',ref,x+ref_off[0],y+ref_off[1],hide=hide_ref))
    s.append(mkprop('Value',value,x+val_off[0],y+val_off[1],hide=False))
    s.append(mkprop('Footprint',fp,x,y))
    s.append(mkprop('Datasheet','~',x,y))
    s.append(mkprop('Description','',x,y))
    for k,v in (fields or {}).items(): s.append(mkprop(k,v,x,y))
    for num in pins: s.append(['pin',Q(num),['uuid',U()]])
    s.append(['instances',['project',Q(''),['path',Q(ROOT),['reference',Q(ref)],['unit','1']]]])
    e.append(s); new_syms.append(s)
    return {n:schlib.xform(s,px,py) for n,(px,py,_,_) in pins.items()}
def power(net, x, y, rot=0):
    ref=f"#PWR0{counter['pwr']}"; counter['pwr']+=1
    place(f'power:{net}', ref, net, x, y, rot, in_bom=False, ref_off=(0,6), val_off=(0,-3.8 if net!='GND' else 3.8))
def flag(x,y):
    ref=f"#FLG0{counter['flg']:02d}"; counter['flg']+=1
    place('power:PWR_FLAG', ref, 'PWR_FLAG', x, y, 0, in_bom=False, ref_off=(0,-6), val_off=(0,-3.8))
def label(name,x,y,ang=0):
    just='left bottom' if ang==0 else 'right bottom'
    e.append(['label',Q(name),['at',str(x),str(y),str(ang)],eff(justify=just),['uuid',U()]])
def noconn(x,y):
    e.append(['no_connect',['at',str(x),str(y)],['uuid',U()]])

# ---------- part database: footprint, LCSC, MPN, manufacturer ----------
PARTS={
 'R1k':  ('Resistor_SMD:R_0603_1608Metric','C21190','0603WAF1001T5E','UNI-ROYAL'),
 'R10k': ('Resistor_SMD:R_0603_1608Metric','C25804','0603WAF1002T5E','UNI-ROYAL'),
 'R20k': ('Resistor_SMD:R_0603_1608Metric','C4184','0603WAF2002T5E','UNI-ROYAL'),
 'R100k':('Resistor_SMD:R_0603_1608Metric','C25803','0603WAF1003T5E','UNI-ROYAL'),
 'C100n':('Capacitor_SMD:C_0603_1608Metric','C14663','CC0603KRX7R9BB104','YAGEO'),
 'C10u': ('Capacitor_SMD:C_0805_2012Metric','C15850','CL21A106KAYNNNE','Samsung'),
 'C100u':('Capacitor_SMD:CP_Elec_6.3x7.7','C4747965','RST100UF25V006','KNSCHA'),
 'M7':   ('Diode_SMD:D_SMA','C95872','M7','MDD'),
 'AO3400A':('Package_TO_SOT_SMD:SOT-23','C20917','AO3400A','Alpha & Omega'),
 'AO4407A':('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm','C2841482','AO4407A','UMW'),
 'BZT52C15':('Diode_SMD:D_SOD-123','C2104','BZT52C15','JSCJ'),
 'B5819W':('Diode_SMD:D_SOD-123','C8598','B5819W SL','JSCJ'),
 'PTC5A':('Fuse:Fuse_2920_7451Metric','C910846','BSMD2920-500-16V','BHFUSE'),
 'HX711':('Package_SO:SOIC-16_3.9x9.9mm_P1.27mm','C43656','HX711','Avia Semicon'),
 'MAX31856':('Package_SO:TSSOP-14_4.4x5mm_P0.65mm','C116632','MAX31856MUD+','Analog Devices/Maxim'),
 'R78':  ('Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT','C22371890','R-78E5.0-1.0','YLPTEC (pin-compatible w/ RECOM R-78E5.0-1.0)'),
 'T2':   ('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-2-2.54_1x02_P2.54mm_Horizontal','C3029316','1725656','Phoenix Contact'),
 'T3':   ('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-3-2.54_1x03_P2.54mm_Horizontal','C5288763','1725669','Phoenix Contact'),
 'T4':   ('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-4-2.54_1x04_P2.54mm_Horizontal','C3816889','1725672','Phoenix Contact'),
 'TEENSY':('teensy.pretty-master:Teensy41','','Teensy 4.1 (PJRC) on 2x HC-PM254-8.5H-1x24PZ sockets C41376163','PJRC'),
}
def setfields(s, key, value=None):
    fp,lcsc,mpn,mfr=PARTS[key]
    p=prop(s,'Footprint'); p[2]=Q(fp)
    if value: prop(s,'Value')[2]=Q(value)
    at=find1(s,'at'); x,y=at[1],at[2]
    for k,v in (('LCSC',lcsc),('MPN',mpn),('Manufacturer',mfr)):
        old=prop(s,k)
        if old: old[2]=Q(v)
        else: s.insert(s.index(find(s,'property')[-1])+1, mkprop(k,v,x,y))

# ---------- 1. existing symbols: fields, footprint fixes, FET flip ----------
for s in find(e,'symbol'):
    ref=pval(s,'Reference'); lid=str(find1(s,'lib_id')[1]); val=pval(s,'Value')
    if ref.startswith('#'): continue
    if lid=='Device:R': setfields(s,{'1k':'R1k','10k':'R10k','20k':'R20k'}[val])
    elif ref=='C1': setfields(s,'C100u','100uF 25V')
    elif ref=='C2': setfields(s,'C10u','10uF 25V')
    elif ref=='C3': setfields(s,'C100n','100nF')
    elif lid=='Diode:1N4007': setfields(s,'M7','M7 (1N4007, SMA)')
    elif lid=='Transistor_FET:AO3400A':
        setfields(s,'AO3400A')
        at=find1(s,'at'); assert find1(s,'mirror')[1]=='y' and at[3]=='0', ref
        s.remove(find1(s,'mirror')); at[3]='180'   # mirror-y -> rot180: swaps D/S, gate unchanged
    elif lid=='Analog_ADC:HX711': setfields(s,'HX711')
    elif lid=='Sensor_Temperature:MAX31856': setfields(s,'MAX31856')
    elif ref=='U2': setfields(s,'R78')
    elif ref=='U1': setfields(s,'TEENSY')
    elif lid.startswith('Connector:Screw_Terminal_01x0'): setfields(s,'T'+lid[-1])
    else: print("UNHANDLED",ref,lid)

# ---------- wire connectivity helper ----------
pts_w=[]
for w in find(e,'wire'):
    xy=find(find1(w,'pts'),'xy'); pts_w.append(((float(xy[0][1]),float(xy[0][2])),(float(xy[1][1]),float(xy[1][2]))))
def onseg(p,a,b):
    (x,y),(x1,y1),(x2,y2)=p,a,b
    if abs((x2-x1)*(y-y1)-(y2-y1)*(x-x1))>1e-6: return False
    return min(x1,x2)-1e-6<=x<=max(x1,x2)+1e-6 and min(y1,y2)-1e-6<=y<=max(y1,y2)+1e-6
def reach(start):
    seen={start}; stack=[start]
    while stack:
        p=stack.pop()
        for a,b in pts_w:
            if onseg(p,a,b) or p in (a,b):
                for q in (a,b):
                    q=(round(q[0],3),round(q[1],3))
                    if q not in seen: seen.add(q); stack.append(q)
    return seen
pp=schlib.pin_positions(e)
def power_syms_at(points, net):
    out=[]
    for s in find(e,'symbol'):
        if str(find1(s,'lib_id')[1])==f'power:{net}':
            at=find1(s,'at'); p=(round(float(at[1]),3),round(float(at[2]),3))
            if p in points: out.append(s)
    return out

# ---------- 2. J16 pin1: +12V -> VIN_RAW ----------
j16p1=pp[('J16','1')][0]; net=reach(j16p1)
ps=power_syms_at(net,'+12V'); assert len(ps)==1, ps
at=find1(ps[0],'at'); e.remove(ps[0]); label('VIN_RAW',float(at[1]),float(at[2]))
# ---------- 3. Teensy VIN: +5V -> TEENSY_VIN ----------
vin=pp[('U1','48')][0]; net=reach(vin)
ps=power_syms_at(net,'+5V'); assert len(ps)==1, ps
at=find1(ps[0],'at'); e.remove(ps[0]); label('TEENSY_VIN',float(at[1]),float(at[2]))
for t in find(e,'text'):
    if 'NEVER HAVE 12VDC' in str(t[1]):
        t[1]=Q('Teensy VIN fed from +5V through Schottky D9. CUT the VIN-VUSB pad on the Teensy (PJRC) so USB and 12V can both be connected.')
# ---------- 4. HX711 DOUT split ----------
dmap={(181.61,43.18):'LoadCell1_DO',(29.21,41.91):'LoadCell1_DO',(259.08,44.45):'LoadCell2_DO',(331.47,45.72):'LoadCell3_DO'}
for l in find(e,'label'):
    if str(l[1])=='LoadCell_DO':
        a=find1(l,'at'); l[1]=Q(dmap[(float(a[1]),float(a[2]))])
for pin,name in (('2','LoadCell2_DO'),('3','LoadCell3_DO')):   # Teensy pad2 = GPIO0, pad3 = GPIO1
    x,y=pp[('U1',pin)][0]; label(name,x,y,180)
# ---------- 5. Teensy extra GND pins ----------
for pin in ('34','47'):
    x,y=pp[('U1',pin)][0]; power('GND',x,y,90)
# ---------- 6. no-connect flags ----------
NC={'U1':['12','15','31','32','33','36','49','50','51','53','54','55','56','57','60','61','62','63','65','66','67'],
    'U3':['2','6','9','10','13'],'U4':['2','6','9','10','13'],'U5':['2','6','9','10','13'],
    'U6':['2','6','7','13'],'U7':['2','6','7','13'],'U8':['2','6','7','13']}
connected=set()
for w in pts_w:
    for p in w: connected.add((round(p[0],3),round(p[1],3)))
for ref,pins in NC.items():
    for n in pins:
        (x,y),name=pp[(ref,n)]
        assert (x,y) not in connected, (ref,n,name)
        noconn(x,y)

# ---------- 7. new circuitry in free right column ----------
CAPMAP={}
X0=365.76
# 12V input: J16 -> F1 -> Q8 (P-FET reverse polarity) -> +12V
p=place('Device:Polyfuse','F1','5A hold PTC',X0,40.64,fp=PARTS['PTC5A'][0],fields={'LCSC':'C910846','MPN':'BSMD2920-500-16V','Manufacturer':'BHFUSE'})
label('VIN_RAW',*p['1']); label('VIN_FUSED',*p['2'])
q=place('DAQ_RevB:AO4407A','Q8','AO4407A',388.62,40.64,fp=PARTS['AO4407A'][0],fields={'LCSC':'C2841482','MPN':'AO4407A','Manufacturer':'UMW'})
label('VIN_FUSED',*q['5']); power('+12V',*q['1']); label('PFET_G',*q['4'],180)
z=place('Device:D_Zener','D8','BZT52C15',408.94,40.64,fp=PARTS['BZT52C15'][0],fields={'LCSC':'C2104','MPN':'BZT52C15','Manufacturer':'JSCJ'})
power('+12V',*z['1']); label('PFET_G',*z['2'])
r=place('Device:R','R35','100k',375.92,58.42,fp=PARTS['R100k'][0],fields={'LCSC':'C25803','MPN':'0603WAF1003T5E','Manufacturer':'UNI-ROYAL'})
label('PFET_G',*r['1']); power('GND',*r['2'])
c=place('Device:C_Polarized','C20','100uF 25V',391.16,58.42,fp=PARTS['C100u'][0],fields={'LCSC':'C4747965','MPN':'RST100UF25V006','Manufacturer':'KNSCHA'})
power('+12V',*c['1']); power('GND',*c['2']); CAPMAP['C20']='12V_BULK'
fx=404.0
flag(fx,55.88); power('+12V',fx,55.88)
flag(fx+8,55.88); power('GND',fx+8,55.88+0)  # GND flag
# Teensy VIN Schottky
d=place('Device:D_Schottky','D9','B5819W',383.54,76.2,fp=PARTS['B5819W'][0],fields={'LCSC':'C8598','MPN':'B5819W SL','Manufacturer':'JSCJ'})
label('TEENSY_VIN',*d['1']); power('+5V',*d['2'])
flag(400.05,76.2); label('TEENSY_VIN',400.05,76.2)
# decoupling caps grid
caps=[('C4','+5V','U3'),('C5','+3V3','U3'),('C6','+5V','U4'),('C7','+3V3','U4'),('C8','+5V','U5'),('C9','+3V3','U5'),
      ('C10','+3V3','U6'),('C11','+3V3','U6'),('C12','+3V3','U7'),('C13','+3V3','U7'),('C14','+3V3','U8'),('C15','+3V3','U8'),
      ('C16','+12V','U2'),('C17','+12V','U2'),('C18','+3V3','U1'),('C19','+3V3','U1')]
for i,(ref,net,ic) in enumerate(caps):
    x=X0+(i%6)*10.16; y=104.14+(i//6)*22.86
    key='C10u' if ref in ('C17','C19') else 'C100n'
    fp,lcsc,mpn,mfr=PARTS[key]
    p=place('Device:C',ref,'10uF 25V' if key=='C10u' else '100nF',x,y,fp=fp,fields={'LCSC':lcsc,'MPN':mpn,'Manufacturer':mfr})
    power(net,*p['1']); power('GND',*p['2']); CAPMAP[ref]=ic
# pressure RC filter caps (100nF at ADC pin, with 10k/20k divider -> fc ~ 239 Hz)
for i in range(6):
    ref=f'C{21+i}'; x=X0+i*10.16; y=180.34
    fp,lcsc,mpn,mfr=PARTS['C100n']
    p=place('Device:C',ref,'100nF',x,y,fp=fp,fields={'LCSC':lcsc,'MPN':mpn,'Manufacturer':mfr})
    label(f'PD_{i+1}',*p['1']); power('GND',*p['2']); CAPMAP[ref]=f'PD_{i+1}'
# section notes
e.append(['text',Q('12V INPUT: PTC 5A hold / 10A trip + P-FET reverse-polarity (ideal diode). Size total 12V load <= 5A.'),['at','360','30','0'],eff(justify='left bottom'),['uuid',U()]])
e.append(['text',Q('DECOUPLING: 100nF at each HX711 VSUP/AVDD(+5V) & DVDD(+3V3), MAX31856 AVDD/DVDD, R-78 in; 10uF bulk on +12V(R-78 in) and +3V3'),['at','360','96','0'],eff(justify='left bottom'),['uuid',U()]])
e.append(['text',Q('PRESSURE ADC RC FILTERS: 100nF at Teensy pin; 10k/20k divider -> 4.5V max = 3.0V, fc ~ 240 Hz'),['at','360','170','0'],eff(justify='left bottom'),['uuid',U()]])

open(SCH,'w').write(sexp.dump(e)+"\n")
json.dump(CAPMAP,open('/workspace/pcb/tools/capmap.json','w'),indent=1)
print("new symbols:",len(new_syms))
