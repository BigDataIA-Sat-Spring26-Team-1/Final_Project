from __future__ import annotations
import asyncio
import html as html_lib
import re
from datetime import date as _date
from typing import Any, Dict, List, Optional
from snowflake.connector import SnowflakeConnection
from app.core.config import get_settings
from app.core.logging_conf import get_logger
from app.services.search import SearchService

logger = get_logger("app.services.mailer")

COMMON_LIMIT = 20
PERSONAL_LIMIT = 10

def _load_user_context(
    db: SnowflakeConnection, user_id: str
) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT u.id, u.email, u.full_name,
               p.job_title, p.seniority, p.persona_archetype, p.bio_summary
        FROM users u
        LEFT JOIN user_personas p ON p.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "user_id": row[0],
        "email": row[1],
        "full_name": row[2],
        "job_title": row[3],
        "seniority": row[4],
        "persona_archetype": row[5],
        "bio_summary": row[6],
    }

def _load_common_highlights(
    db: SnowflakeConnection, edition_date: str, limit: int = COMMON_LIMIT
) -> List[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT c.id, c.primary_title, c.primary_summary, c.trend_status,
               c.final_trend_score, c.cluster_size, a.url, a.source_name
        FROM article_clusters c
        LEFT JOIN (
            SELECT cluster_id, url, source_name,
                   ROW_NUMBER() OVER (
                       PARTITION BY cluster_id
                       ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                   ) AS rn
            FROM articles_raw
            WHERE cluster_id IS NOT NULL AND url IS NOT NULL AND url <> ''
        ) a ON a.cluster_id = c.id AND a.rn = 1
        WHERE c.final_trend_score IS NOT NULL
          AND CAST(c.created_at AS DATE) = %s
        ORDER BY c.final_trend_score DESC, c.cluster_size DESC NULLS LAST
        LIMIT %s
        """,
        (edition_date, limit),
    )
    rows = cur.fetchall()
    if rows:
        return [
            {
                "cluster_id": r[0],
                "title": r[1] or "",
                "summary": r[2] or "",
                "trend_status": r[3],
                "final_trend_score": float(r[4] or 0.0),
                "cluster_size": int(r[5] or 1),
                "url": r[6] or "",
                "source_name": r[7] or "",
            }
            for r in rows
        ]
    # Fallback — no clusters were ingested on the exact edition_date. Still
    # cap to clusters created on or before that date so historical editions
    # never surface future-dated content (the 04-22 hero showing 04-24
    # "Mounting tar" bug).
    cur.execute(
        """
        SELECT c.id, c.primary_title, c.primary_summary, c.trend_status,
               c.final_trend_score, c.cluster_size, a.url, a.source_name
        FROM article_clusters c
        LEFT JOIN (
            SELECT cluster_id, url, source_name,
                   ROW_NUMBER() OVER (
                       PARTITION BY cluster_id
                       ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                   ) AS rn
            FROM articles_raw
            WHERE cluster_id IS NOT NULL AND url IS NOT NULL AND url <> ''
        ) a ON a.cluster_id = c.id AND a.rn = 1
        WHERE c.final_trend_score IS NOT NULL
          AND CAST(c.created_at AS DATE) <= %s
        ORDER BY c.created_at DESC, c.final_trend_score DESC NULLS LAST
        LIMIT %s
        """,
        (edition_date, limit),
    )
    return [
        {
            "cluster_id": r[0],
            "title": r[1] or "",
            "summary": r[2] or "",
            "trend_status": r[3],
            "final_trend_score": float(r[4] or 0.0),
            "cluster_size": int(r[5] or 1),
            "url": r[6] or "",
            "source_name": r[7] or "",
        }
        for r in cur.fetchall()
    ]

async def _load_personalized(
    user_id: str,
    db: SnowflakeConnection,
    limit: int = PERSONAL_LIMIT,
    edition_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    payload = await SearchService.get_personalized_recommendations(
        user_id, limit, db, edition_date=edition_date
    )
    if not payload:
        return []
    return payload.get("results", [])

def _esc(text: Any) -> str:
    if text is None:
        return ""
    return html_lib.escape(str(text), quote=True)

def _article_row_html(article: Dict[str, Any], accent: str) -> str:
    title = _esc(article.get("title") or "Untitled")
    summary = _esc((article.get("summary") or "")[:220])
    if summary and len(article.get("summary", "")) > 220:
        summary += "…"
    url = article.get("url") or ""
    source = (
        article.get("source_name")
        or (article.get("sources") or [None])[0]
        or ""
    )
    source_line = _esc(source) if source else ""
    status = article.get("trend_status") or "FEATURED"
    title_link = (
        f'<a href="{_esc(url)}" style="color:#f8fafc;text-decoration:none;" '
        'target="_blank">' + title + "</a>"
        if url
        else title
    )
    cta = (
        f'<a href="{_esc(url)}" target="_blank" '
        'style="display:inline-block;margin-top:10px;padding:8px 14px;'
        'border-radius:8px;background:#2dd4bf;color:#0f172a;'
        'text-decoration:none;font-size:12px;font-weight:700;">Read source →</a>'
        if url
        else ""
    )
    meta_parts: List[str] = [f'<span style="color:{accent};font-weight:700;">{_esc(status)}</span>']
    if source_line:
        meta_parts.append(f'<span style="color:#94a3b8;">{source_line}</span>')
    meta = ' · '.join(meta_parts)

    return (
        '<tr><td style="padding:16px 0;border-bottom:1px solid rgba(148,163,184,0.15);">'
        f'<div style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">{meta}</div>'
        f'<div style="font-size:17px;font-weight:700;line-height:1.35;color:#f8fafc;">{title_link}</div>'
        + (f'<div style="font-size:13px;line-height:1.55;color:#cbd5e1;margin-top:6px;">{summary}</div>' if summary else "")
        + cta
        + '</td></tr>'
    )

def _hero_html(article: Dict[str, Any]) -> str:
    title = _esc(article.get("title") or "Headline of the day")
    summary = _esc((article.get("summary") or "")[:260])
    url = article.get("url") or ""
    source = (
        article.get("source_name")
        or (article.get("sources") or [None])[0]
        or ""
    )
    linked = (
        f'<a href="{_esc(url)}" style="color:#0f172a;text-decoration:none;" target="_blank">{title}</a>'
        if url
        else title
    )
    src = _esc(source)
    return (
        '<tr><td style="padding:28px 32px;background:linear-gradient(135deg,#2dd4bf 0%,#6366f1 100%);color:#0f172a;border-radius:16px;">'
        '<div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#0f172a;opacity:0.75;margin-bottom:10px;font-weight:700;">Top Headline</div>'
        f'<div style="font-size:26px;font-weight:800;line-height:1.25;">{linked}</div>'
        + (f'<div style="font-size:14px;line-height:1.6;color:#0f172a;opacity:0.8;margin-top:12px;">{summary}</div>' if summary else "")
        + (f'<div style="font-size:12px;color:#0f172a;opacity:0.7;margin-top:14px;font-weight:600;">{src}</div>' if src else "")
        + '</td></tr>'
    )

def _render_html(
    user: Dict[str, Any],
    edition_date: str,
    common: List[Dict[str, Any]],
    personal: List[Dict[str, Any]],
) -> str:
    greeting_name = user.get("full_name") or user.get("email") or "there"
    persona = user.get("persona_archetype") or user.get("job_title") or "Tech Professional"

    hero = common[0] if common else None
    rest_common = common[1:] if common else []

    personal_rows = "".join(_article_row_html(a, "#2dd4bf") for a in personal)
    common_rows = "".join(_article_row_html(a, "#6366f1") for a in rest_common)

    hero_block = _hero_html(hero) if hero else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>CurateAI — {_esc(edition_date)}</title>
</head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:32px 0;">
  <tr><td align="center">
    <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#1e293b;border-radius:20px;overflow:hidden;box-shadow:0 10px 40px rgba(45,212,191,0.12);border:1px solid rgba(148,163,184,0.12);">
      <tr>
        <td style="padding:28px 32px 0 32px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:36px;height:36px;border-radius:10px;background:#2dd4bf;color:#0f172a;font-weight:900;font-size:16px;display:inline-block;text-align:center;line-height:36px;">C</div>
              <div style="font-size:22px;font-weight:800;letter-spacing:-0.01em;color:#f8fafc;">CurateAI</div>
            </div>
            <div style="text-align:right;font-size:12px;color:#94a3b8;font-family:monospace;">{_esc(edition_date)}</div>
          </div>
          <div style="margin-top:20px;font-size:14px;color:#cbd5e1;line-height:1.55;">
            Hey {_esc(greeting_name)} — your daily tech briefing, curated for <strong style="color:#2dd4bf;">{_esc(persona)}</strong>.
          </div>
        </td>
      </tr>

      {'<tr><td style="padding:24px 32px 0 32px;">' + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' + hero_block + '</table></td></tr>' if hero_block else ''}

      <tr>
        <td style="padding:28px 32px 0 32px;">
          <div style="font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#2dd4bf;font-weight:800;">Curated For You</div>
          <div style="font-size:18px;font-weight:800;margin-top:4px;color:#f8fafc;">Top {len(personal)} personalized picks</div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;">
            {personal_rows or '<tr><td style="padding:14px 0;color:#94a3b8;font-style:italic;">No personalized articles ranked for today.</td></tr>'}
          </table>
        </td>
      </tr>

      <tr>
        <td style="padding:32px 32px 12px 32px;">
          <div style="font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#6366f1;font-weight:800;">Today's Deck</div>
          <div style="font-size:18px;font-weight:800;margin-top:4px;color:#f8fafc;">Top {len(rest_common)} trending across every feed</div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;">
            {common_rows or '<tr><td style="padding:14px 0;color:#94a3b8;font-style:italic;">Trend snapshot still warming up.</td></tr>'}
          </table>
        </td>
      </tr>

      <tr>
        <td style="padding:20px 32px 32px 32px;border-top:1px solid rgba(148,163,184,0.15);">
          <div style="font-size:12px;color:#94a3b8;line-height:1.6;">
            Sent by <strong style="color:#2dd4bf;">CurateAI</strong> · generated {_esc(edition_date)}
          </div>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""

def _plain_text_fallback(
    user: Dict[str, Any],
    edition_date: str,
    common: List[Dict[str, Any]],
    personal: List[Dict[str, Any]],
) -> str:
    def _line(a: Dict[str, Any]) -> str:
        src = a.get("source_name") or (a.get("sources") or [""])[0]
        return f"- {a.get('title','')}" + (f" ({src})" if src else "") + (f" → {a['url']}" if a.get("url") else "")

    parts = [f"CurateAI — Daily Briefing ({edition_date})", ""]
    parts.append(f"Curated for {user.get('full_name') or user.get('email') or 'you'}")
    parts.append("")
    parts.append(f"Top {len(personal)} personalized picks:")
    parts += [_line(a) for a in personal]
    parts.append("")
    parts.append(f"Today's deck — top {len(common)} trending:")
    parts += [_line(a) for a in common]
    return "\n".join(parts)

def _rotate_by_date(items: List[Dict[str, Any]], edition_date: str) -> List[Dict[str, Any]]:
    if not items:
        return items
    try:
        ed = _date.fromisoformat(edition_date)
    except ValueError:
        return items
    offset = (_date.today() - ed).days
    if offset <= 0:
        return items
    shift = offset % len(items)
    return items[shift:] + items[:shift]

async def render_personalized_html(
    user_id: str, edition_date: str, db: SnowflakeConnection
) -> Optional[Dict[str, Any]]:
    user = _load_user_context(db, user_id)
    if not user:
        return None
    common = _load_common_highlights(db, edition_date)
    personal = await _load_personalized(user_id, db, edition_date=edition_date)
    common = _rotate_by_date(common, edition_date)
    personal = _rotate_by_date(personal, edition_date)
    html = _render_html(user, edition_date, common, personal)
    text = _plain_text_fallback(user, edition_date, common, personal)
    return {
        "user": user,
        "html": html,
        "text": text,
        "common_count": len(common),
        "personal_count": len(personal),
    }

def _resolve_recipient(
    user: Dict[str, Any], test_recipient: str
) -> Optional[Dict[str, str]]:
    if test_recipient:
        return {
            "email": test_recipient,
            "name": user.get("full_name") or user.get("email") or "Test Reader",
        }
    email = user.get("email")
    if not email:
        return None
    return {"email": email, "name": user.get("full_name") or email}

def _load_stored_html(
    db: SnowflakeConnection, user_id: str, edition_date: str
) -> Optional[str]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT final_content, draft_content
        FROM newsletters
        WHERE user_id = %s AND edition_date = %s
        ORDER BY generated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (user_id, edition_date),
    )
    row = cur.fetchone()
    if not row:
        return None
    html = (row[0] or row[1] or "").strip()
    return html or None


def _persist_rendered_html(
    db: SnowflakeConnection, user_id: str, edition_date: str, html: str
) -> None:
    """Idempotent upsert of the templated HTML, keyed on (user_id,
    edition_date). Used to lock today's newsletter after the first render
    so multiple previews/logins see the same body."""
    import uuid as _uuid
    cur = db.cursor()
    cur.execute(
        """
        MERGE INTO newsletters t
        USING (SELECT %s AS user_id, %s AS edition_date) s
        ON t.user_id = s.user_id AND t.edition_date = s.edition_date
        WHEN MATCHED THEN UPDATE SET
            final_content = %s,
            draft_content = %s,
            status = 'PUBLISHED',
            generated_at = CURRENT_TIMESTAMP(),
            updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
            (id, user_id, edition_date, final_content, draft_content,
             status, generated_at)
        VALUES (%s, s.user_id, s.edition_date, %s, %s, 'PUBLISHED',
                CURRENT_TIMESTAMP())
        """,
        (user_id, edition_date, html, html, str(_uuid.uuid4()), html, html),
    )
    db.commit()


_PERSONAL_COUNT_RE = re.compile(r"Top\s+(\d+)\s+personalized picks", re.IGNORECASE)
_COMMON_COUNT_RE = re.compile(r"Top\s+(\d+)\s+trending", re.IGNORECASE)


def _counts_from_html(html: str) -> tuple[int, int]:
    """Recover (personal_count, common_count) from a stored newsletter body.

    The template always emits ``Top {N} personalized picks`` and
    ``Top {N} trending across every feed`` so a simple regex recovers both.
    Used when we serve a cached row — the counts weren't persisted as
    separate columns, and showing 0/0 in the header while the body has
    real content is misleading."""
    personal = 0
    common = 0
    m = _PERSONAL_COUNT_RE.search(html or "")
    if m:
        try:
            personal = int(m.group(1))
        except ValueError:
            pass
    m = _COMMON_COUNT_RE.search(html or "")
    if m:
        try:
            common = int(m.group(1))
        except ValueError:
            pass
    return personal, common


async def get_or_render_newsletter_html(
    user_id: str, edition_date: str, db: SnowflakeConnection
) -> Optional[Dict[str, Any]]:
    """Serve the stored newsletter HTML if one exists for
    (user_id, edition_date); otherwise render fresh via the templated
    mailer path AND persist it so subsequent calls are stable.

    Past editions without a stored row return None — we never retro-render
    history since the underlying article pool has drifted.
    """
    stored = _load_stored_html(db, user_id, edition_date)
    if stored:
        user = _load_user_context(db, user_id)
        personal, common = _counts_from_html(stored)
        return {
            "user": user,
            "html": stored,
            "text": stored,
            "common_count": common,
            "personal_count": personal,
            "cached": True,
        }

    today = _date.today().isoformat()
    if edition_date != today:
        return None

    rendered = await render_personalized_html(user_id, edition_date, db)
    if not rendered or not (rendered.get("html") or "").strip():
        return None

    _persist_rendered_html(db, user_id, edition_date, rendered["html"])
    rendered["cached"] = False
    return rendered


def _check_existing_delivery(
    db: SnowflakeConnection, user_id: str, edition_date: str
) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT sent_at, delivery_status, delivery_message_id, delivery_recipient
        FROM newsletters
        WHERE user_id = %s AND edition_date = %s
        ORDER BY generated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (user_id, edition_date),
    )
    row = cur.fetchone()
    if not row:
        return None
    sent_at = row[0]
    if sent_at is None:
        return None
    return {
        "sent_at": sent_at.isoformat() if hasattr(sent_at, "isoformat") else str(sent_at),
        "status": row[1] or "SENT",
        "message_id": row[2],
        "recipient": row[3],
    }

def _record_delivery(
    db: SnowflakeConnection,
    user_id: str,
    edition_date: str,
    html: str,
    recipient: str,
    message_id: Optional[str],
    status: str,
) -> Optional[str]:

    import uuid as _uuid

    cur = db.cursor()
    is_success = status == "SENT"
    sent_expr = "CURRENT_TIMESTAMP()" if is_success else "NULL"

    cur.execute(
        f"""
        MERGE INTO newsletters t
        USING (SELECT %s AS user_id, %s AS edition_date) s
        ON t.user_id = s.user_id AND t.edition_date = s.edition_date
        WHEN MATCHED THEN UPDATE SET
            final_content = COALESCE(t.final_content, %s),
            draft_content = COALESCE(t.draft_content, %s),
            status = COALESCE(t.status, 'PUBLISHED'),
            sent_at = {sent_expr},
            delivery_status = %s,
            delivery_message_id = %s,
            delivery_recipient = %s,
            updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
            (id, user_id, edition_date, draft_content, final_content, status,
             generated_at, sent_at, delivery_status, delivery_message_id,
             delivery_recipient)
        VALUES (%s, s.user_id, s.edition_date, %s, %s, 'PUBLISHED',
                CURRENT_TIMESTAMP(), {sent_expr}, %s, %s, %s)
        """,
        (
            user_id,
            edition_date,
            html,
            html,
            status,
            message_id,
            recipient,
            str(_uuid.uuid4()),
            html,
            html,
            status,
            message_id,
            recipient,
        ),
    )
    db.commit()
    cur.execute(
        "SELECT sent_at FROM newsletters WHERE user_id = %s AND edition_date = %s",
        (user_id, edition_date),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
    return None

async def send_newsletter_email(
    user_id: str,
    edition_date: Optional[str],
    db: SnowflakeConnection,
) -> Dict[str, Any]:
    settings = get_settings()
    target_date = edition_date or _date.today().isoformat()

    existing = _check_existing_delivery(db, user_id, target_date)
    if existing:
        logger.info(
            "Newsletter already delivered — skipping MailerSend call",
            user_id=user_id,
            edition_date=target_date,
        )
        return {
            "status": "ALREADY_SENT",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": True,
            "sent_at": existing.get("sent_at"),
            "recipient": existing.get("recipient"),
            "message_id": existing.get("message_id"),
        }

    if not settings.mailersend_api_key:
        return {
            "status": "MAILER_DISABLED",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": False,
            "detail": "MAILERSEND_API_KEY not configured.",
        }

    # Prefer the stored locked copy so the email matches exactly what the
    # user saw in the preview. Only render fresh if there's no stored row.
    rendered = await get_or_render_newsletter_html(user_id, target_date, db)
    if not rendered:
        return {
            "status": "USER_NOT_FOUND",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": False,
        }
    user = rendered.get("user") or _load_user_context(db, user_id)
    if not user:
        return {
            "status": "USER_NOT_FOUND",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": False,
        }
    if "text" not in rendered or not rendered.get("text"):
        rendered["text"] = rendered["html"]

    recipient = _resolve_recipient(user, settings.mailersend_test_recipient)
    if not recipient:
        return {
            "status": "NO_RECIPIENT",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": False,
            "detail": "User has no email on file and no test recipient configured.",
        }

    subject = f"CurateAI — Daily Briefing · {target_date}"

    def _blocking_send() -> Dict[str, Any]:
        from mailersend import MailerSendClient, EmailBuilder  

        client = MailerSendClient(api_key=settings.mailersend_api_key)
        email = (
            EmailBuilder()
            .from_email(settings.mailersend_from_email, settings.mailersend_from_name)
            .to_many([recipient])
            .subject(subject)
            .html(rendered["html"])
            .text(rendered["text"])
            .build()
        )
        return client.emails.send(email)

    try:
        response = await asyncio.to_thread(_blocking_send)
        message_id = getattr(response, "message_id", None) or getattr(response, "id", None)
        sent_at = _record_delivery(
            db,
            user_id,
            target_date,
            rendered["html"],
            recipient["email"],
            message_id,
            "SENT",
        )
        logger.info(
            "Newsletter email sent",
            user_id=user_id,
            edition_date=target_date,
            recipient=recipient["email"],
            message_id=message_id,
        )
        return {
            "status": "SENT",
            "user_id": user_id,
            "edition_date": target_date,
            "recipient": recipient["email"],
            "message_id": message_id,
            "sent_at": sent_at,
            "already_sent": False,
            "common_count": rendered["common_count"],
            "personal_count": rendered["personal_count"],
        }
    except Exception as exc:  
        logger.error(
            "MailerSend dispatch failed",
            user_id=user_id,
            edition_date=target_date,
            error=str(exc),
            exc_info=True,
        )
        try:
            _record_delivery(
                db,
                user_id,
                target_date,
                rendered["html"],
                recipient["email"],
                None,
                "FAILED",
            )
        except Exception: 
            pass
        return {
            "status": "FAILED",
            "user_id": user_id,
            "edition_date": target_date,
            "already_sent": False,
            "detail": str(exc),
        }