exec(open('audit/angles34.py').read().split('SIG=14.0')[0])
import openpyxl
t=openpyxl.load_workbook('in1117/s2.xlsx',data_only=True)['Tracking']; M={}
for r in t.iter_rows(min_row=13,max_row=t.max_row,values_only=True):
    d=dd(r[0])
    if d and isinstance(r[3],(int,float)): M[(d,r[1],r[2])]=(r[3],r[4])
out={}
for g in G:
    pass
