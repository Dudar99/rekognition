import base64
import json
import os

import boto3
from .AWS import AWS

from django.http import HttpResponse
from django.template import loader
from .models import Collection, Person

DEFAULT_IMG_LOCAL_PATH = '/home/dudar99/Pictures'
DEFAULT_BUCKET = "videos-sample-1"
DEFAULT_REGION = 'us-east-1'
MILLISEC_IN_SEC = 1000
rekognition = boto3.client('rekognition', region_name=DEFAULT_REGION)
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb', region_name=DEFAULT_REGION)
dynamodb_resource = boto3.resource('dynamodb', region_name="us-east-1")
sns = boto3.client('sns', region_name=DEFAULT_REGION)


def collection(request):
    template = loader.get_template('rekognition/collections.html')
    errors = []
    # delete_all_collections()
    if request.method == 'POST':
        collection_id = request.POST.get('collection_id')
        aws = AWS(collection_id=collection_id)
        if not collection_id:
            errors.append("Please provide collection name")
        elif Collection.objects.filter(collection_id=collection_id):

            errors.append("Collection with this name already exist")
        else:
            aws.create_face_collection_attributes()
            # create collection
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


def create_faces_context(collection):
    aws = AWS(collection.collection_id)
    description = aws.describe_collection(collection_id=collection.collection_id)
    created_ddtm = description.get('CreationTimestamp').strftime("%m/%d/%Y, %H:%M:%S")
    collection_description = {
        'face_count': description.get('FaceCount'),
        'collection_name': collection.collection_id,
        'created_ddtm': created_ddtm
    }
    return {
        'faces': [{'person': person, 'img': get_base64_image(person)} for person in
                  Person.objects.filter(collection_id_id=collection.id)],
        'collection_id': collection.id,
        'collection_description': collection_description
    }


def prepare_video_results(res):
    recs = []

    for r in res:
        parsed_matching = json.loads(r['results'])
        face_ids = parsed_matching.keys()
        peoples = Person.objects.filter(face_id__in=face_ids)
        peoples_stats = []
        for people in peoples:
            parsed_data = parsed_matching.get(people.face_id)
            peoples_stats.append({'person': people,
                                  'similarity': parsed_data['similarity'],
                                  'timestamp': parsed_data['timestamp'] / MILLISEC_IN_SEC
                                  })
        recs.append({
            'people_count': len(parsed_matching),
            'datetime': r['datetime'],
            'peoples': peoples_stats
        })
    return recs


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

        face_data = rekognition.index_faces(
            CollectionId=collection.collection_id,
            Image={
                'S3Object': {
                    'Bucket': DEFAULT_BUCKET,
                    'Name': key,
                }
            },
            MaxFaces=1,
        )
        face_id = face_data.get('FaceRecords', [{}])[0].get('Face', {}).get('FaceId')
        face_metadata = face_data.get('FaceRecords', [{}])[0].get('FaceDetail', {})
        if not face_id:
            errors.append("this image does not contain eny faces")
        person = Person(
            collection_id_id=collection,
            face_id=face_id,
            first_name=first_name,
            last_name=last_name,
            image_path=key,
            face_metadata=face_metadata
        )
        person.save()

    template = loader.get_template('rekognition/collection_faces.html')
    context = create_faces_context(collection)
    return HttpResponse(template.render(context, request))


def video_results(request, id):
    template = loader.get_template('rekognition/video.html')
    collection = Collection.objects.filter(id=id).first()
    aws = AWS(collection.collection_id)
    video_rekognition_results = aws.get_data_from_dynamodb_table()
    path_to_collection = os.path.join('videos/', collection.collection_id)

    if request.method == 'POST':
        subject = request.POST.get('subject')
        video_name = request.POST.get('video')
        video_path = os.path.join(DEFAULT_IMG_LOCAL_PATH, video_name)

        with open(video_path, "rb") as f:
            s3_video_name = subject + video_name
            key = os.path.join(path_to_collection, s3_video_name)
            s3.upload_fileobj(f, DEFAULT_BUCKET, key)

    context = {
        'results': prepare_video_results(video_rekognition_results),
        'collection_id': id
    }
    return HttpResponse(template.render(context, request))


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    template = loader.get_template('rekognition/index.html')
    context = {
        'latest_question_list': [1, 23],
    }
    return HttpResponse(template.render(context, request))
