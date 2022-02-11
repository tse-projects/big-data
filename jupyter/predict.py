import datetime
import logging
import os
import pickle
import re
import time

import category_encoders as ce
import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer

from utils.logger import Logger
from utils.s3_handler import S3Handler
from utils.sqs_handler import SQSHandler

DATA_FILENAME = '33000-BORDEAUX.csv'


def main():
    Logger()
    # Init messaging queue service
    sqs_handler_predict = SQSHandler(queue_name='PredictQueue')
    sqs_handler_parse = SQSHandler(queue_name='ParseQueue')

    # Init S3 service
    s3_handler = S3Handler()

    while 1:
        time.sleep(1)
        for message in sqs_handler_predict.queue.receive_messages(MessageAttributeNames=['Prediction'],
                                                                  WaitTimeSeconds=20):
            logging.info(f'New messages in {sqs_handler_predict.queue_name}')
            logging.info(message.message_attributes)
            if message.message_attributes is not None:
                prediction = message.message_attributes.get('Prediction')
                logging.info(prediction)
                try:
                    filename = prediction['StringValue']
                    logging.info(f'Downloading the file {filename}')
                    s3_handler.download_file('predict_queue/', filename)

                    logging.info(f'Running ML...')
                    result_filename = simulate_ml(filename)
                    logging.info(f'End ML')

                    # Upload the result to S3
                    logging.info(f'Uploading the result')
                    s3_handler.upload_file('parse_queue/', result_filename)
                    logging.info(f'File uploaded !')

                    # Delete generated file
                    if os.path.exists(result_filename):
                        os.remove(result_filename)
                    else:
                        logging.error("The file does not exist")

                    # Send message to sqs parse queue
                    sqs_handler_parse.send_message('Parsing', result_filename)

                    logging.info('Task complete !')
                except Exception as e:
                    logging.error(e)
                message.delete()


def simulate_ml(filename: str) -> str:
    # Simulate ML
    # data = pandas.read_csv(DATA_FILENAME)
    #
    # filename = f'{datetime.datetime.now().replace(microsecond=0).isoformat()}_countries.csv'
    # data.to_csv(filename)
    #
    # return filename
    # To clean text
    nltk.download('stopwords')
    nltk.download('wordnet')
    nltk.download('omw-1.4')

    # To clean text
    def preprocess_text(sentence):
        sentence = str(sentence)
        # Lowercase text
        sentence = sentence.lower()
        # Remove whitespace
        sentence = sentence.replace('{html}', "")
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', sentence)
        # Remove weblinks
        rem_url = re.sub(r'http\S+', '', cleantext)
        # Remove numbers
        rem_num = re.sub('[0-9]+', '', rem_url)
        tokenizer = RegexpTokenizer(r'\w+')
        tokens = tokenizer.tokenize(rem_num)
        # Remove StopWords
        filtered_words = [w for w in tokens if len(w) > 2 if
                          not w in stopwords.words('french') or not w in stopwords.words('english')]
        return " ".join(filtered_words)

    # Load data
    airbnb = pd.read_csv(filename)
    predict = airbnb
    columns_to_remove = ['title']

    airbnb = airbnb.drop(columns=columns_to_remove, errors='ignore')

    # Encoding housing_type column
    # one_hot_encoder = ce.OneHotEncoder(cols=['housing_type'])
    one_hot_encoder = pickle.load(open('./housing_type_encoder.pickle', 'rb'))
    housing_type_one_hot = one_hot_encoder.transform(airbnb["housing_type"])
    airbnb = pd.concat([airbnb, housing_type_one_hot], axis=1)
    airbnb = airbnb.drop(columns=['housing_type'], errors='ignore')

    # Encoding property_type column
    # binary_encoder = ce.BinaryEncoder(cols=['property_type'])
    binary_encoder = pickle.load(open('./property_type_encoder.pickle', 'rb'))
    property_type_binary = binary_encoder.transform(airbnb["property_type"])
    airbnb = pd.concat([airbnb, property_type_binary], axis=1)
    airbnb = airbnb.drop(columns=['property_type'], errors='ignore')

    # Encoding cancel_conditions column
    cancel_conditions_order = {
        'None': 1,
        'Flexibles': 2,
        'Modérées': 3,
        'Strictes': 4
    }
    airbnb["cancel_conditions"] = airbnb["cancel_conditions"].fillna('None')
    airbnb['cancel_conditions'] = airbnb.cancel_conditions.map(cancel_conditions_order)

    airbnb['description_pre'] = airbnb['description'].map(lambda s: preprocess_text(s))

    # Adding description related features
    final_features_keys = pd.read_csv('final_features.csv').columns
    final_features = {}
    for i in final_features_keys:
        final_features[i] = []

    for feature in final_features:  ## Nom du fichier avec les mots - OK
        for desc in airbnb['description_pre']:
            if feature in desc:
                final_features[feature].append(1)
            else:
                final_features[feature].append(0)
    # for feature in final_features:
    #     airbnb[feature] = final_features[feature]
    airbnb = pd.concat([airbnb, pd.DataFrame.from_dict(final_features)], axis=1)
    airbnb = airbnb.drop(columns=['description', 'longitude', 'latitude', 'description_pre'], errors='ignore')

    # Predict of model
    # Loading the model from disk
    loaded_regressor_model = pickle.load(open('./finalized_model_regressor.sav', 'rb'))
    loaded_rf_model = pickle.load(open('./finalized_model_rf.sav', 'rb'))

    # Add predict in df
    regression_predicted_price = loaded_regressor_model.predict(airbnb)
    predict['regression_predicted_price'] = regression_predicted_price
    rf_predicted_price = loaded_rf_model.predict(airbnb)
    predict['rf_predicted_price'] = rf_predicted_price

    # Convert CSV
    result_filename = f'{datetime.datetime.now().replace(microsecond=0).isoformat()}_prediction.csv'
    predict.to_csv(result_filename)

    return result_filename


if __name__ == "__main__":
    main()
