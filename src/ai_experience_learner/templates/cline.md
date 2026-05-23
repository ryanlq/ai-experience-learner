# Experience Learner

Learn from past interactions by distilling experience into reusable lessons, and recall relevant lessons to improve inference.

## When to use

- **After completing a task**: Write a lesson and save with `xp learn --file LESSON.md`
- **Before starting a task**: Retrieve relevant lessons with `xp recall --query "task description"`
- **Periodically**: Compress memory with `xp consolidate`

## Lesson format

Create a Markdown file with: Context, Pattern, Technique, Pitfalls, Key Insight, When This Applies, Tags.

Focus on transferable patterns, not task-specific details.

## Commands

- `xp learn --file LESSON.md --task-type debugging|coding|architecture|testing`
- `xp recall --query "description" --top-k 3`
- `xp stats`
- `xp consolidate --target-size 30`
