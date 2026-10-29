import logging

import redis
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from cvat.apps.engine.models import Job

logger = logging.getLogger("cvat.apps.test")

# Redis pub/sub channel the WebSocket service listens on.
PUBLISH_CHANNEL = "test:annotations-updated"

# Collapse a burst of job touches (one per chunk of a large annotation save)
# into at most one notification per second per task.
DEBOUNCE_SECONDS = 1


def get_redis_connection():
    return redis.Redis(
        host=settings.REDIS_INMEM_SETTINGS["HOST"],
        port=int(settings.REDIS_INMEM_SETTINGS["PORT"]),
        password=settings.REDIS_INMEM_SETTINGS["PASSWORD"] or None,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


@receiver(post_save, sender=Job)
def job_saved_publish_annotation_update(sender, instance: Job, **kwargs):
    """
    CVAT touches the job's updated_date after every annotation save
    (dataset_manager.task.TaskData._set_updated_date), so a post_save on Job
    is a reliable "annotations changed" signal without hooking into the bulk
    shape writes themselves.

    Publishing failures are logged and swallowed: the WebSocket notification
    is an optimization for the UI, and losing it must never break an
    annotation save.
    """
    try:
        r = get_redis_connection()
    except Exception:
        logger.warning("Redis unavailable; skipping WebSocket update notification", exc_info=True)
        return

    task_id = instance.segment.task_id
    debounce_key = f"test:debounce:{task_id}"

    try:
        # NX + short TTL: only the first touch within DEBOUNCE_SECONDS publishes.
        if r.set(debounce_key, "1", nx=True, ex=DEBOUNCE_SECONDS):
            r.publish(PUBLISH_CHANNEL, str(task_id))
    except Exception:
        logger.warning("Failed to publish WebSocket update notification", exc_info=True)
