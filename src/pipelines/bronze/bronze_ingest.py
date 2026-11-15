# Databricks notebook source
# Bronze: land raw data as-is (table structure comes from src/ddl/bronze/orders.sql)

# Make src/ importable so notebooks can use shared code in src/common
import os, sys
sys.path.append(os.path.abspath("../.."))

from common.audit import add_audit_columns

dbutils.widgets.text("bronze_catalog", "")
dbutils.widgets.text("bronze_schema", "")
target = f"{dbutils.widgets.get('bronze_catalog')}.{dbutils.widgets.get('bronze_schema')}.orders"

data = [
    (1, "acme", 100.0, "complete"),
    (2, "globex", 250.0, "complete"),
    (3, "acme", None, "pending"),
    (4, None, 75.0, "complete"),
]
df = spark.createDataFrame(data, ["order_id", "customer", "amount", "status"])
df = add_audit_columns(df, source="sample")
df.write.mode("overwrite").saveAsTable(target)

print(f"Bronze: wrote {df.count()} rows to {target}")