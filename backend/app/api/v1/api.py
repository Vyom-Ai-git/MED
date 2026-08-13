from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    organizations,
    branches,
    patients,
    tests,
    orders,
    samples,
    verification,
    reports,
    audit,
    dashboard,
    integrations,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(tests.router, prefix="/tests", tags=["tests"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(samples.router, prefix="/samples", tags=["samples"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])




