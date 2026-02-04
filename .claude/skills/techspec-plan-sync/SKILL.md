---
name: techspec-plan-sync
description: Report inconsistencies between TechSpec and Plan with exact section pointers; propose minimal patch list without editing files.
---

# Skill: techspec-plan-sync

## Purpose
Find and report inconsistencies between:
- docs/pdf_extractor_techspec_v_2_6.md
- docs/pdf_extractor_plan_v_2_4.md

## Procedure
1) Extract referenced versions, component lists, invariants, and policy links.
2) Compare:
   - pipeline component order
   - stated invariants (e.g., T=L=E)
   - boundary detector contract fields
   - policy document references and versions
3) Output:
   - A concise mismatch list with file+section pointers
   - Suggested minimal patch list (NO edits applied)

## Output rules
- Facts only: cite exact headings/sections
- If file paths differ, ask to confirm the canonical locations by running:
  - ls -la docs/
