from django.urls import path

from . import views

urlpatterns = [
    path(
        "api/test/tasks/<int:task_id>/annotation-count",
        views.AnnotationCountViewSet.as_view({"get": "retrieve"}),
        name="test-task-annotation-count",
    ),
]
