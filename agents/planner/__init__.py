"""Caged planner agent. For each VIOLATION finding, drafts a
RemediationProposal (offending text -> proposed compliant text + rule
ref). Emits proposals only -- never writes, edits, or publishes; never
approves its own proposal.

Tool whitelist (SPEC.md Agent boundaries): read_finding, read_rule, emit_proposal.
May never fetch pages, write files, or approve its own proposal.

Implemented Phase 5, alongside the human-gate CLI (SPEC.md Phase discipline).
"""
