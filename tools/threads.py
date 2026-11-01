#!/usr/bin/env python3
"""Geng Scholars Threads client — official Meta Threads Graph API, stdlib only.

Auth: set THREADS_ACCESS_TOKEN (long-lived user token, 60-day expiry).
Every write action is appended to logs/actions.jsonl so the agent never
double-engages the same post or author.

Usage:
  python3 tools/threads.py me
  python3 tools/threads.py search "biasiswa" --type RECENT --limit 25
  python3 tools/threads.py reply <post_id> "text"        [--dry-run]
  python3 tools/threads.py repost <post_id>              [--dry-run]
  python3 tools/threads.py post "text"                   [--dry-run]
  python3 tools/threads.py my-posts --limit 10
  python3 tools/threads.py insights <post_id>
  python3 tools/threads.py account-insights
  python3 tools/threads.py quota
  python3 tools/threads.py refresh-token
  python3 tools/threads.py history --days 7              (local log only)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://graph.threads.net"
VER = "v1.0"
ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "actions.jsonl"
POST_FIELDS = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply"


def token() -> str:
    t = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if not t:
        sys.exit("THREADS_ACCESS_TOKEN is not set. See README.md > Setup.")
    return t


def call(method: str, path: str, params: dict | None = None, versioned: bool = True) -> dict:
    params = {k: v for k, v in (params or {}).items() if v is not None}
    params["access_token"] = token()
    url = f"{BASE}/{VER}/{path}" if versioned else f"{BASE}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} on {method} {path}: {body}")


def log_action(kind: str, **fields) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "action": kind, **fields}
    with LOG.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_log(days: int) -> list[dict]:
    if not LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = []
    for line in LOG.read_text().splitlines():
        try:
            row = json.loads(line)
            if datetime.fromisoformat(row["ts"]) >= cutoff:
                rows.append(row)
        except (ValueError, KeyError):
            continue
    return rows


def already_engaged(post_id: str, kind: str) -> bool:
    return any(r.get("target_id") == post_id and r.get("action") == kind and not r.get("dry_run")
               for r in read_log(90))


def publish_text(text: str, reply_to: str | None = None, reply_control: str | None = None) -> dict:
    if len(text) > 500:
        sys.exit(f"Text is {len(text)} chars; Threads limit is 500.")
    container = call("POST", "me/threads", {
        "media_type": "TEXT", "text": text,
        "reply_to_id": reply_to, "reply_control": reply_control,
    })
    cid = container["id"]
    time.sleep(3)  # give Meta a moment to process the container
    res = call("POST", "me/threads_publish", {"creation_id": cid})
    if not res.get("id"):
        sys.exit(f"Publish failed for container {cid}: {res}")
    return res


def out(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("me")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--type", choices=["TOP", "RECENT"], default="TOP")
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--hours", type=int, help="only posts from the last N hours")
    s.add_argument("--author", help="filter by author username")

    r = sub.add_parser("reply")
    r.add_argument("post_id")
    r.add_argument("text")
    r.add_argument("--dry-run", action="store_true")

    rp = sub.add_parser("repost")
    rp.add_argument("post_id")
    rp.add_argument("--dry-run", action="store_true")

    po = sub.add_parser("post")
    po.add_argument("text")
    po.add_argument("--reply-control", choices=["everyone", "accounts_you_follow", "mentioned_only"])
    po.add_argument("--dry-run", action="store_true")

    mp = sub.add_parser("my-posts")
    mp.add_argument("--limit", type=int, default=10)

    ins = sub.add_parser("insights")
    ins.add_argument("post_id")
    sub.add_parser("account-insights")
    sub.add_parser("quota")
    sub.add_parser("refresh-token")
    h = sub.add_parser("history")
    h.add_argument("--days", type=int, default=7)

    a = p.parse_args()

    if a.cmd == "me":
        out(call("GET", "me", {"fields": "id,username,name,threads_biography"}))
    elif a.cmd == "search":
        since = None
        if a.hours:
            since = int((datetime.now(timezone.utc) - timedelta(hours=a.hours)).timestamp())
        res = call("GET", "keyword_search", {
            "q": a.query, "search_type": a.type, "fields": POST_FIELDS,
            "limit": a.limit, "since": since, "author_username": a.author,
        })
        for post in res.get("data", []):
            post["already_replied"] = already_engaged(post["id"], "reply")
            post["already_reposted"] = already_engaged(post["id"], "repost")
        out(res.get("data", []))
    elif a.cmd == "reply":
        if already_engaged(a.post_id, "reply"):
            sys.exit(f"Already replied to {a.post_id}; skipping (see logs/actions.jsonl).")
        if a.dry_run:
            log_action("reply", target_id=a.post_id, text=a.text, dry_run=True)
            out({"dry_run": True, "reply_to": a.post_id, "text": a.text})
        else:
            res = publish_text(a.text, reply_to=a.post_id)
            log_action("reply", target_id=a.post_id, text=a.text, result_id=res["id"])
            out(res)
    elif a.cmd == "repost":
        if already_engaged(a.post_id, "repost"):
            sys.exit(f"Already reposted {a.post_id}; skipping.")
        if a.dry_run:
            log_action("repost", target_id=a.post_id, dry_run=True)
            out({"dry_run": True, "repost": a.post_id})
        else:
            res = call("POST", f"{a.post_id}/repost")
            log_action("repost", target_id=a.post_id, result_id=res.get("id"))
            out(res)
    elif a.cmd == "post":
        if a.dry_run:
            log_action("post", text=a.text, dry_run=True)
            out({"dry_run": True, "text": a.text, "chars": len(a.text)})
        else:
            res = publish_text(a.text, reply_control=a.reply_control)
            log_action("post", text=a.text, result_id=res["id"])
            out(res)
    elif a.cmd == "my-posts":
        out(call("GET", "me/threads", {"fields": "id,text,permalink,timestamp", "limit": a.limit}).get("data", []))
    elif a.cmd == "insights":
        out(call("GET", f"{a.post_id}/insights", {"metric": "views,likes,replies,reposts,quotes,shares"}))
    elif a.cmd == "account-insights":
        out(call("GET", "me/threads_insights", {"metric": "views,likes,replies,reposts,quotes,followers_count"}))
    elif a.cmd == "quota":
        out(call("GET", "me/threads_publishing_limit",
                 {"fields": "quota_usage,config,reply_quota_usage,reply_config"}))
    elif a.cmd == "refresh-token":
        res = call("GET", "refresh_access_token",
                   {"grant_type": "th_refresh_token"}, versioned=False)
        secret = ROOT / ".secrets" / "threads_token"
        secret.parent.mkdir(exist_ok=True)
        secret.write_text(res.get("access_token", ""))
        secret.chmod(0o600)
        out({"expires_in_days": round(res.get("expires_in", 0) / 86400, 1),
             "saved_to": str(secret.relative_to(ROOT)),
             "note": "Copy it into the THREADS_ACCESS_TOKEN environment secret. Never commit it."})
    elif a.cmd == "history":
        out(read_log(a.days))


if __name__ == "__main__":
    main()
