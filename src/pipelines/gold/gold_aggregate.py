# Databricks notebook source
# Gold: business aggregate
from pyspark.sql import functions as F

for w in ["silver_catalog", "silver_schema", "gold_catalog", "gold_schema"]:
    dbutils.widgets.text(w, "")

source = f"{dbutils.widgets.get('silver_catalog')}.{dbutils.widgets.get('silver_schema')}.orders"
target = f"{dbutils.widgets.get('gold_catalog')}.{dbutils.widgets.get('gold_schema')}.customer_sales"

df = (spark.table(source)
      .groupBy("customer")
      .agg(F.sum("amount").alias("total_sales"), F.count("*").alias("order_count")))
df.write.mode("overwrite").saveAsTable(target)

print(f"Gold: wrote {df.count()} rows to {target}")
