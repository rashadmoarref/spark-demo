import json
import time

import spacy
from pyspark.sql import Row
from pyspark.sql.types import StringType
from pyspark.sql.functions import udf

from app import schemas as schemas

NER_MODEL = spacy.load("en_core_web_sm")


@udf(returnType=StringType())
def process(text: str) -> str:
    """
    This is the main driver function that calls the batch prediction and assign it to each message
    """

    start_time = time.time()
    ts_start = int(start_time)

    try:
        document = NER_MODEL(text)
        result = {
            "ner": [
                {"entity": entity.text, "category": entity.label_}
                for entity in document.ents
            ]
        }
    except Exception as e:
        end_time = time.time()
        ts_end = int(end_time)
        process_time = int((end_time - start_time) * 1000)
        failed_message = {
            "error_message": f"{type(e).__name__}: {e}",
            "ts_start": ts_start,
            "ts_end": ts_end,
            "process_time": process_time,
        }
        return json.dumps(failed_message)
    else:
        end_time = time.time()
        ts_end = int(end_time)
        process_time = int((end_time - start_time) * 1000)
        result["error_message"] = None
        result["ts_start"] = ts_start
        result["ts_end"] = ts_end
        result["process_time"] = process_time
        return json.dumps(result)


@udf(returnType=schemas.result_schema)
def generate_result_message(ner: Row, uuid: str, lang: str) -> dict:

    result_message = {}

    # convert ner pyspark Row to dict
    ner = ner.asDict(True)

    result_message["uuid"] = uuid
    result_message["lang"] = lang
    for key, value in ner.items():
        if key == "ner":
            # cleanup
            result_message[key] = []
            entity_set = set()
            for entity in value:
                if entity.get("entity") not in entity_set:
                    entity_set.add(entity.get("entity"))
                    result_message[key].append(entity)
        else:
            result_message[key] = value

    return result_message
