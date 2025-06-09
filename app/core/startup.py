from sqlmodel import Session, select
from app.models.user_model import User, UserRole
from app.core.config import settings
from app.db.session import engine
import logging
from sqlalchemy.exc import SQLAlchemyError
import traceback

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
            except SQLAlchemyError as e:
                logger.error(f"Database error while creating admin: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                session.rollback()

                logger.error("Failed to create admin user, but continuing application startup")
            except Exception as e:
                logger.error(f"Unexpected error while creating admin: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                session.rollback()

                logger.error("Failed to create admin user, but continuing application startup")
        else:
            logger.info(f"Admin user already exists with ID: {admin.id}")
            logger.info(f"Admin login: {admin.login}")
    except Exception as e:
        logger.error(f"Error ensuring admin exists: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        session.rollback()

        logger.error("Failed to check/create admin user, but continuing application startup")
    finally:
        session.close() 
