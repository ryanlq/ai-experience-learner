---
name: experience-learner
description: >
  从过去的交互中学习，将经验蒸馏为可复用的教训，并在新任务中召回相关教训以改进推理。
  基于"Decocted Experience"研究(arXiv 2604.04373)。
  Use when:
  (1) completing a significant coding/debugging/architecture task and wanting
  to capture the experience — triggers: "learn from this", "save this experience",
  "remember this", "xp learn", "保存经验", "记录这次经验", "学到了", "值得记住";
  (2) starting a new task and wanting to recall relevant past lessons — triggers:
  "recall similar tasks", "what have I learned about X", "any past experience with",
  "xp recall", "回忆类似任务", "之前遇到过", "有没有相关经验", "查一下经验库";
  (3) wanting to consolidate or review accumulated experience — triggers:
  "consolidate memory", "show experience stats", "xp consolidate", "xp stats",
  "整理经验", "经验统计", "合并记忆".
---

# Experience Learner

Distill past interactions into reusable lessons, recall relevant lessons to improve inference on new tasks. Powered by the `xp` CLI.

## Quick Start

```bash
xp init                    # Initialize (run once)
xp learn --file LESSON.md  # Save a lesson
xp recall --query "..."    # Retrieve relevant lessons
xp stats                   # Check memory health
```

## Workflow 1: Learn (Distill Experience)

Use after completing a significant task — debugging sessions, architecture decisions, non-obvious fixes.

### Step 1: Write the lesson

Create a Markdown file with this structure:

```markdown
# [Topic]: [Concise Title]

## Context
- **Task Type**: coding | debugging | architecture | testing
- **Problem**: One-sentence problem statement
- **Outcome**: success | failure

## The Lesson

### Pattern
[The transferable reasoning pattern — what general principle applies]

### Technique
[Specific reusable steps, concrete but generalizable]

### Pitfalls
[What to avoid — equally valuable from failures and successes]

### Key Insight
[One sentence capturing the deepest learning]

## When This Applies
[2-3 conditions for when to recall this lesson]

## Tags
topic: [e.g., "CORS"]
problem_type: [e.g., "API integration"]
technique: [e.g., "browser DevTools"]
```

**Critical**: Focus on transferable patterns, not task-specific details.

### Step 2: Store

```bash
xp learn --file LESSON.md --task-type debugging
xp learn --file LESSON.md --task-type coding --failure  # for failure lessons
```

### When to learn

- After a debugging session that took >5 minutes
- After a non-obvious architectural decision
- After discovering a pitfall or anti-pattern
- After a failed approach that revealed important constraints

## Workflow 2: Recall (Retrieve Context)

Use before starting a new task to load relevant past experience.

```bash
xp recall --query "description of what you're about to do"
xp recall --query "debug CORS" --top-k 5 --lambda-val 0.7
```

### How retrieval works

Uses **Maximal Marginal Relevance (MMR)** from the paper:
- **Relevance** (λ weight): semantic similarity to query
- **Diversity** (1-λ weight): variety among selected lessons
- Default λ=0.6 (paper's ablation optimal for information gain)

Read the Pattern and Technique sections first — these contain transferable knowledge. Check Pitfalls for things to avoid.

## Workflow 3: Consolidate (Organize Memory)

As lessons accumulate, memory can become redundant. Consolidation clusters similar lessons.

```bash
xp consolidate --target-size 30
```

When to consolidate: after 30+ lessons, or when recall results feel repetitive.

## Configuration

Config: `~/.ai-experience-learner/config.toml`

```toml
[embedding]
api_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
model = "text-embedding-3-small"
dim = 1536
```

Supports any OpenAI-compatible endpoint. Without an API key, falls back to keyword matching.

## Integration Tips

### Before a task
```bash
xp recall --query "TASK DESCRIPTION"
```

### After a task
1. Reflect on what was learned
2. Write a lesson file
3. `xp learn --file LESSON.md`

### Mid-task
```bash
xp recall --query "current problem description"
```
