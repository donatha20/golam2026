from __future__ import annotations

import os
import logging
from django.apps import AppConfig
from django.utils import timezone


class LoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loans"

    def ready(self) -> None:
        # Avoid running twice with Django's autoreloader.
        if os.environ.get("RUN_MAIN") != "true":
            return

        from .models import refresh_repayment_schedule_statuses

        logger = logging.getLogger(__name__)
        today = timezone.now().date()

        try:
            refresh_repayment_schedule_statuses(today)
            logger.info("Repayment schedule statuses refreshed on startup.")
        except Exception:
            logger.exception("Failed to refresh repayment schedule statuses on startup.")
