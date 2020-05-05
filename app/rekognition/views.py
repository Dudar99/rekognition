from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.template import loader
from .models import Collection

def collection(request):
    if request.method == 'GET':
        context = {
            'collections': Collection.objects.all(),
        }
        template = loader.get_template('rekognition/collections.html')
    else:
        pass

    return HttpResponse(template.render(context, request))


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    template = loader.get_template('rekognition/index.html')
    context = {
        'latest_question_list': [1,23],
    }
    return HttpResponse(template.render(context, request))