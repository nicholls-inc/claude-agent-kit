# OMO -> Claude Code (CLI) Mapping

## Purpose

This document maps every oh-my-opencode (OMO) capability to a Claude Code (CC) CLI-native equivalent.

Rules:
- If there is no 1:1 equivalent, propose the closest CC-native workaround.
- If a workaround changes semantics, assign it Tier C in `design/parity-contract.md` and justify the deviation.
- Every mapping row must include a verification approach.

## Inputs

- Parity contract: `design/parity-contract.md`
- CC capability constraints: `design/claude-code-capabilities.md`
- OMO inventory: `design/omo-inventory.md`

## Mapping Table Schema

| OMO capability | OMO location (files) | CC equivalent mechanism | Workaround | Parity tier (A/B/C) | Verification approach |
| --- | --- | --- | --- | --- | --- |

## Core Workflows

| OMO capability | OMO location (files) | CC equivalent mechanism | Workaround | Parity tier (A/B/C) | Verification approach |
| --- | --- | --- | --- | --- | --- |
| Ultrawork mode (`ulw`/`ultrawork` keyword) | `src/hooks/keyword-detector/*`, `src/hooks/keyword-detector/ultrawork/*` | `UserPromptSubmit` hook + `/omo:ulw` skill | Hook detects keyword and prepends an instruction block that forces (a) parallel subagent research and (b) verification gates. No hidden model override. | A/B | Trigger with keyword; confirm hook fires; confirm additional instruction appears; run a small task and confirm research + verification occurs. |
| Plan (Prometheus) then Start Work (Atlas) | `docs/orchestration-guide.md`, `src/hooks/start-work/*`, `src/features/boulder-state/*` | `/omo:plan` skill (plan mode) + `/omo:start-work` skill + repo state files | Use CC plan permission mode for read-only plan generation; store plan in repo; resume via boulder state file; use Stop hook to enforce continuation. | A | Create plan artifact; restart session; run start-work; verify resume. |
| Session continuity (boulder.json) | `src/features/boulder-state/*` | Repo file state + `SessionStart` hook | On SessionStart, read state file and inject "resuming" context; avoid dependence on CC internal task lists. | A | Restart session; verify resume context injected. |
| Ralph loop | `src/hooks/ralph-loop/*`, `src/features/builtin-commands/templates/ralph-loop.ts` | `/omo:ralph-loop` skill + `Stop` hook | Store loop state in repo (or local) file; Stop hook continues until done marker or max iterations; include manual cancel. | A/B | Start loop; verify it continues automatically; cancel via command. |

## Agents

OMO agents must be expressed as CC plugin subagents (leaf workers) plus skills that coordinate them from the main thread.

| OMO agent | OMO location | CC equivalent | Notes | Tier |
| --- | --- | --- | --- | --- |
| Sisyphus | `src/agents/sisyphus.ts` | Main-thread coordinator behavior packaged as skills + optional output style | CC plugins cannot replace the core agent globally; implement Sisyphus as an opt-in workflow (skills) and/or a named subagent used as the main agent via `--agent`. | A (workflow), C (default agent replacement) |
| Hephaestus | `src/agents/hephaestus.ts` | `agents/hephaestus.md` subagent (foreground) | In CC, Hephaestus can be a subagent for self-contained deep tasks, but it cannot spawn other subagents. If it must orchestrate, keep orchestration in main thread and use a skill to drive leaf workers. | B/C |
| Prometheus | `src/agents/prometheus/*` | Plan-mode workflow (`permissionMode: plan`) + `agents/prometheus.md` | Enforce read-only planning via permissionMode + tool allowlist and hooks. | A |
| Atlas | `src/agents/atlas/*`, `src/hooks/atlas/*` | Main-thread `/omo:start-work` executor + leaf workers | In CC, Atlas-like behavior is best implemented in the main thread (skills + hooks) because leaf subagents cannot coordinate other subagents. | A |
| Explore | `src/agents/explore.ts` | Built-in `Explore` subagent or plugin `agents/omo-explore.md` | Prefer built-in Explore for speed; provide OMO-flavored prompt if needed. | A |
| Librarian | `src/agents/librarian.ts` | Plugin subagent `agents/omo-librarian.md` | Uses WebFetch/MCP for external docs/OSS; keep read-only tools. | A |
| Oracle | `src/agents/oracle.ts` | Plugin subagent `agents/omo-oracle.md` | Read-only verifier/reviewer; no edits. | A |
| Metis | `src/agents/metis.ts` | Plugin subagent `agents/omo-metis.md` | Plan gap analysis. | A |
| Momus | `src/agents/momus.ts` | Plugin subagent `agents/omo-momus.md` | Plan review loop (OKAY/REJECT). | A |
| Multimodal-Looker | `src/agents/multimodal-looker.ts` | CC native vision support / dedicated subagent | If CC CLI supports image/PDF analysis, use built-in; otherwise add a subagent prompt that uses available media tools. | B |

## Skills / Commands

In CC plugins, skills create slash commands but are namespaced by plugin name (e.g., `/omo:start-work`).

| OMO command/skill | OMO location | CC equivalent | Notes | Tier |
| --- | --- | --- | --- | --- |
| `/start-work` | `src/features/builtin-commands/templates/start-work.ts`, `src/hooks/start-work/*` | `/omo:start-work` skill | Creates/resumes repo boulder state and kicks off execution workflow. | A |
| `/ralph-loop` | `src/features/builtin-commands/templates/ralph-loop.ts`, `src/hooks/ralph-loop/*` | `/omo:ralph-loop` skill | Loop continuation via Stop hook + loop state file. | A/B |
| `/ulw-loop` | `src/features/builtin-commands/templates/ralph-loop.ts` | `/omo:ulw-loop` skill | Same as ralph-loop but inject ultrawork mode text each iteration. | B |
| `/cancel-ralph` | `src/features/builtin-commands/templates/ralph-loop.ts` | `/omo:cancel-ralph` skill | Clears loop state file; Stop hook respects cancellation. | A |
| `/stop-continuation` | `src/features/builtin-commands/templates/stop-continuation.ts`, `src/hooks/stop-continuation-guard/*` | `/omo:stop-continuation` skill + Stop hook escape hatch | Must exist to prevent infinite Stop loops. | A |
| `/init-deep` | `src/features/builtin-commands/templates/init-deep.ts` | `/omo:init-deep` skill | Generates AGENTS.md hierarchy; in CC we can generate `.claude/agents` or `AGENTS.md` depending on desired parity. | B |
| `/refactor` | `src/features/builtin-commands/templates/refactor.ts` | `/omo:refactor` skill | In CC, lean on built-in tools (grep/lsp) and an explicit refactor playbook; avoid claiming OpenCode-only tooling. | B/C |
| `/handoff` | `src/features/builtin-commands/templates/handoff.ts` | `/omo:handoff` skill | Produce continuation summary; store in repo file. | B |
| `git-master` | `src/features/builtin-skills/git-master/SKILL.md` | Plugin skill `/omo:git-master` | CC already supports git via Bash; skill provides strict rules. | A/B |
| `playwright` | `src/features/builtin-skills/playwright/SKILL.md` | Plugin skill `/omo:playwright` + plugin MCP server config | Bundle Playwright MCP via `.mcp.json` and route browser tasks through it. | A/B |
| `frontend-ui-ux` | `src/features/builtin-skills/frontend-ui-ux/SKILL.md` | Plugin skill `/omo:frontend-ui-ux` | Pure prompt skill. | A/B |

## Tools

CC cannot add native tools directly; tool parity splits into:
- Built-in CC tools (Grep/Glob/Read/Edit/Bash/Task)
- MCP tools (for new capabilities)
- Skills (to standardize procedures)

| OMO tool | OMO location | CC equivalent | Notes | Tier |
| --- | --- | --- | --- | --- |
| `task` delegation | `src/tools/delegate-task/*`, `src/plugin/tool-registry.ts` | CC `Task` tool (spawn subagents) + skills to route | CC supports `Task(agent_type)`; categories become subagent roster and conventions. | A/B |
| `background_output`/`background_cancel` | `src/tools/background-task/*` | CC background tasks UI + subagent transcripts | CC has background subagents; cancellation/inspection via built-in UI and transcript files. | B |
| `grep`/`glob` | `src/tools/grep/*`, `src/tools/glob/*` | CC built-in Grep/Glob | 1:1. | A |
| LSP tools | `src/tools/lsp/*` | CC LSP integration (via `.lsp.json` or marketplace) | Provide `.lsp.json` in plugin if needed; rely on CC built-ins. | A/B |
| `skill`/`slashcommand` | `src/tools/skill/*`, `src/tools/slashcommand/*` | CC skills/commands | 1:1 concept, different wiring. | A |
| `skill_mcp` | `src/tools/skill-mcp/*` | CC MCP tools directly | CC interacts with MCP tools as first-class. | A |
| `interactive_bash` | `src/tools/interactive-bash/*` | CC built-in terminal interaction + Bash tool | No tmux requirement in CC; tmux visual panes not native. | B/C |
| `hashline_edit` | `src/tools/hashline-edit/*` | CC Edit tool + PreToolUse guardrails | CC cannot replace Edit semantics fully; approximate with hooks that require Read-before-Edit and verify anchors where possible. | C |

## Hooks

Hook mapping focuses on CC events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `SessionEnd`, `ConfigChange`.

| OMO hook | OMO location | CC hook event(s) | CC hook type | Notes / caveats | Tier |
| --- | --- | --- | --- | --- | --- |
| keyword-detector | `src/hooks/keyword-detector/*` | `UserPromptSubmit` | command | Add context block to prompt; cannot use OpenCode message transform; avoid rewriting prompt destructively. | A/B |
| start-work | `src/hooks/start-work/*` | skill (`/omo:start-work`) + `UserPromptSubmit` | skill + command | CC hooks cannot intercept slash command execution identically; implement as explicit skill rather than implicit hook-only. | A |
| todo-continuation-enforcer | `src/hooks/todo-continuation-enforcer/*` | `Stop` | command | Block Stop until checklist complete; must include circuit breaker + escape hatch. | A |
| atlas (boulder orchestrator) | `src/hooks/atlas/*` | `Stop` + `SubagentStop` | command/agent | In CC, use Stop hook + state files to decide next continuation action. | A/B |
| ralph-loop | `src/hooks/ralph-loop/*` | `Stop` | command | Same continuation pattern; state in file. | A/B |
| rules-injector | `src/hooks/rules-injector/*` | `SessionStart` + `UserPromptSubmit` + `PreToolUse(Edit|Write)` | command | SessionStart stdout is injected; PreToolUse can block disallowed edits. | B |
| comment-checker | `src/hooks/comment-checker/*` | `PostToolUse(Edit|Write)` | prompt/command | CC can warn or block via PostToolUse decision when supported; otherwise warn. | B |
| write-existing-file-guard | `src/hooks/write-existing-file-guard/*` | `PreToolUse(Write|Edit)` | command | Require Read before Edit/Write; block on exit 2. | A/B |
| tool-output-truncator | `src/hooks/tool-output-truncator/*` | `PostToolUse` | command | CC cannot rewrite tool outputs for context reliably; mitigate by constraining tools and encouraging scoped queries. | C |

## Appendix: Full OMO Hook Coverage (44)

This appendix ensures every OMO hook name appears at least once in the mapping.

Source of truth: `src/hooks/AGENTS.md` (tiered hook list).

| OMO hook | Primary OMO event(s) | CC equivalent event(s) | Parity notes |
| --- | --- | --- | --- |
| contextWindowMonitor | session.idle | Stop / PreCompact | CC lacks OpenCode context %; approximate via heuristics + compaction events. |
| preemptiveCompaction | session.idle | PreCompact | CC auto-compaction exists; hook can warn earlier; cannot perfectly emulate token math. |
| sessionRecovery | session.error | PostToolUseFailure + Stop | CC has PostToolUseFailure; recovery becomes skill-driven retries + Stop continuation. |
| sessionNotification | session.idle | Notification / Stop | CC notifications exist; behavior depends on CLI support. |
| thinkMode | chat.params | UserPromptSubmit (inject instruction) | CC supports thinking mode in settings; cannot change model params per-message invisibly. |
| anthropicContextWindowLimitRecovery | session.error | PreCompact / Stop | CC compaction hook exists; implement "reduce output" rules. |
| autoUpdateChecker | session.created | SessionStart | CC plugin can log version; cannot query npm without network permissions. |
| agentUsageReminder | chat.message | UserPromptSubmit | Inject reminders as context. |
| nonInteractiveEnv | tool/ chat | SessionStart | Detect env vars and adjust instructions. |
| interactiveBashSession | tool.execute | PreToolUse(Bash) | CC has Bash tool; tmux panes are optional script-only. |
| ralphLoop | event + session.idle | Stop | Loop continuation via Stop and state file. |
| editErrorRecovery | tool.execute.after | PostToolUseFailure(Edit) | Retry pattern can be implemented via follow-up prompt or skill. |
| delegateTaskRetry | tool.execute.after | PostToolUseFailure(Task) | Retry limited by CC task tool behavior. |
| startWork | chat.message | skill | Implement as explicit `/omo:start-work` skill. |
| prometheusMdOnly | tool.execute.before | PreToolUse(Edit|Write) | Enforce planner write restrictions with deny rules. |
| sisyphusJuniorNotepad | chat.message | SessionStart + SubagentStart | Use CC agent memory or repo files for notepad. |
| questionLabelTruncator | tool.execute.before | PreToolUse(AskUserQuestion) | CC AskUserQuestion exists; guard for large option labels as best effort. |
| taskResumeInfo | chat.message | SessionStart | Use transcript + state file to remind resume context. |
| anthropicEffort | chat.params | (settings) | CC does not expose OpenAI-style effort; for Anthropic use thinking mode settings. |
| jsonErrorRecovery | tool.execute.after | PostToolUseFailure | Detect JSON parsing failures from hook output; avoid noisy stdout in hooks. |
| sisyphusGptHephaestusReminder | chat.message | UserPromptSubmit | In CC, model choice is explicit; show reminder when user picks model. |
| taskReminder | tool.execute.after | Stop | Remind to use Task/subagents when large work is detected. |
| commentChecker | tool.execute.after | PostToolUse(Edit|Write) | Warn on excessive comments. |
| toolOutputTruncator | tool.execute.after | PostToolUse | Cannot truncate tool output; constrain via tool use guidance. |
| directoryAgentsInjector | tool.execute.before | SessionStart + UserPromptSubmit | CC already loads CLAUDE.md; emulate AGENTS.md injection by reading files in hooks. |
| directoryReadmeInjector | tool.execute.before | SessionStart + UserPromptSubmit | Similar to AGENTS injection. |
| emptyTaskResponseDetector | tool.execute.after | PostToolUseFailure(Task) | Detect empty summaries from subagents and retry in foreground. |
| rulesInjector | tool.execute.before | SessionStart + PreToolUse(Edit|Write) | Inject rules at start; block violations at PreToolUse. |
| tasksTodowriteDisabler | tool.execute.before | N/A | CC has Tasks built-in; no need to disable TodoWrite if using Tasks. |
| writeExistingFileGuard | tool.execute.before | PreToolUse(Edit|Write) | Enforce Read-before-Edit/Write. |
| hashlineReadEnhancer | tool.execute.after | N/A | CC Read output cannot be rewritten reliably; can add "anchor" conventions instead. |
| stopContinuationGuard | chat.message | UserPromptSubmit + Stop | Escape hatch that sets a stop flag to let Stop hook exit. |
| compactionContextInjector | session.compacted | PreCompact | Provide a compaction summary prompt file and inject at PreCompact. |
| compactionTodoPreserver | session.compacted | PreCompact | Persist checklist state to repo file. |
| todoContinuationEnforcer | session.idle | Stop | Block Stop until checklist complete. |
| unstableAgentBabysitter | session.idle | SubagentStop | Detect failures and recommend switching to foreground. |
| backgroundNotificationHook | event | Notification | Notify on background completion. |
| atlasHook | event | Stop | Main continuation/orchestration loop in CC. |
| categorySkillReminder | chat.message | UserPromptSubmit | Remind that routing uses skills/subagents rather than categories. |
| autoSlashCommand | chat.message | UserPromptSubmit | CC already has skills; optional to detect bare text and suggest command. |
| contextInjectorMessagesTransform | messages.transform | SessionStart / UserPromptSubmit | CC lacks general transform; approximate by injected context text. |
| thinkingBlockValidator | messages.transform | PreToolUse | CC hooks should enforce JSON-only output; no thinking block injection in hooks. |
| claudeCodeHooks | messages.transform | N/A | OMO compatibility layer not needed when living inside CC. |

## Appendix: Full OMO Tool Coverage (26)

Source of truth: `src/tools/AGENTS.md`.

| OMO tool | CC equivalent | Notes |
| --- | --- | --- |
| task_create | CC Tasks (built-in) or repo checklist | Prefer CC Tasks for structured dependencies; if not available, use plan checklist. |
| task_list | CC Tasks | 1:1 concept. |
| task_get | CC Tasks | 1:1 concept. |
| task_update | CC Tasks | 1:1 concept. |
| task (delegate) | CC Task tool (spawn subagent) | Categories become explicit subagent choices. |
| call_omo_agent | CC Task(subagent) | Map to specific subagent types. |
| background_output | CC background UI + transcripts | Inspect via built-in UI; optionally read transcript files. |
| background_cancel | CC background UI | Cancel via UI if supported; otherwise use stop flags. |
| lsp_goto_definition | CC LSP | Use built-in LSP features or plugin .lsp.json. |
| lsp_find_references | CC LSP | Same. |
| lsp_symbols | CC LSP | Same. |
| lsp_diagnostics | CC LSP | Same. |
| lsp_prepare_rename | CC LSP | Same. |
| lsp_rename | CC LSP | Same. |
| ast_grep_search | MCP ast-grep server (optional) | CC does not ship ast-grep; provide MCP if needed. |
| ast_grep_replace | MCP ast-grep server (optional) | Same. |
| grep | CC Grep | Same. |
| glob | CC Glob | Same. |
| session_list | CC transcripts + /resume | No 1:1 tool; approximate via filesystem transcripts. |
| session_read | CC transcripts | Read transcript file paths from hook inputs. |
| session_search | CC grep over transcripts | Implement via Bash+rg on transcript directory. |
| session_info | CC transcript metadata | Best-effort. |
| skill | CC skills | Native. |
| skill_mcp | CC MCP tools | Native. |
| slashcommand | CC skills/commands | Native. |
| interactive_bash | CC Bash tool | tmux integration optional. |
| look_at | CC multimodal | Depends on CLI build; if unsupported, omit. |
| hashline_edit | Not available | Tier C; approximate with Read-before-Edit and careful anchor usage. |


## Hook Feasibility Grid

This section maps OMO hook behaviors to CC hook events and highlights which CC hook mechanism is best.

| OMO hook / behavior | OMO location | CC hook event | CC hook type | Notes / caveats |
| --- | --- | --- | --- | --- |

| keyword-detector (mode injection) | `src/hooks/keyword-detector/*` | `UserPromptSubmit` | command | Best-effort inject context, not rewrite. |
| stop-continuation-guard | `src/hooks/stop-continuation-guard/*` | `UserPromptSubmit` + `Stop` | command | Escape hatch command toggles state file. |
| todo-continuation-enforcer | `src/hooks/todo-continuation-enforcer/*` | `Stop` | command | Block Stop; circuit breaker. |
| start-work plan selection | `src/hooks/start-work/*` | skill | skill | Prefer explicit command/skill. |
| write-existing-file-guard | `src/hooks/write-existing-file-guard/*` | `PreToolUse(Edit|Write)` | command | Implement Read-before-Edit/Write gating. |
| comment-checker | `src/hooks/comment-checker/*` | `PostToolUse(Edit|Write)` | prompt/command | Warn; block if supported. |

## Category / Agent Routing

Map OMO categories and agent roles to CC equivalents.

| OMO concept | OMO location | CC equivalent | Notes |
| --- | --- | --- | --- |

| visual-engineering | `docs/features.md` + categories in config | `agents/frontend.md` subagent + `/omo:frontend-ui-ux` skill | CC does not have categories; emulate via subagent roster and skills. |
| ultrabrain | `docs/features.md` + categories in config | `agents/oracle.md` (or a "deep reasoning" subagent) | Prefer Opus/Sonnet selection explicitly; no hidden routing. |
| quick | `docs/features.md` | Use `haiku` model subagent for trivial tasks | CC subagent model aliases support haiku/sonnet/opus. |

## Hard Gaps (Non-portable) + Closest Workarounds

1. Hidden model override
   - OMO: `src/plugin/ultrawork-model-override.ts` (OpenCode storage mutation)
   - CC: not possible; model selection must be explicit.
   - Workaround: implement ultrawork as an explicit skill/subagent selection with visible model choice.
   - Tier: C

2. First-class custom tools
   - OMO: tool registry (`src/plugin/tool-registry.ts`) provides many non-MCP tools.
   - CC: cannot add native tools directly.
   - Workaround: implement tool-like behaviors as skills + hooks; add true new tools only via MCP servers.
   - Tier: C (partial)

3. Nested orchestration
   - OMO: deep delegation patterns across agents.
   - CC: subagents cannot spawn subagents.
   - Workaround: keep orchestration in main thread; subagents are leaf workers.
   - Tier: C

4. Background + MCP tool availability
   - OMO: background task tool access includes all plugin tools.
   - CC: background subagents cannot use MCP tools.
   - Workaround: background tasks restricted to built-in tools; MCP tasks run foreground.
   - Tier: B/C depending on feature.

5. Tool output transformation
   - OMO: transforms/injects tool outputs via plugin hooks.
   - CC: only some hook stdout becomes context (notably `SessionStart`, `UserPromptSubmit`).
   - Workaround: apply constraints at `PreToolUse` (block/modify) and via skill prompts.
   - Tier: C (partial)

6. Plugin namespacing (command names)
   - OMO: `/start-work`, `/ralph-loop` are global command names in OpenCode.
   - CC: plugin skills are namespaced (`plugin-name:skill`).
   - Workaround: ship canonical commands as `/omo:start-work`, etc. Optionally provide a project-local alias skill in `.claude/skills/start-work/` for teams that want un-namespaced commands.
   - Tier: C
