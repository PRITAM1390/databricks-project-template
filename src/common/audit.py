import json
from pyspark.sql import DataFrame, functions as F


def add_audit_columns(df: DataFrame, source: str) -> DataFrame:
    """Add standard audit columns to every table we write."""
    return (df
            .withColumn("_ingest_ts", F.current_timestamp())
            .withColumn("_source", F.lit(source)))
