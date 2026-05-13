# Alexandria-Hermes Backend MVP Prompt

You are a senior backend architect and FastAPI engineer.

Design and implement the backend MVP for **Alexandria-Hermes**.

Alexandria-Hermes is a library system for AI agents.

It helps agents and users organize, discover, register, search, recommend, and track usage of:

1. Skills
2. Workflows
3. Knowledge

This is NOT an autonomous agent runtime.
This is NOT an MCP marketplace.
This is NOT a prompt marketplace.
This is a structured library system for AI agents.

---

## Core Philosophy

AI agents can use the library in three ways:

1. Ask a librarian agent for recommendations
2. Browse the library manually through categories
3. Submit new skills, workflows, or knowledge into the library

The librarian is optional and selectable.

The system must support different librarian providers:

- GPT
- Claude
- Hermes
- Local model
- Future custom provider

The default provider does not need to be hardcoded.

---

## Tech Stack

Use:

- FastAPI
- Asyncer
- SQLAlchemy 2.x async
- SQLite
- SQLite FTS5
- Pydantic v2
- DDD-lite / Clean Architecture
- Repository pattern
- Service layer
- Dependency injection

Do NOT use:

- Redis
- Kafka
- Vector DB
- Graph DB
- Celery
- Kubernetes
- Complex multi-agent orchestration

Keep MVP lightweight.

---

## Public API Serialization Contract

OpenAPI examples and JSON payloads must use the public API contract:

- Public identifiers are UUID-like strings, not integers.
  - Applies to `id`, `category_id`, `parent_id`, `item_id`, `provider_id`,
    `preferred_librarian_provider`, and related item/skill id arrays.
- Enum fields are serialized as strings, for example `SKILL`, `DRAFT`,
  `ACTIVE`, `SEARCH`, `OPENAI`, and `API_KEY`.

---

## Core Domain Entities

### 1. Category

Hierarchical taxonomy.

Example:

Computer Science
 ├── Programming
 │    ├── Python
 │    └── FastAPI
 ├── Networking
 └── Distributed Systems
      ├── Kafka
      └── Redis Streams

Requirements:

- parent-child structure
- tree retrieval
- move category
- reorder category
- prevent circular references
- support depth validation

---

### 2. LibraryItem

Unified base object for:

- Skill
- Workflow
- Knowledge

Fields:

- id
- item_type: SKILL | WORKFLOW | KNOWLEDGE
- title
- summary
- content
- category_id
- tags
- status: DRAFT | ACTIVE | ARCHIVED | DEPRECATED
- source_type: USER_CREATED | AGENT_SUBMITTED | LIBRARIAN_CREATED | IMPORTED
- created_by_type: USER | AGENT | LIBRARIAN
- created_by_name
- created_at
- updated_at

---

### 3. Skill

A skill is an executable or reusable knowledge unit.

Examples:

- FastAPI async dependency injection
- Redis Streams consumer lag debugging
- Python async debugging

Additional fields:

- purpose
- input_schema
- output_schema
- usage_example
- required_tools
- risk_level: LOW | MEDIUM | HIGH
- version

Users must be able to manually create and edit skills.

Agents must also be able to submit skill candidates.

---

### 4. Workflow

A workflow is a sequence of skills or steps.

Fields:

- steps
- related_skill_ids
- expected_result
- use_case

---

### 5. Knowledge

Reference-style library content.

Fields:

- body
- references
- related_items

---

### 6. UsageHistory

Track when an item is used.

Fields:

- id
- item_id
- item_type
- agent_name
- librarian_provider
- query
- selection_source: RECOMMENDATION | MANUAL_BROWSE | SEARCH | DIRECT_LINK
- used_at
- success
- feedback

This powers:

- recent skills
- frequently used skills
- popular items by category
- future recommendation improvement

---

### 7. AgentProfile

Agents that use the library.

Fields:

- id
- name
- provider
- description
- capabilities
- preferred_librarian_provider
- created_at
- updated_at

Examples:

- GPT
- Claude
- Hermes
- Local Agent

---

### 8. LibrarianProvider

Selectable librarian provider.

Fields:

- id
- name
- provider_type: OPENAI | ANTHROPIC | HERMES | LOCAL | CUSTOM
- auth_type: API_KEY | OAUTH | NONE
- enabled
- config
- created_at
- updated_at

Important:

- API key and OAuth support should both be available from settings.
- Neither API key nor OAuth should be treated as the only primary path.
- Settings should allow users to configure either method depending on provider.
- Sensitive values must be stored safely or abstracted behind a secret manager interface, even if MVP uses SQLite.

---

## Skill Submission Flow

The system must support three skill registration paths.

### Path 1: User manually creates a skill

User fills in:

- title
- purpose
- category
- description
- content
- input_schema
- output_schema
- tags
- usage_example

Then backend stores it as:

source_type = USER_CREATED
created_by_type = USER

---

### Path 2: Agent directly submits a skill

Agent sends a structured skill payload to the API.

Backend validates it and stores it as:

source_type = AGENT_SUBMITTED
created_by_type = AGENT
status = DRAFT or ACTIVE depending on request

---

### Path 3: Agent asks librarian to register a skill

Agent sends an unstructured request such as:

"Please create a skill for FastAPI async dependency injection."

Backend passes it to selected librarian provider.

Librarian returns a structured skill candidate.

Backend stores the result as:

source_type = LIBRARIAN_CREATED
created_by_type = LIBRARIAN
status = DRAFT

User can review and activate it.

---

## Required API Endpoints

Design REST APIs for:

### Category

- POST /categories
- GET /categories
- GET /categories/tree
- GET /categories/{id}
- PATCH /categories/{id}
- PATCH /categories/{id}/move
- DELETE /categories/{id}

### Library Items

- POST /items
- GET /items
- GET /items/{id}
- PATCH /items/{id}
- DELETE /items/{id}

### Skills

- POST /skills
- POST /skills/submit-by-agent
- POST /skills/generate-with-librarian
- GET /skills
- GET /skills/{id}
- PATCH /skills/{id}
- DELETE /skills/{id}

### Workflows

- POST /workflows
- GET /workflows
- GET /workflows/{id}
- PATCH /workflows/{id}
- DELETE /workflows/{id}

### Knowledge

- POST /knowledge
- GET /knowledge
- GET /knowledge/{id}
- PATCH /knowledge/{id}
- DELETE /knowledge/{id}

### Search

- GET /search?q=
- GET /search/skills?q=
- GET /search/workflows?q=
- GET /search/knowledge?q=

Use SQLite FTS5.

### Usage

- POST /usage
- GET /usage/recent
- GET /usage/popular
- GET /usage/popular/by-category
- GET /usage/items/{id}

### Agents

- POST /agents
- GET /agents
- GET /agents/{id}
- PATCH /agents/{id}
- DELETE /agents/{id}

### Librarian Providers

- POST /settings/librarians
- GET /settings/librarians
- GET /settings/librarians/{id}
- PATCH /settings/librarians/{id}
- DELETE /settings/librarians/{id}
- POST /settings/librarians/{id}/test

### Recommendation

- POST /librarian/recommend
- POST /librarian/classify
- POST /librarian/create-skill-candidate

---

## Architecture Requirements

Use this folder structure:

app/
├── library/
│   ├── domain/
│   │   ├── entities/
│   │   ├── repositories/
│   │   └── exceptions/
│   ├── application/
│   │   ├── category_service.py
│   │   ├── item_service.py
│   │   ├── skill_service.py
│   │   ├── workflow_service.py
│   │   ├── knowledge_service.py
│   │   ├── usage_service.py
│   │   └── librarian_service.py
│   ├── infrastructure/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── search/
│   │   └── librarian_providers/
│   └── interface/
│       ├── routers/
│       └── schemas/
│
├── agents/
├── settings/
├── shared/
└── main.py

---

## Output Required

Provide:

1. Backend architecture overview
2. Domain model
3. SQLite schema
4. SQLAlchemy models
5. Pydantic schemas
6. Repository interfaces
7. Service layer design
8. API endpoint design
9. Search design using SQLite FTS5
10. Usage tracking flow
11. Skill submission flow
12. Librarian provider settings flow
13. API key and OAuth setting design
14. Development order
15. MVP scope boundaries

Be practical.
Avoid overengineering.