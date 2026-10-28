import sys, json; sys.path.insert(0,'.')
import pandas as pd
from core import *
key=pd.read_csv('answer_key_local.csv'); key["is_owner"]=key.is_owner.astype(bool); key["is_analyst"]=key.is_analyst.astype(bool)
def own(q): return json.loads(key[(key.qid==q)&key.is_owner].answer.iloc[0])
def ana(q): return json.loads(key[(key.qid==q)&key.is_analyst].answer.iloc[0])
runs=[dict(qid="A1",result_rows_parsed=[[str(own("A1"))]]),
      dict(qid="A1",result_rows_parsed=[[str(ana("A1"))]]),
      dict(qid="A3",result_rows_parsed=[[r,str(v)] for r,v in own("A3").items()]),
      dict(qid="A3",result_rows_parsed=[[r,str(v)] for r,v in ana("A3").items()]),
      dict(qid="A6",result_rows_parsed=[[own("A6"),"83"],["North America","62"]]),
      dict(qid="RR5",result_rows_parsed=[[str(own("RR5")/100)]]),
      dict(qid="R1",result_rows_parsed=[["19129023.00"]]),
      dict(qid="RR1",result_rows_parsed=[[str(ana("RR1"))]]),
      dict(qid="C1",result_rows_parsed=None,response_text="Which definition?")]
for r in score(runs,key): print(r["qid"], r["correct"], r["pct_off"], "|", r["matched_variants"][:120])
