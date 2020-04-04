import json
import boto3


def get_bucket_and_key(event):
    event_rec = event['Records'] and event['Records'][0]
    bucket_name = event_rec['s3']['bucket']['name']
    video_name = event_rec['s3']['object']['key']
    return bucket_name, video_name


def lambda_handler(event, context):
    client = boto3.client('rekognition')
    collection_id = 'faces'
    # Create a collection

    bucket, key = get_bucket_and_key(event)
    response = client.index_faces(
        CollectionId=collection_id,
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key,
            }
        },

        MaxFaces=1,
    )
    faces = client.list_faces(
        CollectionId=collection_id,
    )
