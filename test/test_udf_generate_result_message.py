from pyspark.sql.types import StructType, StructField
from pyspark.sql.functions import col, lit

from app import udfs as udfs
from app import schemas as schemas

test_data = [
    {
        "ner": {
            "ner": [
                {"entity": "Albert Einstein", "category": "PERSON"},
                {"entity": "14 March 1879", "category": "DATE"},
                {"entity": "18", "category": "CARDINAL"},
                {"entity": "April 1955", "category": "DATE"},
                {"entity": "German", "category": "NORP"},
                {"entity": "Einstein", "category": "PERSON"},
                {"entity": "quantum mechanics", "category": "ORG"},
                {"entity": "two", "category": "CARDINAL"},
            ]
        }
    },
    {
        "ner": {
            "ner": [
                {"entity": "Earth", "category": "LOC"},
                {"entity": "third", "category": "ORDINAL"},
                {"entity": "Sun", "category": "LOC"},
                {"entity": "About 29.2%", "category": "PERCENT"},
                {"entity": "Moon", "category": "PERSON"},
                {"entity": "about 365.25 days", "category": "DATE"},
            ]
        }
    },
]

pass_through_data = {"uuid": "1234-5678-910", "lang": "en"}

test_data_schema = StructType(
    [
        StructField("ner", schemas.ner_schema, True),
        StructField("result", schemas.result_schema, True),
    ]
)


# tests
def test_generate_result_message(spark):
    df = spark.createDataFrame(test_data, test_data_schema).withColumn(
        "result",
        udfs.generate_result_message(
            col("ner"), lit(pass_through_data["uuid"]), lit(pass_through_data["lang"])
        ),
    )
    df.persist()
    df.show(truncate=False)
    for df_row in df.collect():
        df_row = df_row.asDict(True)
        ner_result = df_row.get("ner")
        result_message = df_row.get("result")

        print(f"testing calculated result_message: {result_message}")
        for key, value in pass_through_data.items():
            assert result_message[key] == value

        for key, value in ner_result.items():
            assert result_message[key] == value

    df.unpersist()
