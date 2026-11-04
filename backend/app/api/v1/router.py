from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)

# Future modules plug in here, e.g.:
# api_router.include_router(projects.router)   # projects / contracts
# api_router.include_router(documents.router)  # uploads + ingestion
# api_router.include_router(invoices.router)   # draft line items + evidence
# api_router.include_router(paypal.router)     # PayPal invoicing + webhooks
