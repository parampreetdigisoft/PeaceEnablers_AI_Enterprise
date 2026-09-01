# Phase 2 — Knowledge Graph (Neo4j)

Not implemented in Phase 1.

This folder will own:

- Country / pillar / actor / event nodes and relationship types
- Ingestion from SQL Server analytical results into the graph
- Multi-hop traversal used by cross-pillar and executive queries
- Human-override nodes (enterprise PDF §12)
- Graph-path IDs returned on every AI output for audit traceability (PDF §7)

Connection code already has a stub at `app/database/graph.py`. Do not import neo4j from services until this phase.

Related future NFRs from the enterprise requirements PDF: P95 < 5s for cross-pillar graph traversal; reconstructible graph traversal paths on every output.
