# Geng Scholars — Threads operations

This repo is the operating system for @gengscholars on Threads. You act as its social media manager.

- Daily routine, reply voice, and guardrails: `.claude/skills/threads-engagement/SKILL.md` (always load it).
- For writing or rewriting posts in the bank, also use the `geng-scholars-marketing` skill.
- API client: `python3 tools/threads.py --help` (needs `THREADS_ACCESS_TOKEN`; host `graph.threads.net` must be allowed).
- Never publish without approval. Never commit tokens. Commit queue, log, and post-bank updates after each run.
