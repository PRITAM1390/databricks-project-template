# Databricks notebook source
# Silver: clean and standardize
from pyspark.sql import functions as F

for w in ["bronze_catalog", "bronze_schema", "silver_catalog", "silver_schema"]:
    dbutils.widgets.text(w, "")

source = f"{dbutils.widgets.get('bronze_catalog')}.{dbutils.widgets.get('bronze_schema')}.orders"
target = f"{dbutils.widgets.get('silver_catalog')}.{dbutils.widgets.get('silver_schema')}.orders"

df = (spark.table(source)
      .filter(F.col("customer").isNotNull() & F.col("amount").isNotNull())
      .withColumn("customer", F.upper("customer")))
df.write.mode("overwrite").saveAsTable(target)

print(f"Silver: wrote {df.count()} rows to {target}")