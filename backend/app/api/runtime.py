from fastapi import APIRouter, HTTPException

from backend.app.services.producer_task import (
    get_available_profiles,
    get_runtime_policy,
    set_runtime_profile,
)

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/polling-profiles")
def polling_profiles():
    return {"profiles": get_available_profiles()}


@router.get("/polling-config")
def polling_config():
    return get_runtime_policy()


@router.post("/polling-profile/{profile}")
def switch_polling_profile(profile: str):
    try:
        return set_runtime_profile(profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
