from fastapi import APIRouter, Depends
from api.endpoints import asset, timeseries, event, intelligence, user, notification, detail
from core.security import verify_supabase_token

api_router = APIRouter(dependencies=[Depends(verify_supabase_token)])
api_router.include_router(asset.router, tags=["Assets"])
api_router.include_router(detail.router, tags=["Asset Details"])
api_router.include_router(timeseries.router, tags=["TimeSeries Data"])
api_router.include_router(event.router, tags=["Events & Maintenance"])
api_router.include_router(intelligence.router, tags=["AI Intelligence"])
api_router.include_router(user.router, tags=["Users (Engineers)"])
api_router.include_router(notification.router, tags=["Alerts & Notifications"])
