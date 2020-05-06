import base64
import os

import boto3
from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.template import loader
from .models import Collection, Person

DEFAULT_IMG_LOCAL_PATH = '/home/dudar99/Pictures'
DEFAULT_BUCKET = "videos-sample-1"
rekognition = boto3.client('rekognition', region_name='us-east-1')
s3 = boto3.client('s3')


def add_face_to_folder(bucket, path, photo_name):
    name = os.path.join(path, photo_name)
    s3.put_object(Bucket=bucket, Key=(name))


def delete_all_collections():
    collections = rekognition.list_collections().get("CollectionIds")
    for col_id in collections:
        Collection.objects.filter(collection_id=col_id).delete()
        rekognition.delete_collection(CollectionId=col_id)


def create_s3_folder(bucket, path, name):
    name = os.path.join(path, name) + '/'
    s3.put_object(Bucket=bucket, Key=(name))


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
            create_s3_folder(DEFAULT_BUCKET, '/faces', collection_id)
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


def create_context(id):
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
            key = os.path.join(path_to_collection, img)
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
    context = create_context(id)

    return HttpResponse(template.render(context, request))


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    template = loader.get_template('rekognition/index.html')
    context = {
        'latest_question_list': [1, 23],
    }
    return HttpResponse(template.render(context, request))
