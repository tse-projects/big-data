import logging

import boto3


class SQSHandler:
    booted = False

    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.sqs = boto3.resource('sqs')

        try:
            # Create the queue. This returns an SQS.Queue instance
            self.queue = self.sqs.create_queue(QueueName=self.queue_name)
            self.booted = True
        except Exception as e:
            print(e)

    def send_message(self, message_body: str, message: str):
        """
        Send calculation to Simple Queue Service
        :param message_body: message body
        :param message: message, the filename
        :return: the request id
        """
        message_attr: dict = {
            message_body: {
                'StringValue': message,
                'DataType': 'String'
            }
        }
        request = self.queue.send_message(MessageBody=message_body, MessageAttributes=message_attr)
        logging.info(f'Message sent {request}')
        return request['MessageId']

    def get_message(self, message_attribute_name):
        """
        Get calculation response from Simple Queue Service
        :return: the calculation response
        """
        for message in self.queue.receive_messages(MaxNumberOfMessages=10,
                                                   MessageAttributeNames=[message_attribute_name]):
            response = message
            message.delete()
            return response.message_attributes

        return None
