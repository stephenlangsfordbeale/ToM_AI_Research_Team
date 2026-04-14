# Instruction Archive Index

Last archive pass: 2026-04-14

Purpose: keep one active top-level brief (`program.md`) while preserving surplus instruction surfaces for later referral/recovery.

## Active top-level brief

- `program.md` (repo root)

## Archived files (safe relocation)

| Former path | Archived path | Reason |
|---|---|---|
| `# Mission.md` | `archive/instructions/top-level/Mission.md` | Overlapped with `program.md`; kept as historical detailed mission brief. |
| `AZURE_ML_UPLOAD_CHECKLIST.md` | `archive/instructions/top-level/AZURE_ML_UPLOAD_CHECKLIST.md` | Legacy upload/checklist surface, not primary local-first workflow. |
| `.github/instructions/train-py-research.instructions.md` | `archive/instructions/github/instructions/train-py-research.instructions.md` | Duplicate guardrail surface vs current OMX/AGENTS + canonical docs. |
| `.github/prompts/append-tom-run-note.prompt.md` | `archive/instructions/github/prompts/append-tom-run-note.prompt.md` | Legacy GitHub prompt surface archived for reference. |
| `.github/prompts/tom-overnight-session.prompt.md` | `archive/instructions/github/prompts/tom-overnight-session.prompt.md` | Legacy GitHub prompt surface archived for reference. |
| `.github/agents/ACCOUNTANT.agent.md` | `archive/instructions/github/agents/ACCOUNTANT.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/CONTROLLER.agent.md` | `archive/instructions/github/agents/CONTROLLER.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/CRITIC.agent.md` | `archive/instructions/github/agents/CRITIC.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/PLANNER.agent.md` | `archive/instructions/github/agents/PLANNER.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/RESEARCHER.agent.md` | `archive/instructions/github/agents/RESEARCHER.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/STORYTELLER.agent.md` | `archive/instructions/github/agents/STORYTELLER.agent.md` | Legacy GitHub role agent definition archived. |
| `.github/agents/tom-overnight-researcher.agent.md` | `archive/instructions/github/agents/tom-overnight-researcher.agent.md` | Legacy GitHub meta-agent definition archived. |

## Restore quick commands

Restore one file:

```bash
git mv archive/instructions/top-level/Mission.md '# Mission.md'
```

Restore all archived instruction files to original locations:

```bash
git mv archive/instructions/top-level/Mission.md '# Mission.md'
git mv archive/instructions/top-level/AZURE_ML_UPLOAD_CHECKLIST.md AZURE_ML_UPLOAD_CHECKLIST.md
git mv archive/instructions/github/instructions/train-py-research.instructions.md .github/instructions/train-py-research.instructions.md
git mv archive/instructions/github/prompts/append-tom-run-note.prompt.md .github/prompts/append-tom-run-note.prompt.md
git mv archive/instructions/github/prompts/tom-overnight-session.prompt.md .github/prompts/tom-overnight-session.prompt.md
git mv archive/instructions/github/agents/*.agent.md .github/agents/
```

## Notes

- This archive is a relocation, not deletion; git history remains intact.
- Canonical operational guidance still comes from AGENTS/OMX runtime + `docs/` + `program.md`.
