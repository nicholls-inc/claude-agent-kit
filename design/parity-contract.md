# Parity Contract: OMO -> Claude Code CLI Plugin

## Purpose

This document defines what "functional parity" means for recreating oh-my-opencode (OMO) inside Claude Code (CC) CLI.

It exists to:
- Prevent scope creep and infinite "chase the edge cases" work.
- Provide a clear definition of done.
- Make gaps explicit and justified.

## Constraints (Hard)

- No modifications to Claude Code source.
- No external systems that programmatically control Claude Code.
- Do NOT use or research Claude Code Agent Teams.
- Allowed: CC plugins, hooks, skills/commands, subagents, worktrees; plugin-bundled scripts; plugin-bundled MCP servers.
- Disallowed: any custom automation that launches additional Claude Code instances (no programmatic `claude ...` spawning).

## Glossary

- OMO "agent" -> CC "subagent" (leaf worker), plus a main-thread coordinator.
- OMO "tool" -> CC built-in tools OR MCP tools OR skill/command wrappers.
- OMO "hook" -> CC hook event handler (command/prompt/agent).
- OMO "category" -> CC routing convention (skill chooses a subagent/model profile).
- OMO "plan" -> CC plan artifacts (Markdown) stored in repo (project scope) and/or in CC plans directory.

## Tier A (Must Match)

Tier A defines behaviors that must be present for the system to feel like OMO.

1. **Two primary workflows**:
   - Ultrawork-style "just do it" (keyword-triggered or explicit command).
   - Plan -> Start Work (planning separated from execution).
2. **Agent specialization**:
   - Dedicated leaf workers for (a) codebase exploration and (b) external research and (c) architecture review.
3. **Continuation discipline**:
   - The system reliably continues until completion (with explicit circuit breakers).
4. **Session continuity**:
   - A resume mechanism exists across session restarts (state stored outside transient chat memory).
5. **Hard guardrails**:
   - No nested subagent spawning.
   - Background work does not assume MCP availability.
6. **Explicit documentation of gaps**:
   - Any non-parity is documented in a dedicated section (no silent deviations).

## Tier B (Should Match)

Tier B defines strong parity goals that improve the experience, but can be deferred if CC constraints make them expensive.

1. **Keyword detector modes** beyond ultrawork (e.g., search/investigate/analyze) implemented via `UserPromptSubmit`.
2. **Rules/rubric injection** to keep agent behavior consistent (coding conventions, safety rules).
3. **Output control**: best-effort truncation/containment strategies to avoid context blowups.
4. **Notification patterns** for long background work (within CC's supported mechanisms).
5. **Selftest harness** that validates workflows end-to-end inside a single CC session (no `claude` spawning).

## Tier C (Will Not Match / Known Gaps)

Tier C is explicitly accepted non-parity.

1. **Hidden model override**:
   - OMO can override the model used for an API call while leaving the UI/model indicator unchanged (via OpenCode internal storage manipulation).
   - CC plugin must NOT attempt this. Any model choice must be explicit/visible.
2. **First-class custom tools**:
   - OMO can add arbitrary tools via OpenCode plugin APIs.
   - CC plugins cannot add native tools; tool parity requires MCP servers or skill wrappers.
3. **Nested multi-agent orchestration**:
   - OMO can delegate from orchestrator to subagents that themselves orchestrate.
   - CC subagents cannot spawn subagents; orchestration remains main-thread only.
4. **Tool output rewriting**:
   - OMO can transform tool outputs via plugin hooks.
   - CC hooks are more constrained; we will favor pre-tool guardrails and workflow constraints.

## "Done" Definition

The system is considered complete when:
- Tier A items are implemented and verified via documented scenarios.
- Tier B items are either implemented or explicitly deferred with an issue list.
- Tier C items are documented as gaps with the closest CC-native workaround.
