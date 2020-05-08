import base64
import os

import boto3
from boto3.dynamodb.conditions import Key


# Create your views here.
from django.http import HttpResponse
from django.template import loader
from .models import Collection, Person

DEFAULT_IMG_LOCAL_PATH = '/home/dudar99/Pictures'
DEFAULT_BUCKET = "videos-sample-1"
DEFAULT_REGION = 'us-east-1'
rekognition = boto3.client('rekognition', region_name=DEFAULT_REGION)
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb', region_name=DEFAULT_REGION)
dynamodb_resource = boto3.resource('dynamodb', region_name="us-east-1")


def add_face_to_folder(bucket, path, photo_name):
    name = os.path.join(path, photo_name)
    s3.put_object(Bucket=bucket, Key=(name))


def delete_all_collections():
    collections = rekognition.list_collections().get("CollectionIds")
    for col_id in collections:
        Collection.objects.filter(collection_id=col_id).delete()
        rekognition.delete_collection(CollectionId=col_id)


def create_s3_folder(bucket, path, name):
    name = f"{path}/{name}/"
    s3.put_object(Bucket=bucket, Key=(name))


def create_dynamodb_table(table_name):
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'collection_name',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'results',
                    'KeyType': 'RANGE'  # sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'collection_name',
                    'AttributeType': 'S'
                },

                {
                    'AttributeName': 'results',
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


def get_data_from_dynamodb_table(table_name):
    table = dynamodb_resource.Table(table_name)

    res = table.query(
        TableName=table_name,
        KeyConditionExpression=Key('collection_name').eq(table_name)
    )
    results = res['Items']
    return results


def collection(request):
    template = loader.get_template('rekognition/collections.html')
    errors = []
    # delete_all_collections()
    if request.method == 'POST':
        collection_id = request.POST.get('collection_id')
        if not collection_id:
            errors.append("Please provide collection name")
        elif Collection.objects.filter(collection_id=collection_id):

            errors.append("Collection with this name already exist")

        else:
            response = rekognition.create_collection(CollectionId=collection_id)
            create_s3_folder(DEFAULT_BUCKET, 'faces', collection_id)
            create_s3_folder(DEFAULT_BUCKET, 'videos', collection_id)
            create_dynamodb_table(collection_id)
            print(response)
            collection = Collection(collection_id=collection_id)
            collection.save()
    context = {
        'collections': Collection.objects.all(),
        'errors': errors
    }

    return HttpResponse(template.render(context, request))


def get_base64_image(person):
    obj = s3.get_object(Bucket=DEFAULT_BUCKET, Key=person.image_path)
    body = obj.get('Body').read()
    base64_encoded_data = base64.b64encode(body)
    base64_message = base64_encoded_data.decode('utf-8')
    return base64_message


def create_faces_context(id):
    return {
        'faces': [{'person': person, 'img': get_base64_image(person)} for person in
                  Person.objects.filter(collection_id_id=id)],
        'collection_id': id
    }


def collection_faces(request, id):
    errors = []
    collection = Collection.objects.filter(id=id).first()
    path_to_collection = os.path.join('faces/', collection.collection_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        img = request.POST.get('img')
        img_path = os.path.join(DEFAULT_IMG_LOCAL_PATH, img)

        with open(img_path, "rb") as f:
            s3_image_name = first_name + last_name + img
            key = os.path.join(path_to_collection, s3_image_name)
            s3.upload_fileobj(f, DEFAULT_BUCKET, key)

        response = rekognition.index_faces(
            CollectionId=collection.collection_id,
            Image={
                'S3Object': {
                    'Bucket': DEFAULT_BUCKET,
                    'Name': key,
                }
            },
            MaxFaces=1,
        )
        face_id = response.get('FaceRecords', [{}])[0].get('Face', {}).get('FaceId')
        face_metadata = response.get('FaceRecords', [{}])[0].get('FaceDetail', {})
        if not face_id:
            errors.append("this image does not contain eny faces")
        person = Person(
            collection_id_id=collection,
            face_id=face_id,
            first_name=first_name,
            last_name=last_name,
            image_path=key
        )
        person.save()

    template = loader.get_template('rekognition/collection_faces.html')
    context = create_faces_context(id)
    # context.update({'list' : rekognition.list_faces(CollectionId=collection.collection_id)})

    return HttpResponse(template.render(context, request))


def video_results(request, id):
    template = loader.get_template('rekognition/video.html')
    collection = Collection.objects.filter(id=id).first()
    video_rekognition_results = get_data_from_dynamodb_table(collection.collection_id)
    context = {
        'results': video_rekognition_results
    }
    return HttpResponse(template.render(context, request))


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    template = loader.get_template('rekognition/index.html')
    context = {
        'latest_question_list': [1, 23],
    }
    return HttpResponse(template.render(context, request))
