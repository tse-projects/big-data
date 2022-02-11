import logging
import os

import boto3
from botocore.exceptions import ClientError


class S3Handler:
    def __init__(self):
        self.bucket_name = 'big-data-bucket-tse'
        self.s3 = boto3.client('s3', region_name='us-east-1')

        try:
            # Create a new bucket if it does not exist
            os.system('aws s3api create-bucket '
                      '--acl private '
                      f'--bucket {self.bucket_name} '
                      '--region us-east-1')

            os.system(
                'aws s3api put-public-access-block '
                f'--bucket {self.bucket_name} '
                '--public-access-block-configuration '
                '"BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"')
        except Exception as e:
            print(e)

    def upload_file(self, path_s3, filename, object_name=None):
        logging.info(f'Uploading file {filename}')
        try:
            if object_name is None:
                object_name = os.path.basename(filename)
            self.s3.upload_file(filename, self.bucket_name, path_s3 + object_name)
        except ClientError as e:
            logging.error(e)

    def download_file(self, path_s3, filename, object_name=None):
        try:
            if object_name is None:
                object_name = os.path.basename(filename)
            self.s3.download_file(self.bucket_name, path_s3 + object_name, filename)
        except ClientError as e:
            logging.error(e)
