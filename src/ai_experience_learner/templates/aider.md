# Experience Learner

Learn from past interactions by distilling experience into reusable lessons, and recall relevant lessons to improve inference.

## Commands

- `xp learn --file LESSON.md` — Save a distilled lesson
- `xp recall --query "description"` — Retrieve relevant lessons
- `xp stats` — Check memory health
- `xp consolidate --target-size 30` — Compress memory

## When to use

- After completing a non-obvious debugging session or architectural decision, write a lesson and save it
- Before starting a new task, recall relevant past experience
- Periodically consolidate when you have 30+ lessons

## Lesson format

Markdown with sections: Context, Pattern, Technique, Pitfalls, Key Insight, When This Applies, Tags. Focus on transferable patterns.
