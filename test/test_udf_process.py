from pyspark.sql.types import DoubleType, StringType, StructType, StructField
from pyspark.sql.functions import col, lit, udf, from_json

from app import udfs as udfs
from app import schemas as schemas

# test parameters
MIN_JACCARD_SIMILARITY = 0.5

# test data
supported_text_data = [
    {
        "text": "Albert Einstein (born: 14 March 1879, died: 18 April 1955) was a German theoretical physicist, widely acknowledged to be one of the greatest physicists of all time. Einstein is known for developing the theory of relativity, but he also made important contributions to the development of the theory of quantum mechanics. Relativity and quantum mechanics are together the two pillars of modern physics.",
        "expected_entities": {
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
        },
    },
    {
        "text": "Earth is the third planet from the Sun and the only astronomical object known to harbor life. About 29.2% of Earth's surface is land consisting of continents and islands. Earth's atmosphere consists mostly of nitrogen and oxygen. Earth's gravity interacts with other objects in space, especially the Moon, which is Earth's only natural satellite. Earth orbits around the Sun in about 365.25 days. Earth's axis of rotation is tilted with respect to its orbital plane, producing seasons on Earth.",
        "expected_entities": {
            "ner": [
                {"entity": "Earth", "category": "LOC"},
                {"entity": "third", "category": "ORDINAL"},
                {"entity": "Sun", "category": "LOC"},
                {"entity": "About 29.2%", "category": "PERCENT"},
                {"entity": "Moon", "category": "PERSON"},
                {"entity": "about 365.25 days", "category": "DATE"},
            ]
        },
    },
]

supported_text_data_schema = StructType(
    [
        StructField("text", StringType(), True),
        StructField("expected_entities", schemas.ner_schema, True),
        StructField("calculated_entities", schemas.ner_schema, True),
        StructField("entities_similarity", DoubleType(), True),
    ]
)


# utility functions
def jaccard_similarity(x, y):
    intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
    union_cardinality = len(set.union(*[set(x), set(y)]))
    if union_cardinality > 0:
        return intersection_cardinality / float(union_cardinality)
    return 0


def get_all_entities(entities_list):
    s = set()
    for entity in entities_list:
        s.add(entity["entity"])
    return s


@udf(returnType=DoubleType())
def get_entities_similarity(expected, calculated):

    expected = expected.asDict(True)
    calculated = calculated.asDict(True)
    all_expected_entities = get_all_entities(expected["ner"])
    all_calculated_entities = get_all_entities(calculated["ner"])
    return jaccard_similarity(all_expected_entities, all_calculated_entities)


# tests
def test_process(spark):
    df = spark.createDataFrame(supported_text_data, supported_text_data_schema)
    df = df.withColumn(
        "calculated_entities", from_json(udfs.process(col("text")), schemas.ner_schema)
    )
    df.persist()
    df = df.withColumn(
        "entities_similarity",
        get_entities_similarity(col("expected_entities"), col("calculated_entities")),
    )
    df.persist()
    df.show(truncate=False)

    # assert entities
    assert (
        df.where(col("entities_similarity") <= lit(MIN_JACCARD_SIMILARITY)).count() == 0
    )

    df.unpersist()
