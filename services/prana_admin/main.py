from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from services.prana_admin.i18n import translator


BASE_DIR = Path(__file__).resolve().parent
USER_STATUSES = ("registered", "email_verified", "pending_payment", "active", "expired", "suspended")
PAGE_SIZE = 25

app = FastAPI(title="PRANA ELEX Admin", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _db():
    return firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)


def _operator(x_goog_authenticated_user_email: str | None = Header(default=None)) -> str:
    prefix = "accounts.google.com:"
    if (
        not x_goog_authenticated_user_email
        and os.getenv("PRANA_ADMIN_ENV") == "development"
        and not os.getenv("K_SERVICE")
    ):
        development_email = os.getenv("PRANA_ADMIN_DEV_EMAIL", "").strip().lower()
        if development_email:
            return development_email
    if not x_goog_authenticated_user_email or not x_goog_authenticated_user_email.startswith(prefix):
        raise HTTPException(401, "IAP authentication required")
    email = x_goog_authenticated_user_email[len(prefix):].lower()
    allowed = {item.strip().lower() for item in os.getenv("PRANA_ADMIN_ALLOWED_EMAILS", "").split(",") if item.strip()}
    if allowed and email not in allowed:
        raise HTTPException(403, "Operator is not allowed")
    return email


def _audit(db, operator: str, action: str, target_uid: str, details: dict | None = None) -> None:
    db.collection("admin_audit").add(
        {"operator": operator, "action": action, "target_uid": target_uid, "details": details or {},
         "created_at": firestore.SERVER_TIMESTAMP}
    )


def _locale(request: Request) -> str:
    value = request.cookies.get("prana_admin_locale", "en")
    return value if value in {"en", "vi"} else "en"


def _format_datetime(value) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return str(value)


def _render(request: Request, template: str, operator: str, title: str, active_nav: str, **context):
    locale = _locale(request)
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"operator": operator, "locale": locale, "t": translator(locale), "title": title,
                 "active_nav": active_nav, "return_path": request.url.path + (f"?{request.url.query}" if request.url.query else ""),
                 "notice": request.query_params.get("notice", ""), **context},
    )


def _redirect(path: str, notice: str) -> RedirectResponse:
    joiner = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{joiner}notice={notice}", status_code=303)


def _cursor(uid: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"uid": uid}).encode()).decode().rstrip("=")


def _decode_cursor(value: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        uid = json.loads(raw).get("uid", "")
        return uid if isinstance(uid, str) else ""
    except (ValueError, TypeError, json.JSONDecodeError):
        return ""


def _plan_rows(db) -> list[dict]:
    return [{"id": snap.id, **snap.to_dict()} for snap in db.collection("plans").stream()]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/locale/{locale}")
def set_locale(locale: str, next: str = "/"):
    if locale not in {"en", "vi"}:
        raise HTTPException(404, "Unsupported locale")
    parsed = urlsplit(next)
    destination = next if next.startswith("/") and not next.startswith("//") and not parsed.scheme and not parsed.netloc else "/"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie("prana_admin_locale", locale, max_age=31536000, httponly=True, samesite="lax", secure=True)
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    users = [{"uid": snap.id, **snap.to_dict()} for snap in db.collection("users").stream()]
    counts = {status: sum(1 for item in users if item.get("status") == status) for status in USER_STATUSES}
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = db.collection("system_usage").document(f"monthly-{period}").get().to_dict() or {}
    attention = [item for item in users if item.get("status") in {"registered", "email_verified", "pending_payment"}][:8]
    activity = []
    try:
        for snap in db.collection("admin_audit").order_by("created_at", direction=firestore.Query.DESCENDING).limit(8).stream():
            item = snap.to_dict()
            activity.append({**item, "when": _format_datetime(item.get("created_at"))})
    except Exception:
        activity = []
    metrics = {"total": len(users), "active": counts["active"],
               "pending": counts["registered"] + counts["email_verified"] + counts["pending_payment"],
               "audio_minutes": int(usage.get("used_audio_seconds", 0)) / 60}
    return _render(request, "dashboard.html", email, "Dashboard", "dashboard", metrics=metrics,
                   attention=attention, activity=activity)


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, q: str = "", status: str = "", plan: str = "", cursor: str = "",
               operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    normalized = q.strip().lower()
    plans = _plan_rows(db)
    items = []
    exact = db.collection("users").document(q.strip()).get() if q.strip() else None
    if exact is not None and exact.exists:
        data = exact.to_dict()
        if (not status or data.get("status") == status) and (not plan or data.get("plan_id") == plan):
            items = [{"uid": exact.id, **data}]
        has_more = False
    else:
        query = db.collection("users")
        if normalized:
            query = query.where(filter=FieldFilter("email_lower", ">=", normalized)).where(
                filter=FieldFilter("email_lower", "<=", normalized + "\uf8ff")
            ).order_by("email_lower")
        else:
            query = query.order_by("__name__")
        if status in USER_STATUSES:
            query = query.where(filter=FieldFilter("status", "==", status))
        if plan:
            query = query.where(filter=FieldFilter("plan_id", "==", plan))
        cursor_uid = _decode_cursor(cursor)
        if cursor_uid:
            cursor_doc = db.collection("users").document(cursor_uid).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)
        snapshots = list(query.limit(PAGE_SIZE + 1).stream())
        has_more = len(snapshots) > PAGE_SIZE
        items = [{"uid": snap.id, **snap.to_dict()} for snap in snapshots[:PAGE_SIZE]]
    for item in items:
        item["expires"] = _format_datetime(item.get("subscription_expires_at"))
    filters = {"q": q, "status": status, "plan": plan}
    base_params = {key: value for key, value in filters.items() if value}
    first_query = urlencode(base_params)
    next_query = urlencode({**base_params, "cursor": _cursor(items[-1]["uid"])}) if has_more and items else ""
    return _render(request, "users.html", email, "Users", "users", users=items, plans=plans,
                   statuses=USER_STATUSES, filters=filters, cursor=cursor, first_query=first_query, next_query=next_query)


@app.get("/users/{uid}", response_class=HTMLResponse)
def user_detail(request: Request, uid: str,
                operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    snap = db.collection("users").document(uid).get()
    if not snap.exists:
        raise HTTPException(404, "User not found")
    user = snap.to_dict()
    user["expires"] = _format_datetime(user.get("subscription_expires_at"))
    devices = [{"id": item.id, **item.to_dict()} for item in snap.reference.collection("devices").stream()]
    usage = [{"period": item.id, "minutes": int(item.to_dict().get("used_audio_seconds", 0)) / 60,
              "requests": int(item.to_dict().get("request_count", 0))}
             for item in snap.reference.collection("usage").stream()]
    return _render(request, "user_detail.html", email, user.get("email", "User"), "users", uid=uid,
                   user=user, plans=_plan_rows(db), devices=devices, usage=usage)


@app.post("/users/{uid}/activate")
def activate_user(uid: str, plan_id: str = Form(), days: int = Form(30),
                  operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    if not db.collection("plans").document(plan_id).get().exists:
        raise HTTPException(400, "Plan not found")
    user_ref = db.collection("users").document(uid)
    current = user_ref.get().to_dict() or {}
    now = datetime.now(timezone.utc)
    current_expiry = current.get("subscription_expires_at")
    base = current_expiry if current_expiry and current_expiry > now else now
    user_ref.update({"status": "active", "plan_id": plan_id,
                     "subscription_expires_at": base + timedelta(days=max(1, days)),
                     "updated_at": firestore.SERVER_TIMESTAMP})
    _audit(db, email, "subscription.activate", uid, {"plan_id": plan_id, "days": days})
    return _redirect(f"/users/{uid}", "subscription_updated")


@app.post("/users/{uid}/status")
def set_status(uid: str, status: str = Form(),
               operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    if status not in {"active", "expired", "suspended"}:
        raise HTTPException(400, "Invalid status")
    db = _db()
    db.collection("users").document(uid).update({"status": status, "updated_at": firestore.SERVER_TIMESTAMP})
    _audit(db, email, f"user.{status}", uid)
    return _redirect(f"/users/{uid}", "status_updated")


@app.post("/users/{uid}/devices/reset")
def reset_devices(uid: str, operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    batch = db.batch()
    for device in db.collection("users").document(uid).collection("devices").stream():
        batch.update(device.reference, {"active": False, "revoked_at": firestore.SERVER_TIMESTAMP})
    batch.commit()
    _audit(db, email, "devices.reset", uid)
    return _redirect(f"/users/{uid}", "devices_revoked")


@app.post("/users/{uid}/devices/{device_id}/allow-reenrollment")
def allow_device_reenrollment(uid: str, device_id: str,
                              operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    db = _db()
    device_ref = db.collection("users").document(uid).collection("devices").document(device_id)
    snapshot = device_ref.get()
    if not snapshot.exists:
        raise HTTPException(404, "Device not found")
    if snapshot.to_dict().get("active", False):
        raise HTTPException(409, "Revoke the device before allowing re-enrollment")
    device_ref.delete()
    _audit(db, email, "device.allow_reenrollment", uid, {"device_id": device_id})
    return _redirect(f"/users/{uid}", "device_reenrollment")


@app.get("/plans", response_class=HTMLResponse)
def plans_page(request: Request, operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    return _render(request, "plans.html", email, "Plans", "plans", plans=_plan_rows(_db()))


@app.post("/plans")
def save_plan(plan_id: str = Form(), name: str = Form(), monthly_audio_minutes: int | None = Form(None),
              requests_per_minute: int = Form(), monthly_audio_seconds: int | None = Form(None),
              operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    seconds = monthly_audio_seconds if monthly_audio_seconds is not None else int(monthly_audio_minutes or 0) * 60
    if seconds <= 0 or requests_per_minute <= 0:
        raise HTTPException(400, "Plan limits must be positive")
    db = _db()
    db.collection("plans").document(plan_id).set(
        {"name": name, "monthly_audio_seconds": seconds, "requests_per_minute": requests_per_minute,
         "max_concurrency": 2, "max_devices": 2, "updated_at": firestore.SERVER_TIMESTAMP}, merge=True
    )
    _audit(db, email, "plan.save", plan_id)
    return _redirect("/plans", "plan_saved")
