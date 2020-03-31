import json
import boto3


def get_bucket_and_key(event):
    event_rec = event['Records'] and event['Records'][0]
    bucket_name = event_rec['s3']['bucket']['name']
    video_name = event_rec['s3']['object']['key']
    return bucket_name, video_name


def lambda_handler(event, context):
    bucket_name, video_name = get_bucket_and_key(event)


    return None
