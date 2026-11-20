import openpyxl, sys, datetime
wb=openpyxl.load_workbook(sys.argv[1],data_only=True); t=wb['Tracking']
day=datetime.datetime.strptime(sys.argv[2],"%Y-%m-%d")
hdr=[t.cell(12,c).value for c in range(1,36)]
pcols={'ML away','ML home','ML away edge','ML home edge','Over %','Away cover %','Home cover %','Away TT over %','Home TT over %'}
ocols={'ML away odds','ML home odds','Over odds','Under odds','Away spr odds','Home spr odds','Away TT Over','Away TT Under','Home TT Over','Home TT Under'}
out=['\t'.join(hdr)]
for r in range(13,t.max_row+1):
    if t.cell(r,1).value!=day: continue
    v=[]
    for c,h in enumerate(hdr,1):
        x=t.cell(r,c).value
        if h=='Game date': v.append(x.strftime('%m/%d/%y'))
        elif h=='Card' or isinstance(x,str): v.append(x or '')
        elif h in pcols: v.append(f"{x*100:.4f}%")
        elif h in ocols: v.append(f"{x:+.0f}")
        elif h in ('Away spread','Home spread'): v.append(f"{x:+g}")
        else: v.append(repr(x))
    out.append('\t'.join(v))
open(sys.argv[3],'w').write('\n'.join(out)+'\n'); print('\n'.join(out))
