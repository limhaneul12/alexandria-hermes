# Alexandria Operating Loop

Use Alexandria only when it improves grounding or durable capability reuse.

1. Use the current conversation, local files, loaded skills, and relevant project context first.
2. For durable memory gaps, use the current Memory Compact and canonical `alexandria_search` retrieval boundary.
3. For reusable capability gaps, call `alexandria_search_skills` before creating anything.
4. If a matching skill is sufficient, load and use it.
5. If the skill is missing or insufficient, call `alexandria_start_skill_acquisition` with the search snapshot and current task goal.
6. Poll `alexandria_skill_acquisition_job_status` and resume the blocked task only from a verified handoff.
7. Do not choose Librarian providers, profiles, OAuth credentials, or manual completion routes from the requesting-agent surface.
8. Use Alexandria Core vault tools for search/read/write/graph/curation. Do not route ordinary vault maintenance through Librarian.
9. Memory reconciliation and periodic compaction belong to Memory Steward, not Librarian.

Never store secrets. Do not invent evidence or activate an insufficiently verified skill.
