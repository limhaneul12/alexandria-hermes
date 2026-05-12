import { prisma } from "@/lib/prisma";

const categorySeeds = [
  { name: "Computer Science", slug: "computer-science", parentSlug: null },
  { name: "Programming", slug: "programming", parentSlug: "computer-science" },
  { name: "Python", slug: "python", parentSlug: "programming" },
  { name: "FastAPI", slug: "fastapi", parentSlug: "python" },
  { name: "DevOps", slug: "devops", parentSlug: "computer-science" },
  { name: "System Design", slug: "system-design", parentSlug: "computer-science" },
];

const skillSeeds = [
  {
    title: "FastAPI Dependency Injection",
    slug: "fastapi-dependency-injection",
    description: "Compose FastAPI dependencies, request sessions, and domain services without leaking infrastructure.",
    content: "Use explicit dependency helpers for request-scoped resources, keep providers async-safe, and route use cases through narrow ports.\n\nUsage Guide:\n- Define ports in the domain layer.\n- Map ORM rows in infrastructure adapters.\n- Keep router dependencies async-safe.\n\n```py\nasync def get_service(session = Depends(get_db_session)):\n    return Service(repo=Repository(session=session))\n```",
    type: "SKILL",
    version: "2.1.0",
    author: "Hermes Librarian",
    categorySlug: "fastapi",
    tags: ["FastAPI", "DI", "Python"],
  },
  {
    title: "Redis Streams Consumer Recovery",
    slug: "redis-streams-consumer-recovery",
    description: "Recover stalled Redis stream consumers, pending entries, and replay windows safely.",
    content: "Inspect pending entries, claim orphaned messages, and apply retry/drop policy with idempotency keys.\n\n```bash\nXINFO GROUPS events\nXPENDING events workers\n```",
    type: "WORKFLOW",
    version: "1.4.3",
    author: "Operations Scribe",
    categorySlug: "devops",
    tags: ["Redis", "Streams", "Recovery"],
  },
  {
    title: "AsyncIO Event Loop Deep Dive",
    slug: "asyncio-event-loop-deep-dive",
    description: "Operating notes for scheduling, cancellation, shielding, and async backpressure.",
    content: "Treat cancellation as a first-class signal. Use bounded queues and explicit timeouts at IO edges.\n\n```py\nasync with asyncio.timeout(3):\n    await client.fetch()\n```",
    type: "KNOWLEDGE",
    version: "3.0.0",
    author: "Alexandria Core",
    categorySlug: "python",
    tags: ["AsyncIO", "Python", "Concurrency"],
  },
  {
    title: "Celery Retry Strategy",
    slug: "celery-retry-strategy",
    description: "Retry, backoff, dead-letter, and idempotency conventions for resilient task processing.",
    content: "Separate transient failures from permanent domain failures. Use bounded retry counts and observable drop policy.\n\n```py\nraise self.retry(exc=exc, countdown=backoff)\n```",
    type: "WORKFLOW",
    version: "1.8.1",
    author: "Hermes Librarian",
    categorySlug: "devops",
    tags: ["Celery", "Retries", "Queues"],
  },
  {
    title: "SQLAlchemy Session Management",
    slug: "sqlalchemy-session-management",
    description: "Async SQLAlchemy session lifecycle rules for repositories and transactions.",
    content: "Create sessions at request boundaries, commit once per success, rollback on failure, and keep ORM models inside infrastructure.\n\n```py\nasync with sessionmaker() as session:\n    yield session\n```",
    type: "SKILL",
    version: "2.0.2",
    author: "Database Archivist",
    categorySlug: "python",
    tags: ["SQLAlchemy", "Database", "Python"],
  },
  {
    title: "API Contract Review Checklist",
    slug: "api-contract-review-checklist",
    description: "Review schema examples, response stability, errors, and pagination contracts.",
    content: "Check explicit schema examples, stable error naming, cursor behavior for scroll surfaces, and endpoint descriptions.",
    type: "CHECKLIST",
    version: "1.2.0",
    author: "Grand Archive Council",
    categorySlug: "system-design",
    tags: ["API", "Review", "Design"],
  },
];

export async function ensureDatabaseSeeded() {
  const existing = await prisma.skill.count();
  if (existing > 0) return;

  const categoryBySlug = new Map<string, { id: number }>();
  for (const category of categorySeeds) {
    const created = await prisma.category.upsert({
      where: { slug: category.slug },
      update: {},
      create: {
        name: category.name,
        slug: category.slug,
        parentId: category.parentSlug ? categoryBySlug.get(category.parentSlug)?.id : null,
      },
    });
    categoryBySlug.set(category.slug, created);
  }

  const tagByName = new Map<string, { id: number }>();
  for (const skill of skillSeeds) {
    for (const tagName of skill.tags) {
      const tag = await prisma.tag.upsert({
        where: { name: tagName },
        update: {},
        create: { name: tagName },
      });
      tagByName.set(tagName, tag);
    }
  }

  const now = Date.now();
  for (let index = 0; index < skillSeeds.length; index += 1) {
    const seed = skillSeeds[index];
    const skill = await prisma.skill.create({
      data: {
        title: seed.title,
        slug: seed.slug,
        description: seed.description,
        content: seed.content,
        type: seed.type,
        version: seed.version,
        author: seed.author,
        categoryId: categoryBySlug.get(seed.categorySlug)!.id,
        lastAccessedAt: new Date(now - (index + 1) * 3600 * 1000),
        tags: { connect: seed.tags.map((name) => ({ id: tagByName.get(name)!.id })) },
      },
    });

    for (let usageIndex = 0; usageIndex < 3 + index; usageIndex += 1) {
      await prisma.usageHistory.create({
        data: {
          skillId: skill.id,
          accessedAt: new Date(now - (usageIndex + index) * 9 * 3600 * 1000),
          agentName: usageIndex % 2 === 0 ? "Claude 3.5" : "Hermes Librarian",
          accessMethod: usageIndex % 3 === 0 ? "recommendation" : "search",
        },
      });
    }
  }

  await prisma.workflow.createMany({
    data: [
      {
        title: "Backend Rule Compliance Review",
        slug: "backend-rule-compliance-review",
        description: "Check FastAPI code against local engineering rules.",
        content: "Map rule docs, changed files, quality gates, and severity findings.",
        author: "Hermes Librarian",
      },
      {
        title: "Capability Intake Triage",
        slug: "capability-intake-triage",
        description: "Classify incoming knowledge into skill, workflow, or document.",
        content: "Normalize input, assign category, tag domain, and capture usage intent.",
        author: "Archive Curator",
      },
    ],
  });

  await prisma.knowledgeDocument.createMany({
    data: [
      {
        title: "Dependency Injection Boundary Notes",
        slug: "dependency-injection-boundary-notes",
        description: "Notes on root containers, bounded contexts, and async-safe wiring.",
        content: "Root owns shared resources; bounded contexts compose local use cases.",
        categoryId: categoryBySlug.get("fastapi")!.id,
      },
      {
        title: "Operational Pagination Policy",
        slug: "operational-pagination-policy",
        description: "When to use limit/offset, cursor pagination, and infinite scroll.",
        content: "Use cursor pagination for changing scrollable lists; offset for small admin views.",
        categoryId: categoryBySlug.get("system-design")!.id,
      },
    ],
  });

  await prisma.recommendation.createMany({
    data: [
      {
        title: "Review FastAPI DI before adding routers",
        description: "Most agent failures come from unclear dependency boundaries and request-session ownership.",
        type: "SKILL",
        usageCount: 128,
      },
      {
        title: "Normalize FTS query input",
        description: "Prevent operator syntax from surfacing as 500s in library search.",
        type: "KNOWLEDGE",
        usageCount: 91,
      },
      {
        title: "Use cursor pagination for scroll-heavy archives",
        description: "Preserves stable exploration as the archive grows and changes.",
        type: "POLICY",
        usageCount: 72,
      },
    ],
  });
}
