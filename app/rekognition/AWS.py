import os

import boto3
from boto3.dynamodb.conditions import Key

DEFAULT_IMG_LOCAL_PATH = '/home/dudar99/Pictures'
DEFAULT_BUCKET = "videos-sample-1"
DEFAULT_REGION = 'us-east-1'


class AWS:

    def __init__(self, collection_id):
        self.rekognition = boto3.client('rekognition', region_name=DEFAULT_REGION)
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.client('dynamodb', region_name=DEFAULT_REGION)
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=DEFAULT_REGION)
        self.sns = boto3.client('sns', region_name=DEFAULT_REGION)
        self.collection_id = collection_id
        self.sns_topic_arn = ''

    def create_s3_folder(self, bucket, path):
        name = f"{path}/{self.collection_id}/"
        self.s3.put_object(Bucket=bucket, Key=(name))

    def add_face_to_folder(self, bucket, path, photo_name):
        name = os.path.join(path, photo_name)
        self.s3.put_object(Bucket=bucket, Key=(name))

    @classmethod
    def delete_all_collections(self):
        collections = self.rekognition.list_collections().get("CollectionIds")
        for col_id in collections:
            Collection.objects.filter(collection_id=col_id).delete()
            self.rekognition.delete_collection(CollectionId=col_id)

    def create_dynamodb_table(self):
        try:
            table = self.dynamodb.create_table(
                TableName=self.collection_id,
                KeySchema=[
                    {
                        'AttributeName': 'collection_name',
                        'KeyType': 'HASH'  # Partition key
                    },

                    {
                        'AttributeName': 'datetime',
                        'KeyType': 'RANGE'  # Partition key
                    }

                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'collection_name',
                        'AttributeType': 'S'
                    },

                    {
                        'AttributeName': 'datetime',
                        'AttributeType': 'S'
                    },

                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )

            print("Table status:", table)
        except Exception as e:
            print(e)

    def get_data_from_dynamodb_table(self):
        table = self.dynamodb_resource.Table(self.collection_id)

        res = table.query(
            TableName=self.collection_id,
            KeyConditionExpression=Key('collection_name').eq(self.collection_id)
        )
        results = res['Items']
        return results

    def create_sns_topic(self):
        res = self.sns.create_topic(Name=self.collection_id)
        self.sns_topic_arn = res.get('TopicArn')
        self.__subscribe_to_email(email='dudaryourko@gmail.com')

    def __subscribe_to_email(self, email: str):
        print("Subscribing SNS to send emails")
        response = self.sns.subscribe(
            TopicArn=self.sns_topic_arn,
            Protocol='email',
            Endpoint=email,
            ReturnSubscriptionArn=True
        )
        print(f"Subscribing response:{response}")

    def __create_face_collection(self):
        self.rekognition.create_collection(CollectionId=self.collection_id)

    def create_face_collection_attributes(self):
        self.__create_face_collection()
        self.create_s3_folder(DEFAULT_BUCKET, 'faces')
        self.create_s3_folder(DEFAULT_BUCKET, 'videos')
        self.create_sns_topic()
        self.create_dynamodb_table()
