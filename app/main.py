import logging
from contextlib import asynccontextmanager
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from app.core.config import settings
from app.external_services.s3_service import S3Service
from app.db.session import create_db_and_tables
from app.core.startup import ensure_admin_exists, ensure_free_tariff_exists, ensure_users_have_tariff
from fastapi.openapi.utils import get_openapi

from app.routers.auth_router import router as auth_router
from app.routers.user_router import router as user_router
from app.routers.card_router import router as card_router
from app.routers.category_router import router as category_router
from app.routers.interaction_router import router as interaction_router
from app.routers.tariff_router import router as tariff_router

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    print("Database and tables created.")
    try:
        logger.info("Creating database and tables...")
        create_db_and_tables()
        logger.info("Database and tables created successfully")
        
        # Ensure admin exists
        logger.info("Checking for admin user...")
        await ensure_admin_exists()
        logger.info("Admin user check completed")
        
        logger.info("Checking for free tariff...")
        await ensure_free_tariff_exists()
        logger.info("Free tariff check completed")
        
        logger.info("Checking users without tariff...")
        await ensure_users_have_tariff()
        logger.info("User tariff check completed")
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    yield

app = FastAPI(
    # title=settings.PROJECT_NAME,
    # version=settings.VERSION,
    # description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()[0].get("msg", "Validation Error")}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "errors": exc.errors()
        }
    )

# Add JWT bearer authentication to Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Wedy API",
        version="1.0.0",
        description="Web API for Wedy",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(category_router)
app.include_router(card_router)
app.include_router(interaction_router)
app.include_router(tariff_router)

@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def root():
    return {"message": "Service is up"}

@app.get("/test-s3", include_in_schema=False)
async def test_s3():
    try:
        s3_service = S3Service()
        # Try to list objects in the bucket
        response = s3_service.s3_client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, MaxKeys=1)
        return {"status": "success", "message": "S3 connection successful"}
    except Exception as e:
        logger.error(f"S3 connection test failed: {str(e)}")
        return {"status": "error", "message": f"S3 connection failed: {str(e)}"}
