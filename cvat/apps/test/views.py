from django.db.models import Count
from rest_framework import mixins, serializers, viewsets
from rest_framework.response import Response

from cvat.apps.engine.models import LabeledShape, LabeledTrack, Task
from cvat.apps.engine.permissions import TaskPermission


class AnnotationCountSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(read_only=True)
    counts = serializers.ListField(child=serializers.DictField(), read_only=True)


def _count_annotations(task: Task) -> list[dict]:
    """
    One aggregate query per annotation table, grouped in the database.

    Shapes are counted per (label, type); tracks are counted per label and
    reported with the synthetic type "track". Results are merged in Python
    because the two tables are separate models and the merge cost is
    proportional to the number of classes, not the number of annotations.
    """
    shape_rows = (
        LabeledShape.objects.filter(job__segment__task=task)
        .values("label__name", "type")
        .annotate(count=Count("id"))
    )
    track_rows = (
        LabeledTrack.objects.filter(job__segment__task=task)
        .values("label__name")
        .annotate(count=Count("id"))
    )

    per_label: dict[str, dict] = {}
    for row in shape_rows:
        entry = per_label.setdefault(row["label__name"], {"count": 0, "by_type": {}})
        entry["count"] += row["count"]
        entry["by_type"][row["type"]] = row["count"]
    for row in track_rows:
        entry = per_label.setdefault(row["label__name"], {"count": 0, "by_type": {}})
        entry["count"] += row["count"]
        entry["by_type"]["track"] = row["count"]

    return [
        {"label": label, "count": data["count"], "by_type": data["by_type"]}
        for label, data in sorted(per_label.items())
    ]


class AnnotationCountViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """
    Returns the number of annotations per class for a task, read from the database.

    Access control reuses CVAT's own machinery: the default authentication
    classes (session/token) refuse anonymous requests, and TaskPermission
    (scope "view") delegates to CVAT's IAM/OPA service, which refuses users
    who cannot view the task.
    """

    serializer_class = AnnotationCountSerializer
    queryset = Task.objects.all()
    lookup_url_kwarg = "task_id"
    iam_permission_class = TaskPermission

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(
            {"task_id": task.id, "counts": _count_annotations(task)}
        )
        return Response(serializer.data)
