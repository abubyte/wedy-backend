from sqlmodel import Session, select
from app.models.user_model import User, UserRole
from app.models.tariff_model import Tariff
from app.core.config import settings
from app.db.session import engine
import logging
from sqlalchemy.exc import SQLAlchemyError
import traceback
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def ensure_admin_exists():
    """Ensure that at least one admin user exists in the database."""
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    session = Session(engine)
    try:
        logger.info("Checking for existing admin user...")
        admin = session.exec(
            select(User).where(User.role == UserRole.admin)
        ).first()
        
        if not admin:
            logger.warning("No admin user found. Creating default admin...")
            try:
                admin = User(
                    firstname=settings.DEFAULT_ADMIN_FIRSTNAME,
                    lastname=settings.DEFAULT_ADMIN_LASTNAME,
                    login=settings.DEFAULT_ADMIN_EMAIL,
                    hashed_password=User.get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                    role=UserRole.admin,
                    is_verified=True,
                    is_active=True
                )
                logger.info("Adding admin user to session...")
                session.add(admin)
                logger.info("Committing admin user to database...")
                session.commit()
                logger.info("Refreshing admin user from database...")
                session.refresh(admin)
                logger.info(f"Default admin user created successfully with ID: {admin.id}")
                logger.warning(
                    "IMPORTANT: Please change the default admin password immediately! "
                    f"Default credentials: {settings.DEFAULT_ADMIN_EMAIL} / {settings.DEFAULT_ADMIN_PASSWORD}"
                )
            except Exception as e:
                logger.error(f"Error creating admin user: {str(e)}")
                logger.error(traceback.format_exc())
                raise
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()

async def ensure_free_tariff_exists():
    """Ensure that a free tariff exists in the database."""
    logger.info("Checking for existing free tariff...")
    session = Session(engine)
    try:
        free_tariff = session.exec(
            select(Tariff).where(Tariff.price == 0)
        ).first()
        
        if not free_tariff:
            logger.warning("No free tariff found. Creating default free tariff...")
            try:
                free_tariff = Tariff(
                    name="Free",
                    description="Basic free tariff with limited features",
                    price=0,
                    duration_days=30,  # 30 days trial
                    is_active=True,
                    search_priority=0,
                    has_website=False,
                    max_social_medias=2,
                    max_description_chars=200,
                    max_phone_numbers=1,
                    max_images=3,
                    created_at=datetime.utcnow()
                )
                logger.info("Adding free tariff to session...")
                session.add(free_tariff)
                logger.info("Committing free tariff to database...")
                session.commit()
                logger.info("Refreshing free tariff from database...")
                session.refresh(free_tariff)
                logger.info(f"Default free tariff created successfully with ID: {free_tariff.id}")
            except Exception as e:
                logger.error(f"Error creating free tariff: {str(e)}")
                logger.error(traceback.format_exc())
                raise
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()

async def ensure_users_have_tariff():
    """Ensure all users have a tariff assigned."""
    logger.info("Checking users without tariff...")
    session = Session(engine)
    try:
        # Get free tariff
        free_tariff = session.exec(
            select(Tariff).where(Tariff.price == 0)
        ).first()
        
        if not free_tariff:
            logger.warning("No free tariff found. Creating default free tariff...")
            free_tariff = Tariff(
                name="Free",
                description="Basic free tariff with limited features",
                price=0,
                duration_days=30,
                is_active=True,
                search_priority=0,
                has_website=False,
                max_social_medias=2,
                max_description_chars=200,
                max_phone_numbers=1,
                max_images=3,
                created_at=datetime.utcnow()
            )
            session.add(free_tariff)
            session.commit()
            session.refresh(free_tariff)
        
        # Get users without tariff
        users_without_tariff = session.exec(
            select(User).where(User.tariff_id.is_(None))
        ).all()
        
        if users_without_tariff:
            logger.warning(f"Found {len(users_without_tariff)} users without tariff. Assigning free tariff...")
            for user in users_without_tariff:
                user.tariff_id = free_tariff.id
                user.tariff_expires_at = datetime.utcnow() + timedelta(days=free_tariff.duration_days)
                session.add(user)
            
            session.commit()
            logger.info("Successfully assigned free tariff to all users without tariff")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close() 