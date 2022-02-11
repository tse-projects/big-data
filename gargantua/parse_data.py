import json
import logging
import os
import time

import pandas
import pymongo

from utils.logger import Logger
from utils.s3_handler import S3Handler
from utils.sqs_handler import SQSHandler

password = 'HM7ovg1VmvVwgMYT'
database = 'airbnb'


def read_csv(filename: str):
    data = pandas.read_csv(filename)
    return data


def connect_to_mongo():
    client = pymongo.MongoClient(
        f"mongodb+srv://jupyter:{password}@cluster0.lmi6c.mongodb.net/{database}?retryWrites=true&w=majority")
    return client


def main():
    Logger()
    client = connect_to_mongo()
    s3_handler = S3Handler()

    # Start the client and wait for messages
    sqs_handler_parse = SQSHandler(queue_name='ParseQueue')
    sqs_handler_result = SQSHandler(queue_name='ResultQueue')
    while 1:
        time.sleep(1)
        for message in sqs_handler_parse.queue.receive_messages(MessageAttributeNames=['Parsing'], WaitTimeSeconds=20):
            logging.info(f'New messages in {sqs_handler_parse.queue_name}')
            if message.message_attributes is not None:
                prediction = message.message_attributes.get('Parsing')
                try:
                    filename = prediction['StringValue']

                    # Download the file
                    s3_handler.download_file('parse_queue/', filename)
                    logging.info(f'File {filename} downloaded')

                    data = read_csv(filename)

                    db = client[database]

                    collection = db['predictions']

                    # Empty the collection
                    # logging.info('Emptying database...')
                    # collection.delete_many({})

                    logging.info('Inserting database...')
                    payload = json.loads(data.to_json(orient='records'))
                    result = collection.insert_many(payload)
                    logging.info('Inserting completed')

                    logging.info(f'Deleting {filename}')
                    os.remove(filename)

                    str_formatted_ids = list(map(lambda x: str(x), result.inserted_ids))
                    logging.info(str_formatted_ids)
                    sqs_handler_result.send_message('Result', json.dumps(str_formatted_ids))
                    logging.info('Task complete !')
                except Exception as e:
                    print(e)
                message.delete()


if __name__ == "__main__":
    main()
