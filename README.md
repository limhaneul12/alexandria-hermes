# ALEXANDRIA-HERMES

> AI Agent Capability Library & Operational Knowledge Archive

<p align="center">
  <img src="./docs/assets/alexandria-hermes-library.png" alt="ALEXANDRIA-HERMES grand archive concept art" width="100%" />
</p>

ALEXANDRIA-HERMES is a digital archive system being built for the AI Agent era.

It organizes executable skills, workflows, operational knowledge, and reusable capabilities into a structured library system inspired by grand archives and modern AI operating platforms.

This project is currently under active production. The current milestone is a working frontend MVP and local archive foundation; the broader agent-native archive system is still being designed and expanded.

Rather than acting as a traditional documentation tool, ALEXANDRIA-HERMES focuses on:

- Capability-centric knowledge management
- AI agent skill organization
- Workflow and execution history tracking
- Searchable operational archives
- Reusable engineering knowledge
- Agent-compatible skill registries
- Library-style exploration for operational capabilities

The platform combines concepts from:

- digital libraries
- developer knowledge systems
- AI workflow registries
- internal operational platforms
- capability marketplaces
- persistent agent memory systems

Core philosophy:

> “Knowledge should not only be stored.  
> It should remain executable, searchable, reusable, and operational.”

---

## Current Build Status

ALEXANDRIA-HERMES is not finished yet.

The project is currently focused on building the first operational archive experience:

- a grand archive dashboard
- a searchable capability library
- skill and workflow detail views
- local archive data modeling
- usage and recommendation primitives
- a premium dark library interface
- a foundation for future agent-aware workflows

The goal is to evolve from a visual MVP into a practical operating layer for AI agents and engineers.

---

## Core Features

- Grand Archive Dashboard
- Skill Registry System
- Workflow Library
- Knowledge Documents
- Category Explorer
- Usage Analytics
- Recommendation System
- Agent-aware Search
- Split-view Skill Detail UI
- SQLite + Prisma-powered local archive
- Reusable capability cards inspired by premium digital libraries

---

## Product Direction

ALEXANDRIA-HERMES is designed around the idea that AI agents need more than chat history.

They need a structured operating memory:

- what skills exist
- when to use them
- how they were used before
- which workflows are reliable
- which knowledge documents support execution
- what should be reused instead of rediscovered

In that sense, ALEXANDRIA-HERMES is not just a documentation interface. It is being shaped as a capability archive where agent knowledge can become discoverable, versioned, reusable, and operational.

---

## Hermes Agent Reference

This project takes conceptual inspiration from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), especially its direction around agent memory, skill growth, tool use, subagent delegation, cross-session continuity, and run-anywhere agent operation.

ALEXANDRIA-HERMES is not intended to copy Hermes Agent directly.

Instead, it adapts a few useful ideas into our own product direction:

- skills as reusable operational memory
- agent experience becoming structured knowledge
- archives that support search, recall, and future execution
- workflows that can be improved over time
- capability systems that can serve both humans and agents

Hermes Agent focuses on the self-improving agent runtime.  
ALEXANDRIA-HERMES focuses on the archive, registry, and knowledge operating layer around agent capabilities.

---

## Application Areas

ALEXANDRIA-HERMES is designed for:

- developers
- AI operators
- workflow engineers
- internal platform teams
- autonomous agent ecosystems
- engineering knowledge curators
- teams building reusable agent capabilities

---

## Local Development

Frontend:

```bash
cd frontend
npm install
npx prisma migrate dev
npm run dev
```

Backend:

```bash
cd backend
uv sync
uv run pytest -q
```

Full stack:

```bash
docker compose up --build
```

Local endpoints:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health/live`

---

## Vision

ALEXANDRIA-HERMES aims to become:

> “A Steam Library for AI Capabilities”  
> mixed with  
> “an Operational Knowledge OS for Agents and Engineers.”

It is designed for developers, AI operators, workflow engineers, and future autonomous agent ecosystems.
