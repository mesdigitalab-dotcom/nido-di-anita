# apps.py
import os
import logging
from django.apps import AppConfig
from .ical_manager import ICalManager

logger = logging.getLogger(__name__)
_ical_manager: ICalManager | None = None


def get_ical_manager() -> ICalManager:
    if _ical_manager is None:
        raise RuntimeError(
            "ICalManager non inizializzato. "
            "Assicurati che PrenotazioniConfig.ready() sia stato chiamato."
        )
    return _ical_manager


class PrenotazioniConfig(AppConfig):
    name = "app"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import sys

        if _is_manage_command():
            return
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        global _ical_manager
        from django.conf import settings
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        _ical_manager = ICalManager(
            external_urls=settings.ICAL_EXTERNAL_URLS,
            cache_dir=settings.ICAL_CACHE_DIR,
        )
        _ical_manager.fetch_external_icals()

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=_ical_manager.fetch_external_icals,
            trigger=IntervalTrigger(minutes=15),
            id="fetch_external_icals",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("ICalManager avviato, scheduler attivo ogni 15 min.")


def _is_manage_command():
    import sys
    skip = {"migrate", "makemigrations", "shell", "collectstatic", "createsuperuser"}
    return len(sys.argv) > 1 and sys.argv[1] in skip