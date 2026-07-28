from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from services.prana_admin.i18n import translator


BASE_DIR = Path(__file__).resolve().parent
USER_STATUSES = ("registered", "email_verified", "pending_payment", "active", "expired", "suspended")
EDITABLE_PLAN_IDS = ("free", "plus", "pro")
PAGE_SIZE = 25
AUDIT_PAGE_SIZE = 50
CSRF_COOKIE = "prana_admin_csrf"
CSRF_MAX_AGE = 8 * 60 * 60

app = FastAPI(title="PRANA ELEX Admin", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _error_response(request: Request, status: int, detail: str = ""):
    locale = _locale(request)
    safe_status = status if status in {403, 404, 409, 422, 500, 503} else 500
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        status_code=status,
        context={
            "locale": locale,
            "t": translator(locale),
            "status": safe_status,
            "detail": detail if safe_status < 500 else "",
        },
    )


@app.exception_handler(HTTPException)
async def admin_http_error(request: Request, exc: HTTPException):
    return _error_response(request, exc.status_code, str(exc.detail))


@app.exception_handler(Exception)
async def admin_unhandled_error(request: Request, _exc: Exception):
    return _error_response(request, 500)


@app.exception_handler(RequestValidationError)
async def admin_validation_error(request: Request, _exc: RequestValidationError):
    return _error_response(request, 422, "Review the submitted form values")


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
    if os.getenv("K_SERVICE") and not allowed:
        raise HTTPException(503, "Admin allowlist is not configured")
    if allowed and email not in allowed:
        raise HTTPException(403, "Operator is not allowed")
    return email


def _csrf_secret() -> bytes:
    value = os.getenv("PRANA_ADMIN_CSRF_SECRET", "")
    if value:
        return value.encode("utf-8")
    if os.getenv("K_SERVICE"):
        raise HTTPException(503, "Admin CSRF secret is not configured")
    return b"prana-admin-development-csrf-secret"


def _csrf_token(operator: str, now: int | None = None) -> str:
    issued_at = now or int(datetime.now(timezone.utc).timestamp())
    payload = f"{operator}:{issued_at}:{secrets.token_urlsafe(18)}"
    signature = hmac.new(_csrf_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode().rstrip("=")


def _verify_csrf(request: Request, operator: str, form_token: str) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    if not form_token or not hmac.compare_digest(cookie_token, form_token):
        raise HTTPException(403, "Invalid CSRF token")
    try:
        raw = base64.urlsafe_b64decode(form_token + "=" * (-len(form_token) % 4)).decode()
        token_operator, issued_at, nonce, signature = raw.rsplit(":", 3)
        payload = f"{token_operator}:{issued_at}:{nonce}"
        expected = hmac.new(_csrf_secret(), payload.encode(), hashlib.sha256).hexdigest()
        age = int(datetime.now(timezone.utc).timestamp()) - int(issued_at)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(403, "Invalid CSRF token") from None
    if (
        token_operator != operator
        or age < 0
        or age > CSRF_MAX_AGE
        or not hmac.compare_digest(signature, expected)
    ):
        raise HTTPException(403, "Invalid CSRF token")


def _audit_payload(
    operator: str,
    action: str,
    target_uid: str,
    details: dict | None = None,
    request_id: str = "",
) -> dict:
    return {
        "operator": operator,
        "action": action,
        "target_uid": target_uid,
        "details": details or {},
        "request_id": request_id,
        "created_at": firestore.SERVER_TIMESTAMP,
    }


def _write_audit(
    writer,
    db,
    operator: str,
    action: str,
    target_uid: str,
    details: dict | None = None,
    request_id: str = "",
) -> None:
    writer.set(
        db.collection("admin_audit").document(),
        _audit_payload(operator, action, target_uid, details, request_id),
    )


def _station_stop_transition(registry: dict) -> tuple[bool, dict | None]:
    desired = dict(registry.get("desired_state") or {})
    generation = int(desired.get("generation", 0))
    if desired.get("running", False):
        desired["running"] = False
        desired["generation"] = generation + 1
        return False, {
            "desired_state": desired,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    observed = int(registry.get("observed_generation", 0))
    capture_state = str(registry.get("capture_state", "idle"))
    return observed >= generation and capture_state in {"idle", "error"}, None


def _station_transfer_data(station_id: str, registry: dict) -> tuple[dict, dict]:
    desired = dict(registry.get("desired_state") or {})
    desired["running"] = False
    registry_update = {
        "active": True,
        "desired_state": desired,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    projection = {
        "station_id": station_id,
        "name": registry.get("name", "PRANA station"),
        "platform": registry.get("platform", "unknown"),
        "active": True,
        "online": False,
        "capture_state": "idle",
        "desired_state": desired,
        "observed_generation": 0,
        "session_id": "",
        "sequence": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    return registry_update, projection


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
    token = _csrf_token(operator)
    response = templates.TemplateResponse(
        request=request,
        name=template,
        context={"operator": operator, "locale": locale, "t": translator(locale), "title": title,
                 "active_nav": active_nav, "return_path": request.url.path + (f"?{request.url.query}" if request.url.query else ""),
                 "notice": request.query_params.get("notice", ""), "csrf_token": token, **context},
    )
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=CSRF_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return response


def _redirect(path: str, notice: str) -> RedirectResponse:
    joiner = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{joiner}notice={notice}", status_code=303)


def _request_id(request: Request) -> str:
    trace = request.headers.get("X-Cloud-Trace-Context", "")
    return trace.split("/", 1)[0][:128] or request.headers.get("X-Request-ID", "")[:128]


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
    plans = []
    for snap in db.collection("plans").stream():
        item = {"id": snap.id, **snap.to_dict()}
        item["audio_seconds_limit"] = int(
            item.get("audio_seconds_limit") or item.get("monthly_audio_seconds") or 0
        )
        item.setdefault("quota_period", "monthly")
        item.setdefault("availability", "available")
        item.setdefault("sort_order", 0)
        item.setdefault("max_stations", 2)
        item.setdefault("live_log_limit", 10 if snap.id == "free" else 0)
        item.setdefault(
            "history_unlock_delay_days",
            1 if snap.id == "free" else 0,
        )
        plans.append(item)
    return sorted(plans, key=lambda item: (int(item["sort_order"]), item["id"]))


def _aggregate_count(query) -> int:
    result = query.count(alias="total").get()
    return int(result[0][0].value) if result else 0


def _station_row(db, snap, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    data = snap.to_dict()
    last_seen = data.get("last_seen_at")
    online = (
        bool(data.get("active", True))
        and isinstance(last_seen, datetime)
        and (now - last_seen).total_seconds() <= 15
    )
    owner_uid = data.get("owner_uid", "")
    owner = db.collection("users").document(owner_uid).get() if owner_uid else None
    owner_data = owner.to_dict() if owner is not None and owner.exists else {}
    return {
        "id": snap.id,
        **data,
        "online": online,
        "owner_email": owner_data.get("email", "-"),
        "last_seen": _format_datetime(last_seen),
    }


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
    counts = {
        status: _aggregate_count(
            db.collection("users").where(filter=FieldFilter("status", "==", status))
        )
        for status in USER_STATUSES
    }
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = db.collection("system_usage").document(f"monthly-{period}").get().to_dict() or {}
    attention = []
    for snap in (
        db.collection("station_registry")
        .order_by("last_seen_at")
        .limit(8)
        .stream()
    ):
        row = _station_row(db, snap)
        if not row["online"] or row.get("last_error"):
            attention.append(row)
    activity = []
    try:
        for snap in db.collection("admin_audit").order_by("created_at", direction=firestore.Query.DESCENDING).limit(8).stream():
            item = snap.to_dict()
            activity.append({**item, "when": _format_datetime(item.get("created_at"))})
    except Exception:
        activity = []
    metrics = {"total": sum(counts.values()), "active": counts["active"],
               "pending": counts["registered"] + counts["email_verified"] + counts["pending_payment"],
               "audio_minutes": int(usage.get("used_audio_seconds", 0)) / 60}
    return _render(request, "dashboard.html", email, "Dashboard", "dashboard", metrics=metrics,
                   attention=attention, activity=activity)


@app.get("/stations", response_class=HTMLResponse)
def stations_page(
    request: Request,
    q: str = "",
    state: str = "",
    platform: str = "",
    error: str = "",
    cursor: str = "",
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    db = _db()
    query = db.collection("station_registry").order_by("__name__")
    normalized = q.strip().lower()
    if len(normalized) == 32 and all(char in "0123456789abcdef" for char in normalized):
        snap = db.collection("station_registry").document(normalized).get()
        snapshots = [snap] if snap.exists else []
        has_more = False
    else:
        if normalized and "@" in normalized:
            owners = list(
                db.collection("users")
                .where(filter=FieldFilter("email_lower", "==", normalized))
                .limit(1)
                .stream()
            )
            if not owners:
                snapshots = []
                has_more = False
                query = None
            else:
                query = query.where(filter=FieldFilter("owner_uid", "==", owners[0].id))
        if query is not None:
            if platform:
                query = query.where(filter=FieldFilter("platform", "==", platform))
            cursor_id = _decode_cursor(cursor)
            if cursor_id:
                cursor_doc = db.collection("station_registry").document(cursor_id).get()
                if cursor_doc.exists:
                    query = query.start_after(cursor_doc)
            snapshots = list(query.limit(PAGE_SIZE * 3 + 1).stream())
            has_more = len(snapshots) > PAGE_SIZE * 3
            snapshots = snapshots[: PAGE_SIZE * 3]
    rows = [_station_row(db, snap) for snap in snapshots]
    if state == "online":
        rows = [row for row in rows if row["online"]]
    elif state == "offline":
        rows = [row for row in rows if not row["online"]]
    if error == "yes":
        rows = [row for row in rows if row.get("last_error")]
    rows = rows[:PAGE_SIZE]
    filters = {"q": q, "state": state, "platform": platform, "error": error}
    base = {key: value for key, value in filters.items() if value}
    next_query = (
        urlencode({**base, "cursor": _cursor(rows[-1]["id"])})
        if has_more and rows
        else ""
    )
    return _render(
        request,
        "stations.html",
        email,
        "Stations",
        "stations",
        stations=rows,
        filters=filters,
        cursor=cursor,
        first_query=urlencode(base),
        next_query=next_query,
    )


@app.get("/stations/{station_id}", response_class=HTMLResponse)
def station_detail(
    request: Request,
    station_id: str,
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    db = _db()
    snap = db.collection("station_registry").document(station_id).get()
    if not snap.exists:
        raise HTTPException(404, "Station not found")
    station = _station_row(db, snap)
    transfers = []
    for audit in (
        db.collection("admin_audit")
        .where(filter=FieldFilter("details.station_id", "==", station_id))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(20)
        .stream()
    ):
        data = audit.to_dict()
        transfers.append({**data, "when": _format_datetime(data.get("created_at"))})
    return _render(
        request,
        "station_detail.html",
        email,
        station.get("name", station_id),
        "stations",
        station=station,
        transfers=transfers,
    )


@app.post("/stations/{station_id}/stop")
def stop_station(
    request: Request,
    station_id: str,
    csrf_token: str = Form(),
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    db = _db()
    registry_ref = db.collection("station_registry").document(station_id)

    @firestore.transactional
    def run(tx):
        snap = registry_ref.get(transaction=tx)
        if not snap.exists:
            raise HTTPException(404, "Station not found")
        before = snap.to_dict()
        desired = dict(before.get("desired_state") or {})
        if desired.get("running", False):
            desired["running"] = False
            desired["generation"] = int(desired.get("generation", 0)) + 1
        update = {"desired_state": desired, "updated_at": firestore.SERVER_TIMESTAMP}
        tx.update(registry_ref, update)
        owner_uid = before.get("owner_uid", "")
        if owner_uid:
            tx.set(
                db.collection("users").document(owner_uid).collection("stations").document(station_id),
                update,
                merge=True,
            )
        _write_audit(
            tx,
            db,
            email,
            "station.stop",
            owner_uid,
            {"station_id": station_id, "before": before.get("desired_state"), "after": desired},
            _request_id(request),
        )

    run(db.transaction())
    return _redirect(f"/stations/{station_id}", "station_stop_sent")


@app.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    operator_filter: str = "",
    action: str = "",
    target: str = "",
    date_from: str = "",
    date_to: str = "",
    cursor: str = "",
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    db = _db()
    query = db.collection("admin_audit").order_by(
        "created_at",
        direction=firestore.Query.DESCENDING,
    )
    if operator_filter:
        query = query.where(filter=FieldFilter("operator", "==", operator_filter.strip().lower()))
    if action:
        query = query.where(filter=FieldFilter("action", "==", action.strip()))
    if target:
        query = query.where(filter=FieldFilter("target_uid", "==", target.strip()))
    try:
        if date_from:
            query = query.where(
                filter=FieldFilter(
                    "created_at",
                    ">=",
                    datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc),
                )
            )
        if date_to:
            query = query.where(
                filter=FieldFilter(
                    "created_at",
                    "<",
                    datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
                    + timedelta(days=1),
                )
            )
    except ValueError as exc:
        raise HTTPException(422, "Invalid audit date") from exc
    cursor_id = _decode_cursor(cursor)
    if cursor_id:
        cursor_doc = db.collection("admin_audit").document(cursor_id).get()
        if cursor_doc.exists:
            query = query.start_after(cursor_doc)
    snapshots = list(query.limit(AUDIT_PAGE_SIZE + 1).stream())
    has_more = len(snapshots) > AUDIT_PAGE_SIZE
    entries = []
    for snap in snapshots[:AUDIT_PAGE_SIZE]:
        data = snap.to_dict()
        entries.append(
            {
                "id": snap.id,
                **data,
                "when": _format_datetime(data.get("created_at")),
                "details_json": json.dumps(data.get("details") or {}, ensure_ascii=False, indent=2, default=str),
            }
        )
    filters = {
        "operator_filter": operator_filter,
        "action": action,
        "target": target,
        "date_from": date_from,
        "date_to": date_to,
    }
    base = {key: value for key, value in filters.items() if value}
    next_query = (
        urlencode({**base, "cursor": _cursor(entries[-1]["id"])})
        if has_more and entries
        else ""
    )
    return _render(
        request,
        "audit.html",
        email,
        "Audit",
        "audit",
        entries=entries,
        filters=filters,
        cursor=cursor,
        first_query=urlencode(base),
        next_query=next_query,
    )


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
    user["last_login"] = _format_datetime(user.get("last_login_at"))
    user["last_activity"] = _format_datetime(user.get("updated_at"))
    devices = [{"id": item.id, **item.to_dict()} for item in snap.reference.collection("devices").stream()]
    stations = [{"id": item.id, **item.to_dict()} for item in snap.reference.collection("stations").stream()]
    usage = [{"period": item.id, "minutes": int(item.to_dict().get("used_audio_seconds", 0)) / 60,
              "requests": int(item.to_dict().get("request_count", 0))}
             for item in snap.reference.collection("usage").stream()]
    usage.sort(key=lambda item: item["period"], reverse=True)
    timeline = []
    for audit in (
        db.collection("admin_audit")
        .where(filter=FieldFilter("target_uid", "==", uid))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(10)
        .stream()
    ):
        data = audit.to_dict()
        timeline.append({**data, "when": _format_datetime(data.get("created_at"))})
    return _render(request, "user_detail.html", email, user.get("email", "User"), "users", uid=uid,
                   user=user, plans=_plan_rows(db), devices=devices, stations=stations, usage=usage,
                   timeline=timeline)


@app.post("/users/{uid}/status")
def set_status(request: Request, uid: str, status: str = Form(), csrf_token: str = Form(),
               operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    if status not in {"active", "suspended"}:
        raise HTTPException(400, "Invalid status")
    db = _db()
    user_ref = db.collection("users").document(uid)
    snapshot = user_ref.get()
    if not snapshot.exists:
        raise HTTPException(404, "User not found")
    user = snapshot.to_dict()
    if status == "active" and not user.get("email_verified"):
        raise HTTPException(409, "Email must be verified before reactivation")
    update = {"status": status, "updated_at": firestore.SERVER_TIMESTAMP}
    if status == "active" and not user.get("plan_id"):
        update.update({"plan_id": "free", "subscription_expires_at": None})
    batch = db.batch()
    batch.update(user_ref, update)
    _write_audit(
        batch,
        db,
        email,
        f"user.{status}",
        uid,
        {
            "before": user,
            "after": {
                key: value for key, value in update.items() if key != "updated_at"
            },
        },
        _request_id(request),
    )
    batch.commit()
    return _redirect(f"/users/{uid}", "status_updated")


@app.post("/users/{uid}/devices/reset")
def reset_devices(request: Request, uid: str, csrf_token: str = Form(),
                  operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    db = _db()
    user_ref = db.collection("users").document(uid)
    if not user_ref.get().exists:
        raise HTTPException(404, "User not found")
    devices = list(user_ref.collection("devices").stream())
    batch = db.batch()
    for device in devices:
        batch.update(device.reference, {"active": False, "revoked_at": firestore.SERVER_TIMESTAMP})
    _write_audit(
        batch,
        db,
        email,
        "devices.reset",
        uid,
        {"revoked_count": len(devices), "device_ids": [item.id for item in devices]},
        _request_id(request),
    )
    batch.commit()
    return _redirect(f"/users/{uid}", "devices_revoked")


@app.post("/users/{uid}/devices/{device_id}/allow-reenrollment")
def allow_device_reenrollment(uid: str, device_id: str,
                              request: Request,
                              csrf_token: str = Form(),
                              operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    db = _db()
    device_ref = db.collection("users").document(uid).collection("devices").document(device_id)
    snapshot = device_ref.get()
    if not snapshot.exists:
        raise HTTPException(404, "Device not found")
    if snapshot.to_dict().get("active", False):
        raise HTTPException(409, "Revoke the device before allowing re-enrollment")
    before = snapshot.to_dict()
    batch = db.batch()
    batch.delete(device_ref)
    _write_audit(
        batch,
        db,
        email,
        "device.allow_reenrollment",
        uid,
        {"device_id": device_id, "before": before},
        _request_id(request),
    )
    batch.commit()
    return _redirect(f"/users/{uid}", "device_reenrollment")


@app.post("/users/{uid}/stations/{station_id}/transfer")
def transfer_station(
    request: Request,
    uid: str,
    station_id: str,
    target_email: str = Form(),
    confirm_email: str = Form(),
    csrf_token: str = Form(),
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    target_email = target_email.strip().lower()
    if confirm_email.strip().lower() != target_email:
        raise HTTPException(422, "Target email confirmation does not match")
    if not target_email or "@" not in target_email:
        raise HTTPException(422, "A valid target email is required")
    db = _db()
    matches = list(
        db.collection("users")
        .where(filter=FieldFilter("email_lower", "==", target_email))
        .limit(2)
        .stream()
    )
    if len(matches) != 1:
        raise HTTPException(404, "Target account was not found")
    target_uid = matches[0].id
    if target_uid == uid:
        raise HTTPException(409, "Station already belongs to this account")

    registry_ref = db.collection("station_registry").document(station_id)
    source_projection = db.collection("users").document(uid).collection("stations").document(station_id)
    target_user_ref = db.collection("users").document(target_uid)
    target_projection = target_user_ref.collection("stations").document(station_id)

    @firestore.transactional
    def run(tx):
        registry_snap = registry_ref.get(transaction=tx)
        target_user_snap = target_user_ref.get(transaction=tx)
        target_projection_snap = target_projection.get(transaction=tx)
        if not registry_snap.exists or registry_snap.to_dict().get("owner_uid") != uid:
            raise HTTPException(404, "Station was not found for the source account")
        target_user = target_user_snap.to_dict() if target_user_snap.exists else {}
        if not target_user.get("email_verified") or target_user.get("status") != "active":
            raise HTTPException(409, "Target account must be active and email verified")
        plan_id = target_user.get("plan_id")
        plan_snap = db.collection("plans").document(plan_id or "").get(transaction=tx)
        max_stations = int((plan_snap.to_dict() if plan_snap.exists else {}).get("max_stations", 2))
        target_stations = target_user_ref.collection("stations")
        active_target = list(target_stations.where("active", "==", True).stream(transaction=tx))
        target_projection_data = (
            target_projection_snap.to_dict() if target_projection_snap.exists else {}
        )
        if not target_projection_data.get("active", False) and len(active_target) >= max_stations:
            raise HTTPException(409, "Target account has reached its station limit")
        registry = registry_snap.to_dict()
        ready_to_transfer, stop_update = _station_stop_transition(registry)
        if not ready_to_transfer:
            if stop_update is not None:
                tx.update(registry_ref, stop_update)
                tx.set(
                    source_projection,
                    {
                        "desired_state": stop_update["desired_state"],
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    },
                    merge=True,
                )
            return "stopping"
        registry_update, projection = _station_transfer_data(station_id, registry)
        registry_update["owner_uid"] = target_uid
        tx.update(
            registry_ref,
            registry_update,
        )
        tx.set(
            source_projection,
            {
                "active": False,
                "online": False,
                "transferred_to": target_uid,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        tx.set(target_projection, projection)
        _write_audit(
            tx,
            db,
            email,
            "station.transfer",
            uid,
            {
                "station_id": station_id,
                "target_uid": target_uid,
                "target_email": target_email,
                "before": registry,
                "after": {
                    key: value
                    for key, value in registry_update.items()
                    if key != "updated_at"
                },
            },
            _request_id(request),
        )
        return "transferred"

    outcome = run(db.transaction())
    if outcome == "stopping":
        return _redirect(f"/users/{uid}", "station_stopping")
    return _redirect(f"/users/{uid}", "station_transferred")


@app.get("/plans", response_class=HTMLResponse)
def plans_page(request: Request, operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email")):
    email = _operator(operator)
    return _render(request, "plans.html", email, "Plans", "plans", plans=_plan_rows(_db()))


@app.post("/plans/{plan_id}")
def update_plan(
    request: Request,
    plan_id: str,
    name: str = Form(...),
    daily_minutes: int = Form(...),
    requests_per_minute: int = Form(...),
    max_concurrency: int = Form(...),
    max_devices: int = Form(...),
    max_stations: int = Form(2),
    live_log_limit: int | None = Form(None),
    history_unlock_delay_days: int | None = Form(None),
    sort_order: int = Form(...),
    csrf_token: str = Form(),
    operator: str = Header(default=None, alias="X-Goog-Authenticated-User-Email"),
):
    email = _operator(operator)
    _verify_csrf(request, email, csrf_token)
    if plan_id not in EDITABLE_PLAN_IDS:
        raise HTTPException(404, "Plan is not editable")
    if live_log_limit is None:
        live_log_limit = 10 if plan_id == "free" else 0
    if history_unlock_delay_days is None:
        history_unlock_delay_days = 1 if plan_id == "free" else 0
    display_name = name.strip()
    if not display_name or len(display_name) > 40:
        raise HTTPException(422, "Plan name must contain 1 to 40 characters")
    limits = {
        "daily_minutes": (daily_minutes, 1, 1_440),
        "requests_per_minute": (requests_per_minute, 1, 600),
        "max_concurrency": (max_concurrency, 1, 10),
        "max_devices": (max_devices, 1, 10),
        "max_stations": (max_stations, 1, 20),
        "live_log_limit": (live_log_limit, 0, 1_000),
        "history_unlock_delay_days": (
            history_unlock_delay_days,
            0,
            30,
        ),
        "sort_order": (sort_order, 0, 1_000),
    }
    for field, (value, minimum, maximum) in limits.items():
        if not minimum <= value <= maximum:
            raise HTTPException(422, f"{field} must be between {minimum} and {maximum}")

    db = _db()
    ref = db.collection("plans").document(plan_id)
    snapshot = ref.get()
    if not snapshot.exists:
        raise HTTPException(404, "Plan not found")
    before = snapshot.to_dict()
    audio_seconds_limit = daily_minutes * 60
    updates = {
        "name": display_name,
        "audio_seconds_limit": audio_seconds_limit,
        # Compatibility for app 1.1.0 during the rollout window.
        "monthly_audio_seconds": audio_seconds_limit,
        "quota_period": "daily",
        "requests_per_minute": requests_per_minute,
        "max_concurrency": max_concurrency,
        "max_devices": max_devices,
        "max_stations": max_stations,
        "live_log_limit": live_log_limit,
        "history_unlock_delay_days": history_unlock_delay_days,
        "sort_order": sort_order,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "updated_by": email,
    }
    batch = db.batch()
    batch.update(ref, updates)
    _write_audit(
        batch,
        db,
        email,
        "plan.update",
        plan_id,
        {
            "before": {key: before.get(key) for key in updates if key not in {"updated_at", "updated_by"}},
            "after": {key: value for key, value in updates.items() if key not in {"updated_at", "updated_by"}},
        },
        _request_id(request),
    )
    batch.commit()
    return _redirect("/plans", "plan_saved")
