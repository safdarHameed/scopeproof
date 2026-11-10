from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, health, invoices, projects, review, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(review.router)
api_router.include_router(invoices.router)
# PayPal webhooks plug in here, e.g. api_router.include_router(paypal.router)
