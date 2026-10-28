import sys, json, datetime
sys.path.insert(0,'.')
from pyspark.sql import SparkSession
sp=SparkSession.builder.master("local[1]").config("spark.ui.enabled","false").getOrCreate(); sp.sparkContext.setLogLevel("ERROR")
from setup_sql import setup_statements
from core import *
sp.sql("CREATE DATABASE IF NOT EXISTS sales2")
for st in setup_statements("sales2"):
    sp.sql(st.replace("CREATE OR REPLACE TABLE","CREATE OR REPLACE TEMP VIEW").replace("sales2.","").split("COMMENT")[0] + "AS" + st.split("\nAS",1)[1] if False else st.replace("CREATE OR REPLACE TABLE sales2.","CREATE OR REPLACE TEMP VIEW ").replace("\nCOMMENT 'One row per customer account.'","").replace("\nCOMMENT 'One row per order. order_date is when the order was placed; invoice_date is when it was billed. product_line is what was sold.'",""))
orders=sp.table("orders").toPandas(); customers=sp.table("customers").toPandas()
orders["amount_usd"]=orders.amount_usd.astype(float)
today=datetime.date.today()
key=answer_key(orders,customers,today)
print(len(key), "rows in answer key")
for qid in ["A1","C1","E1","R1","RR1","F1","F2","RR5","A3"]:
    k=key[key.qid==qid]
    print(qid, "owner:", k[k.is_owner].answer.iloc[0], "| analyst:", k[k.is_analyst].answer.iloc[0] if k.is_analyst.any() else None)
key.to_csv("answer_key_local.csv", index=False)
# check owner == analyst?
same=[q for q in key.qid.unique() if key[(key.qid==q)&key.is_owner].answer.iloc[0]==(key[(key.qid==q)&key.is_analyst].answer.iloc[0] if key[(key.qid==q)&key.is_analyst].shape[0] else None)]
print("questions where analyst guess == owner:", same)
