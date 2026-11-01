# Geng Scholars: Threads Engagement Engine

An AI social media manager for @gengscholars on Threads. Every day it:

1. **Warms up:** finds the conversations our audience is having (SPM leavers, scholarship hunters, first-year uni students).
2. **Drafts value-first replies and picks posts to repost.** You approve them in one tap.
3. **Engages first, then publishes** the day's post from the bank about 30 minutes later.
4. **Learns:** a weekly report shows what worked, and it adjusts keywords, timing and themes.

```
discover ──► queue/YYYY-MM-DD.md ──► you approve [x] ──► execute (replies + reposts)
                                    └─► you like ~20 posts by hand (5 min, list provided)
                                                     │
                                         30 min later ▼
                                     publish today's post from content/post_bank.csv
                                                     │
                                     you answer replies in the first hour
                                                     ▼
                                        weekly report ──► tune config/targets.json
```

## What the official API can and can't do

| Action | Automatable? | How |
|---|---|---|
| Find relevant posts (keyword search) | ✅ | `threads.py search`. Public results need App Review approval for `threads_keyword_search`. |
| Reply to other people's posts | ✅ | `threads.py reply` |
| Repost | ✅ | `threads.py repost` |
| Publish your post bank | ✅ | `threads.py post` |
| Insights / analytics | ✅ | `threads.py insights`, `account-insights` |
| **Like posts** | ❌ No API exists | Agent gives you a ready list. ~5 min on your phone. |
| Follow accounts | ❌ No API exists | Manual |

Bots that like or follow through unofficial APIs or browser automation break Meta's terms. That
puts the account and our sponsor reputation at risk, so this repo doesn't use them.

## Setup (one-time, ~45 min + Meta review time)

### 1. Create the Meta app
1. Go to developers.facebook.com, then **Create App**, and choose the use case **"Access the Threads API"**.
2. In the use case, add these permissions:
   `threads_basic`, `threads_content_publish`, `threads_manage_replies`, `threads_read_replies`,
   `threads_manage_insights`, `threads_keyword_search`.
3. **App roles → Roles → Add Threads Tester** and enter the `gengscholars` Threads account. Accept the
   invite in the Threads app (Settings → Account → Website permissions → Invites).
4. Generate a user access token with the Threads **User Token Generator** in the app dashboard, then
   exchange it for a **long-lived token** (60 days).

### 2. Submit for App Review (critical path, start now)
Until Meta approves **`threads_keyword_search`** (and advanced access for replies), search only
returns *your own* posts. Then discovery doesn't work. Submit for App Review with a short screencast
of the approve-then-reply flow. Business verification of Geng Scholars Enterprise (SSM
202603018759) may be required. While you wait, the agent can still run your post bank, reply to
replies on your own posts, and pull insights. Paste posts you want to engage with and it drafts replies.

### 3. Connect it to the Claude cloud environment
In the session's cloud environment settings (environment menu in the title bar, then **Edit**):
- **Network access:** add `graph.threads.net` under *Allowed domains* (keep "Allow package managers" ticked).
- **Secrets / environment variables:** add `THREADS_ACCESS_TOKEN` = your long-lived token.

New sessions pick these up. Check with `python3 tools/threads.py me`.

### 4. Load your post bank
Put your month of posts into `content/post_bank.csv` (columns: `id, scheduled_date, slot, brand,
theme, text, status, posted_id, notes`). Set `status=approved` for posts that are ready.
Or upload the file in any format and ask Claude to convert it.

### 5. Fill in who we engage with
Edit `config/targets.json`: add **priority accounts** (edu creators, uni clubs, partners,
scholarship pages). This list does more for reach than keywords do.

## Automating it

Ask Claude in this session: **"Schedule the daily Threads routine."** It creates a scheduled task:

| When (MYT) | Task | You do |
|---|---|---|
| Daily 12:00 & 20:00 | `discover`: builds the queue, notifies you | Approve in chat ("execute all" or "skip 3, 7"), do likes (5 min) |
| On your approval | `execute`, then `publish` 30 min later | Answer replies in the first hour |
| Sunday 21:00 | `report` | Agree or reject 3 recommended changes |
| Every 50 days | `refresh-token` reminder | Paste the new token into the environment secret |

Manual commands work any time: "run today's Threads discover", "execute", "post today's thread",
"Threads weekly report".

**Autonomy path:** weeks 1–4 you approve everything. After that, if quality holds, set
`"auto_approve": true` in `config/targets.json` for replies scoring 9+, and keep approval for the rest.

## Files
- `tools/threads.py`: Threads API client (stdlib Python, no installs). Logs every action to `logs/actions.jsonl` so the account never double-replies.
- `.claude/skills/threads-engagement/SKILL.md`: the operating playbook (scoring, voice, guardrails).
- `config/targets.json`: keywords, priority accounts, budgets, no-go topics.
- `content/post_bank.csv`: your month of posts.
- `queue/`: daily approval queues (audit trail).
