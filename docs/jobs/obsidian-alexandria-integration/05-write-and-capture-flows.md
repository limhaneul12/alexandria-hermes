---
alexandria_type: job_plan
id: job_obsidian_alexandria_integration_05_write_capture_flows
tags:
  - write-flow
  - capture
  - markdown
  - obsidian
status: implemented
created_at: "2026-05-25"
source: codex
---

# Write and Capture Flows

## 목표

Agent, CLI, MCP, Obsidian plugin이 생성하는 durable artifact를 Obsidian Markdown note로 저장한다.
저장 성공 후 SQLite index를 갱신해 즉시 검색 가능하게 한다.

## context capture

```text
alexandria_capture_context
  -> validate payload and redact secrets
  -> choose folder by kind
  -> generate stable id
  -> render frontmatter
  -> render Markdown body
  -> atomic write
  -> reindex note
  -> return note id/path/wikilink
```

본문 기본형:

```md
# <Context Title>

## Summary

## Content

## Evidence

## Restore Prompt
```

## memory compact

현재 구현된 Obsidian-backed Memory Compact 흐름을 유지/확장한다.

```text
prepare compact candidate
  -> create Memory Compact Markdown
  -> if status CURRENT, supersede prior current for project
  -> source_refs frontmatter에 보존
  -> reindex note
```

주의:

- current compact는 source_refs 없이 받지 않는다.
- status enum은 기존 구현과 호환되게 `CURRENT`, `DRAFT`, `SUPERSEDED`, `ARCHIVED`를 유지한다.

## skill acquisition

```text
start_skill_acquisition
  -> job state 생성
  -> agent/librarian research
  -> complete_skill_acquisition
  -> Skills/Drafts/<title>.md 생성
  -> evidence_urls/source_summary 저장
  -> reindex note
  -> job result에 note id/path 반환
```

Skill body 기본형:

```md
# <Skill Title>

## When to use

## Inputs

## Procedure

## Outputs

## Failure modes

## Evidence
```

## prompt submit

```text
submit prompt candidate
  -> Prompts/<kind>/<title>.md 생성
  -> variables/model_hint/eval metadata 저장
  -> reindex note
```

Prompt body 기본형:

```md
# <Prompt Title>

## Purpose

## Template

## Variables

## Evaluation notes
```

## librarian chat transcript

```text
ask in Obsidian
  -> answer shown in side pane
  -> user clicks Save Chat or policy auto-save allows transcript
  -> Librarian/Chats/<conversation>.md 생성/append
  -> reindex note
```

## 완료 기준

- 각 write flow가 Markdown note를 만든다.
- 모든 생성 note에 필수 frontmatter가 있다.
- raw secret 패턴은 저장 전에 차단/경고된다.
- 저장 직후 search API에서 해당 note가 검색된다.
- path traversal, filename collision, id collision 테스트가 있다.
