from confluent_kafka import Consumer
import pymongo
from dotenv import load_dotenv
import json
import os
import ast
load_dotenv()
CONNECTION_STRING=os.getenv("CONNECTION_STRING")
c = pymongo.MongoClient(CONNECTION_STRING)
db= c.get_database("users1")
col ="device_data" 
if col not in db.list_collection_names():
    db.create_collection(col)
col=db.device_data
consumer_config = {
    'bootstrap.servers': os.getenv('bootstrap_servers'),
    'group.id': 'learner',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
}
kafka_consumer = Consumer(consumer_config)
topic = 'learn'
kafka_consumer.subscribe([topic])
def upload_to_database(data:str):
    json_objects = data.split('}')
    for json_object in json_objects:
        # Check if the JSON object is not empty
        if json_object.strip():
            json_object += '}'
            try:
                document = json.loads(json_object)
                col.insert_one(document)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
count=1
try:
    while count<=5:
        msg = kafka_consumer.poll(1.0)
        if msg is not None:
            count+=1
            data = msg.value().decode('utf-8')
            print(data)
            upload_to_database(data)
        
except KeyboardInterrupt:
    pass
finally:
    kafka_consumer.close()       