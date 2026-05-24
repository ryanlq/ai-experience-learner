"""CLI entry point for xp command."""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from . import embed
from .config import Config
from .db import get_db, init_db
from .retrieval import keyword_recall, mmr_select


def _slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9一-鿿]+", "-", text.strip())[:max_len]
    return slug.strip("-") or "lesson"


def _parse_tags(text: str) -> dict:
    meta = {"topic": None, "problem_type": None, "technique": None}
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        if ":" in title:
            meta["topic"] = title.split(":", 1)[0].strip()
        else:
            meta["topic"] = title[:60]
    tags = re.search(r"^##\s+Tags\s*\n(.+?)(?=\n#|\Z)", text, re.MULTILINE | re.DOTALL)
    if tags:
        for line in tags.group(1).strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower().replace("-", "_").replace(" ", "_")
                if k in meta:
                    meta[k] = v.strip()
    return meta


def _do_embed(text: str, cfg: Config) -> np.ndarray | None:
    """Try to embed text using configured API. Returns None on failure."""
    if not cfg.has_api_key:
        return None
    return embed.encode(text, cfg.embedding_api_url, cfg.api_key, cfg.embedding_model)


# ── init ──────────────────────────────────────────────────────────────────

def cmd_init(args):
    cfg = Config()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.lessons_dir.mkdir(parents=True, exist_ok=True)
    init_db(cfg.db_path)
    if not cfg.config_path.exists():
        cfg.save()

    tier = cfg.tier
    tier_label = "API embedding" if tier == 2 else "keyword (no API key)"
    print(f"Data dir:     {cfg.data_dir}")
    print(f"Database:     {cfg.db_path}")
    print(f"Config:       {cfg.config_path}")
    print(f"Tier:         {tier} ({tier_label})")
    print(f"API:          {cfg.embedding_api_url}")
    print(f"Model:        {cfg.embedding_model}")
    print(f"Key env:      {cfg.embedding_api_key_env} {'(set)' if cfg.has_api_key else '(not set)'}")


# ── learn ─────────────────────────────────────────────────────────────────

def cmd_learn(args):
    cfg = Config()
    path = Path(args.file)
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    lesson_text = path.read_text().strip()
    if not lesson_text:
        print("Error: empty lesson file", file=sys.stderr)
        sys.exit(1)

    meta = _parse_tags(lesson_text)
    task_type = args.task_type or "coding"
    success = 0 if args.failure else 1

    now = datetime.now()
    slug = _slug(meta.get("topic") or "lesson")
    filename = f"{now:%Y-%m-%d_%H%M%S}_{slug}.md"

    dest = cfg.lessons_dir / filename
    dest.write_text(lesson_text)

    embed_blob = None
    embed_text = (
        f"{meta.get('topic', '')} {meta.get('problem_type', '')} "
        f"{meta.get('technique', '')} {lesson_text[:500]}"
    )
    vec = _do_embed(embed_text, cfg)
    if vec is not None:
        embed_blob = embed.to_blob(vec)

    conn = get_db(cfg.db_path)
    conn.execute(
        """INSERT INTO lessons
           (filename, topic, problem_type, technique, task_type, success,
            source_project, lesson_text, embedding)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (filename, meta["topic"], meta["problem_type"], meta["technique"],
         task_type, success, os.environ.get("PWD", ""), lesson_text, embed_blob),
    )
    conn.commit()
    lid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    status = "embedded" if embed_blob else "keyword-only"
    print(f"Learned #{lid}: {filename}")
    print(f"  Topic: {meta.get('topic', 'N/A')} | Type: {task_type} | {status}")


# ── recall ────────────────────────────────────────────────────────────────

def cmd_recall(args):
    cfg = Config()
    query = args.query
    top_k = args.top_k or cfg.retrieval_top_k
    lam = args.lambda_val if args.lambda_val is not None else cfg.retrieval_lambda

    conn = get_db(cfg.db_path)
    rows = conn.execute(
        "SELECT id, filename, topic, problem_type, technique, "
        "task_type, success, lesson_text, embedding FROM lessons ORDER BY id"
    ).fetchall()
    conn.close()

    if not rows:
        print("No lessons in memory. Run `xp learn` first.")
        return

    candidates = []
    for row in rows:
        entry = {k: row[k] for k in row.keys() if k != "embedding"}
        if row["embedding"]:
            entry["embedding"] = embed.from_blob(row["embedding"])
        candidates.append(entry)

    # Adaptive top_k: don't return a high percentage of a small DB
    effective_top_k = min(top_k, max(1, len(candidates) // 5))

    query_vec = _do_embed(query, cfg)
    if query_vec is not None and any("embedding" in c for c in candidates):
        pool = [c for c in candidates if "embedding" in c]
        selected = mmr_select(query_vec, pool, top_k=min(effective_top_k, len(pool)), lam=lam)
    else:
        selected = keyword_recall(query, candidates, effective_top_k)

    # Filter by relevance threshold
    threshold = cfg.relevance_threshold
    selected = [s for s in selected if s.get("_relevance", 0) >= threshold]

    if not selected:
        print(f"No relevant lessons found (threshold: {threshold}).")
        return

    print(f"<!-- Retrieved {len(selected)} lesson(s) for: {query} -->\n")
    for i, lesson in enumerate(selected, 1):
        tag = "SUCCESS" if lesson["success"] else "FAILURE"
        score = lesson.get("_relevance", 0)
        print(f"### Lesson {i}: {lesson.get('topic', 'Untitled')} [{tag}] (relevance: {score:.2f})")
        print()
        text = lesson["lesson_text"]
        if len(text) > 600:
            text = text[:600] + "\n... (truncated)"
        print(text)
        print()


# ── consolidate ───────────────────────────────────────────────────────────

def cmd_consolidate(args):
    cfg = Config()
    target = args.target_size or cfg.consolidate_target_size

    conn = get_db(cfg.db_path)
    rows = conn.execute(
        "SELECT id, embedding FROM lessons WHERE embedding IS NOT NULL"
    ).fetchall()

    if len(rows) <= target:
        print(f"Only {len(rows)} lessons. No consolidation needed (target: {target}).")
        conn.close()
        return

    try:
        from sklearn.cluster import KMeans
    except ImportError:
        print("Error: scikit-learn required. Install with: xp[cluster]", file=sys.stderr)
        conn.close()
        sys.exit(1)

    ids = [r["id"] for r in rows]
    vecs = np.stack([embed.from_blob(r["embedding"]) for r in rows])

    km = KMeans(n_clusters=target, random_state=42, n_init=10)
    labels = km.fit_predict(vecs)

    reps = set()
    for cid in range(target):
        mask = labels == cid
        cluster_vecs = vecs[mask]
        cluster_ids = [ids[i] for i in range(len(ids)) if mask[i]]
        centroid = km.cluster_centers_[cid]
        dists = np.linalg.norm(cluster_vecs - centroid, axis=1)
        reps.add(cluster_ids[int(np.argmin(dists))])

    for i, lid in enumerate(ids):
        cluster = int(labels[i])
        is_rep = lid in reps
        conn.execute(
            "UPDATE lessons SET cluster_id = ? WHERE id = ?",
            (cluster if is_rep else -cluster - 1000, lid),
        )

    conn.commit()
    archived = len(ids) - len(reps)
    conn.close()

    print(f"Consolidated {len(rows)} -> {target} clusters")
    print(f"  Active: {len(reps)} | Archived: {archived}")


# ── stats ─────────────────────────────────────────────────────────────────

def cmd_stats(args):
    cfg = Config()
    conn = get_db(cfg.db_path)

    total = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    with_embed = conn.execute("SELECT COUNT(*) FROM lessons WHERE embedding IS NOT NULL").fetchone()[0]
    clustered = conn.execute("SELECT COUNT(*) FROM lessons WHERE cluster_id >= 0").fetchone()[0]
    by_type = conn.execute("SELECT task_type, COUNT(*) as cnt FROM lessons GROUP BY task_type").fetchall()
    by_success = conn.execute("SELECT success, COUNT(*) as cnt FROM lessons GROUP BY success").fetchall()
    last = conn.execute("SELECT created_at FROM lessons ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    tier = cfg.tier
    tier_label = "API embedding" if tier == 2 else "keyword"
    print("Experience Memory Stats")
    print("=" * 40)
    print(f"Total lessons:     {total}")
    print(f"With embeddings:   {with_embed}")
    print(f"Clustered:         {clustered}")
    print(f"Tier:              {tier} ({tier_label})")
    print(f"Embedding API:     {cfg.embedding_api_url}")
    print(f"Embedding model:   {cfg.embedding_model}")
    print(f"Data dir:          {cfg.data_dir}")
    print(f"Config:            {cfg.config_path}")
    if last:
        print(f"Last lesson:       {last[0]}")

    if by_type:
        print("\nBy task type:")
        for row in by_type:
            print(f"  {row['task_type'] or 'untyped'}: {row['cnt']}")

    if by_success:
        print("\nBy outcome:")
        for row in by_success:
            label = "success" if row["success"] else "failure"
            print(f"  {label}: {row['cnt']}")


# ── setup ─────────────────────────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).parent / "templates"

SETUP_TARGETS = {
    "claude": {
        "template": "claude.md",
        "dest": Path.home() / ".claude" / "skills" / "experience-learner" / "SKILL.md",
        "label": "Claude Code",
    },
    "codex": {
        "template": "codex.md",
        "dest": Path.home() / ".codex" / "instructions" / "experience-learner.md",
        "label": "Codex CLI",
    },
    "cursor": {
        "template": "cursor.mdc",
        "dest": Path.home() / ".cursor" / "rules" / "experience-learner.mdc",
        "label": "Cursor",
    },
    "windsurf": {
        "template": "windsurf.md",
        "dest": Path.home() / ".windsurf" / "rules" / "experience-learner.md",
        "label": "Windsurf",
    },
    "aider": {
        "template": "aider.md",
        "dest": Path.home() / ".aider" / "conventions" / "experience-learner.md",
        "label": "Aider",
    },
    "cline": {
        "template": "cline.md",
        "dest": Path.home() / "Documents" / "Cline" / "Rules" / "experience-learner.md",
        "label": "Cline",
    },
}


def cmd_setup(args):
    tool = args.tool
    if tool == "all":
        tools = list(SETUP_TARGETS.keys())
    elif tool in SETUP_TARGETS:
        tools = [tool]
    else:
        print(f"Error: unknown tool '{tool}'. Choose from: {', '.join(SETUP_TARGETS)}, all", file=sys.stderr)
        sys.exit(1)

    # Run init first
    cmd_init(args)

    print()
    installed = []
    for t in tools:
        target = SETUP_TARGETS[t]
        src = TEMPLATES_DIR / target["template"]
        dest = target["dest"]

        if not src.exists():
            print(f"  [{target['label']}] template not found: {src}", file=sys.stderr)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        installed.append(target["label"])
        print(f"  [{target['label']}] installed -> {dest}")

    print()
    if installed:
        print(f"Setup complete. Installed for: {', '.join(installed)}")
    print("Next steps:")
    print("  1. Edit ~/.ai-experience-learner/config.toml to set embedding API")
    print("  2. Run 'xp stats' to verify")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="xp",
        description="ai-experience-learner: Decocted Experience CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize experience database and config")

    p_learn = sub.add_parser("learn", help="Store a distilled lesson")
    p_learn.add_argument("--file", required=True, help="Path to lesson Markdown file")
    p_learn.add_argument("--task-type", choices=["coding", "debugging", "architecture", "testing"], default=None)
    p_learn.add_argument("--failure", action="store_true")

    p_recall = sub.add_parser("recall", help="Retrieve relevant lessons")
    p_recall.add_argument("--query", required=True, help="Task description")
    p_recall.add_argument("--top-k", type=int, default=None)
    p_recall.add_argument("--lambda-val", type=float, default=None, dest="lambda_val")

    p_cons = sub.add_parser("consolidate", help="Compress memory via clustering")
    p_cons.add_argument("--target-size", type=int, default=None)

    sub.add_parser("stats", help="Show memory statistics")

    p_setup = sub.add_parser("setup", help="Install instruction files for AI coding tools")
    p_setup.add_argument("--tool", required=True,
                         choices=["claude", "codex", "cursor", "windsurf", "aider", "cline", "all"],
                         help="Which AI tool to install instructions for")

    args = parser.parse_args()

    cmds = {
        "init": cmd_init,
        "learn": cmd_learn,
        "recall": cmd_recall,
        "consolidate": cmd_consolidate,
        "stats": cmd_stats,
        "setup": cmd_setup,
    }

    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
