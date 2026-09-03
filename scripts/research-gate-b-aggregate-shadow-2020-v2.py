#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agg',ROOT/'scripts/research-gate-b-aggregate-shadow-2020.py')
agg=importlib.util.module_from_spec(spec);spec.loader.exec_module(agg)

def extract_ppty(text,series):
 lines=agg.schedule_segment(text,series);cleaned=[agg.plain(x) for x in lines];inside=False;rows=[];net=None
 for i,line in enumerate(cleaned):
  if re.search(r'^COMMON STOCKS\s*-\s*100\.0%',line,re.I):inside=True;continue
  if inside and re.search(r'^TOTAL COMMON STOCKS',line,re.I):inside=False
  if re.search(r'^NET ASSETS\s*-\s*100\.0%',line,re.I):
   for x in cleaned[i+1:min(len(cleaned),i+8)]:
    q=x.replace('$','').strip()
    if re.fullmatch(r'\d[\d,]*',q):net=float(q.replace(',',''));break
  if not inside or not line or not re.search(r'[A-Za-z]',line):continue
  if re.search(r'\d+(?:\.\d+)?\s*%$',line) or re.match(r'^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION|VALUE|SCHEDULE OF INVESTMENTS)',line,re.I):continue
  prev=[x for x in cleaned[max(0,i-5):i] if x];foll=[x for x in cleaned[i+1:min(len(cleaned),i+6)] if x]
  if not any(re.fullmatch(r'\d[\d,]*',x) for x in prev):continue
  value=None
  for x in foll:
   if re.search(r'[A-Za-z]',x):break
   q=x.replace('$','').strip()
   if re.fullmatch(r'\d[\d,]*',q):value=float(q.replace(',',''));break
  if value and value>0:rows.append((line,value))
 return rows,net

def extract_gfin(text,series):
 lines=agg.schedule_segment(text,series);rows=[];net=None;inside=False;seen=False;ended=False
 for i,raw in enumerate(lines):
  line=agg.plain(raw)
  if not seen and re.search(r'^Common Stocks?\s*[–—-]',line,re.I):inside=True;seen=True;continue
  if inside and re.search(r'^(?:Repurchase Agreements?|Short-Term Investments?|Securities Lending|Total Investments)',line,re.I):inside=False;ended=True
  if inside:
   m=re.match(r'^([\d,]+)\s+(.+?)\s+(?:\$\s*)?([\d,]+)\s*$',line)
   if m:
    desc=re.sub(r'\s*\([a-z]\)\s*$','',m.group(2),flags=re.I).strip();v=float(m.group(3).replace(',',''))
    if re.search(r'[A-Za-z]',desc) and not re.match(r'^(Total|Common Stocks)',desc,re.I):rows.append((desc,v))
  if seen and re.search(r'^NET ASSETS\s*[–—-]\s*100\.0%',line,re.I):
   nums=re.findall(r'\d[\d,]*',line)
   if nums:net=float(nums[-1].replace(',',''));break
   for x in lines[i+1:min(len(lines),i+8)]:
    q=agg.plain(x).replace('$','').strip()
    if re.fullmatch(r'\d[\d,]*',q):net=float(q.replace(',',''));break
   if net:break
  if ended and re.search(r'^Total Investments\s*[–—-]\s*(\d+(?:\.\d+)?)%',line,re.I) and net is None:
   pct=float(re.search(r'(\d+(?:\.\d+)?)%',line).group(1))
   for x in lines[i:min(len(lines),i+8)]:
    q=agg.plain(x)
    vals=re.findall(r'\$\s*([\d,]+)',q)
    if vals and pct>0:net=float(vals[-1].replace(',',''))/(pct/100.0);break
  if ended and seen and re.search(r'^Common Stocks?\s*[–—-]',line,re.I):break
 return rows,net

agg.extract_ppty=extract_ppty
agg.extract_gfin=extract_gfin
agg.OUT=ROOT/'data/research/gate-b-aggregate-shadow-2020-v2.json'
if __name__=='__main__':agg.main()
# trigger marker 2026-09-03
