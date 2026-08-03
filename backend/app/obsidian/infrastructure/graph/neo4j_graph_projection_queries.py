"""Parameterized Cypher for the optional Obsidian graph projection."""

from typing import Final

CREATE_NOTE_KEY_CONSTRAINT: Final[str] = """
CREATE CONSTRAINT obsidian_graph_note_projection_key IF NOT EXISTS
FOR (note:ObsidianGraphNote) REQUIRE note.projection_key IS UNIQUE
"""

CREATE_PROJECTION_NAME_CONSTRAINT: Final[str] = """
CREATE CONSTRAINT obsidian_graph_projection_name IF NOT EXISTS
FOR (projection:ObsidianGraphProjectionState)
REQUIRE projection.projection_name IS UNIQUE
"""

ACTIVATE_PROJECTION_METADATA: Final[str] = """
MERGE (projection:ObsidianGraphProjectionState {
    projection_name: $projection_name
})
WITH projection, projection.run_id AS previous_run_id
SET projection.run_id = $run_id,
    projection.contract_version = $projection_version,
    projection.issue_total = $issue_total,
    projection.issue_counts_json = $issue_counts_json,
    projection.updated_at = datetime()
WITH previous_run_id
MATCH (note:ObsidianGraphNote {projection_name: $projection_name})
WHERE previous_run_id IS NOT NULL
  AND previous_run_id <> $run_id
  AND note.projection_run_id = previous_run_id
DETACH DELETE note
"""

DELETE_PROJECTION_RUN_NODES: Final[str] = """
MATCH (note:ObsidianGraphNote {
    projection_name: $projection_name,
    projection_run_id: $run_id
})
DETACH DELETE note
"""

UPSERT_NODES: Final[str] = """
UNWIND $nodes AS row
MERGE (note:ObsidianGraphNote {projection_key: row.projection_key})
SET note.projection_name = $projection_name,
    note.note_id = row.note_id,
    note.relative_path = row.relative_path,
    note.alexandria_type = row.alexandria_type,
    note.title = row.title,
    note.status = row.status,
    note.project = row.project,
    note.is_placeholder = false,
    note.projection_run_id = $run_id,
    note.projection_version = $projection_version
"""

UPSERT_EDGES: Final[str] = """
UNWIND $edges AS row
MERGE (source:ObsidianGraphNote {projection_key: row.source_key})
ON CREATE SET source.projection_name = $projection_name,
              source.note_id = row.source_note_id,
              source.relative_path = row.source_path,
              source.is_placeholder = true,
              source.projection_run_id = $run_id,
              source.projection_version = $projection_version
MERGE (target:ObsidianGraphNote {projection_key: row.target_key})
ON CREATE SET target.projection_name = $projection_name,
              target.note_id = row.target_note_id,
              target.relative_path = row.target_path,
              target.is_placeholder = true,
              target.projection_run_id = $run_id,
              target.projection_version = $projection_version
MERGE (source)-[edge:OBSIDIAN_GRAPH_EDGE {edge_id: row.edge_id}]->(target)
SET edge.source_path = row.source_path,
    edge.target_path = row.target_path,
    edge.relation = row.relation,
    edge.confidence = row.confidence,
    edge.source_kind = row.source_kind,
    edge.projection_run_id = $run_id,
    edge.projection_version = $projection_version
"""

READ_NODES: Final[str] = """
MATCH (note:ObsidianGraphNote {
    projection_name: $projection_name,
    projection_run_id: $run_id
})
WHERE note.is_placeholder = false
RETURN note.note_id AS note_id,
       note.relative_path AS relative_path,
       note.alexandria_type AS alexandria_type,
       note.title AS title,
       note.status AS status,
       note.project AS project
ORDER BY note.note_id
"""

READ_EDGES: Final[str] = """
MATCH (source:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: $run_id
      })
      -[edge:OBSIDIAN_GRAPH_EDGE]->
      (target:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: $run_id
      })
RETURN edge.edge_id AS edge_id,
       source.note_id AS source_note_id,
       edge.source_path AS source_path,
       target.note_id AS target_note_id,
       edge.target_path AS target_path,
       edge.relation AS relation,
       edge.confidence AS confidence,
       edge.source_kind AS source_kind
ORDER BY edge.edge_id
"""

READ_PROJECTION_METADATA: Final[str] = """
OPTIONAL MATCH (projection:ObsidianGraphProjectionState {
    projection_name: $projection_name
})
RETURN projection.run_id AS run_id,
       projection.contract_version AS projection_version,
       projection.issue_total AS issue_total,
       projection.issue_counts_json AS issue_counts_json
"""

READ_RELATED_NOTES: Final[str] = """
MATCH (projection:ObsidianGraphProjectionState {projection_name: $projection_name})
WITH projection.run_id AS run_id
MATCH (source:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: run_id,
          note_id: $note_id
      })-[edge:OBSIDIAN_GRAPH_EDGE]-(related:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: run_id
      })
WHERE related.is_placeholder = false
WITH related, edge,
     CASE WHEN startNode(edge) = source THEN 'outgoing' ELSE 'incoming' END AS direction,
     CASE edge.relation
       WHEN 'derived_from' THEN 1.0
       WHEN 'cites' THEN 0.9
       WHEN 'supersedes' THEN 0.8
       WHEN 'promotes_to' THEN 0.8
       WHEN 'duplicates' THEN 0.8
       WHEN 'supports' THEN 0.7
       WHEN 'extends' THEN 0.7
       WHEN 'related' THEN 0.6
       WHEN 'wikilink' THEN 0.5
       ELSE 0.4
     END + edge.confidence AS score
ORDER BY score DESC, edge.edge_id
WITH related, collect({edge: edge, direction: direction, score: score})[0] AS best
RETURN related.note_id AS related_note_id,
       best.edge.edge_id AS edge_id,
       best.edge.relation AS relation,
       best.edge.source_kind AS source_kind,
       best.direction AS direction,
       best.score AS score
ORDER BY score DESC, edge_id, related_note_id
LIMIT $limit
"""

READ_CONTEXT_EVIDENCE: Final[str] = """
MATCH (projection:ObsidianGraphProjectionState {projection_name: $projection_name})
WITH projection.run_id AS run_id
MATCH (source:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: run_id
      })-[edge:OBSIDIAN_GRAPH_EDGE]->(target:ObsidianGraphNote {
          projection_name: $projection_name,
          projection_run_id: run_id
      })
WHERE source.note_id IN $note_ids
  AND target.note_id IN $note_ids
  AND source.is_placeholder = false
  AND target.is_placeholder = false
RETURN edge.edge_id AS edge_id,
       source.note_id AS source_note_id,
       target.note_id AS target_note_id,
       target.title AS target_title,
       CASE
         WHEN edge.relation = 'duplicates' THEN 'duplicate_candidate'
         WHEN edge.relation = 'supersedes' THEN 'supersedes_candidate'
         WHEN edge.relation IN ['blocks', 'resolves', 'contradicts']
           THEN 'impact_analysis'
         WHEN edge.relation IN ['derived_from', 'promotes_to', 'supports', 'extends']
           THEN 'lineage'
         WHEN target.alexandria_type IN [
           'memory_compact',
           'job_plan',
           'implementation_history'
         ] THEN 'resume_path'
         ELSE 'graph_proximity'
       END AS signal,
       edge.relation AS relation
ORDER BY edge.edge_id
"""
