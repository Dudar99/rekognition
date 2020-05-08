from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('collection', views.collection, name='create_collection'),
    path('collection/<int:id>', views.collection_faces, name='create_collection'),
    path('collection/<int:id>/video', views.video_results, name='video_results')
]
