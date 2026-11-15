# Databricks notebook source
dbutils.widgets.text("catalog", "")
dbutils.widgets.text("bronze_schema", "")

catalog = dbutils.widgets.get("catalog")
bronze = dbutils.widgets.get("bronze_schema")
target = f"{catalog}.{bronze}.sample_table"

df = spark.createDataFrame([(1, "alpha"), (2, "beta")], ["id", "name"])
df.write.mode("overwrite").saveAsTable(target)

print(f"Wrote {df.count()} rows to {target}")