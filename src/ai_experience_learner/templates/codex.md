# Experience Learner

Learn from past interactions by distilling experience into reusable lessons, and recall relevant lessons to improve inference on new tasks. Powered by the `xp` CLI.

## Commands

- `xp learn --file LESSON.md` — Save a distilled lesson after completing a task
- `xp recall --query "description"` — Retrieve relevant lessons before starting a task
- `xp stats` — Check memory health
- `xp consolidate --target-size 30` — Compress memory via clustering

## When to use

- **After completing a task**: If you just solved a non-obvious bug, made an architectural decision, or discovered a pitfall, write a lesson and save it with `xp learn`.
- **Before starting a task**: Run `xp recall --query "task description"` to load relevant past experience.
- **Periodically**: Run `xp consolidate` when you have 30+ lessons.

## Lesson format

Write lessons as Markdown with these sections:
- Context (task type, problem, outcome)
- Pattern (transferable reasoning pattern)
- Technique (concrete reusable steps)
- Pitfalls (what to avoid)
- Key Insight (one sentence)
- When This Applies (conditions for recall)
- Tags (topic, problem_type, technique)

Focus on transferable patterns, not task-specific details.

## Configuration

Config: `~/.ai-experience-learner/config.toml`. Supports any OpenAI-compatible embedding API.
