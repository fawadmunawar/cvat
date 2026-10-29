from django.apps import AppConfig


class TestConfig(AppConfig):
    name = "cvat.apps.test"
    label = "test"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Required to define signals in the application
        import cvat.apps.test.signals

        assert cvat.apps.test.signals
