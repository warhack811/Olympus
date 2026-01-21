"""
Mami AI - Task Templates Package
--------------------------------
Scheduler tarafından çalıştırılacak görev şablonları.
"""

from app.services.tasks.templates.cognitive import EpisodeWorkerJob
from app.services.tasks.templates.maintenance import CleanupJob
from app.services.tasks.templates.system import HealthCheckJob

__all__ = ["EpisodeWorkerJob", "CleanupJob", "HealthCheckJob"]
