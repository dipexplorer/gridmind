from sqlalchemy.orm import Session
from models.system import SystemSettings

def get_settings(db: Session) -> SystemSettings:
    """
    Get system settings. Initializes default if none exist.
    """
    settings = db.query(SystemSettings).filter(SystemSettings.id == "default").first()
    if not settings:
        settings = SystemSettings(
            id="default",
            critical_threshold=75.0,
            high_threshold=55.0,
            medium_threshold=35.0
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

def update_settings(db: Session, critical: float, high: float, medium: float) -> SystemSettings:
    """
    Update system settings.
    """
    settings = get_settings(db)
    settings.critical_threshold = critical
    settings.high_threshold = high
    settings.medium_threshold = medium
    db.commit()
    db.refresh(settings)
    return settings
