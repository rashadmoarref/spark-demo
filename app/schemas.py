from pyspark.sql.types import LongType, ArrayType, DoubleType, StringType, StructType, StructField

input_schema = StructType(
    [
        StructField("uuid", StringType(), True),
        StructField("text", StringType(), True),
        StructField("lang", StringType(), True),
    ]
)

entity_schema = StructType(
    [
        StructField("entity", StringType(), True),
        StructField("category", StringType(), True),
    ]
)

ner_schema = StructType(
    [
        StructField("ner", ArrayType(entity_schema), True),
        StructField("error_message", StringType(), True),
        StructField("ts_start", LongType(), True),
        StructField("ts_end", LongType(), True),
        StructField("process_time", DoubleType(), True),
    ]
)

result_schema = StructType(
    [
        StructField("ner", ArrayType(entity_schema), True),
        StructField("ts_start", LongType(), True),
        StructField("ts_end", LongType(), True),
        StructField("process_time", DoubleType(), True),
        StructField("uuid", StringType(), True),
        StructField("lang", StringType(), True),
        StructField("error_message", StringType(), True),
    ]
)
