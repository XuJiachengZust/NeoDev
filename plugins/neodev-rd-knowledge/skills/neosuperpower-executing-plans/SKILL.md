---
name: neosuperpower-executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** Tell your human partner that NeoSuperpower works much better with access to subagents. The quality of its work will be significantly higher if run on a platform with subagent support (such as Claude Code or Codex). If subagents are available, use neosuperpower-subagent-driven-development instead of this skill.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. Run the document coverage gate for all planned code changes: confirm each code-changing task maps to an approved controlled document or includes a document update before code edits
4. If concerns or missing document coverage: Raise them with your human partner before starting
5. If no concerns: Create task plan and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress
2. Before the first code edit, re-check that this task has document coverage or explicit user confirmation to proceed without it
3. Follow each step exactly (plan has bite-sized steps)
4. Run verifications as specified
5. Mark as completed

### Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use neosuperpower-finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Check document coverage before code edits
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **neosuperpower-using-git-worktrees** - Ensures isolated workspace (creates one or verifies existing)
- **neosuperpower-writing-plans** - Creates the plan this skill executes
- **neosuperpower-finishing-a-development-branch** - Complete development after all tasks
