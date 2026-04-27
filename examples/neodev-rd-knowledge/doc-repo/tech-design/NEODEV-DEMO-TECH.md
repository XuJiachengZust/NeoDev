---
doc_id: NEODEV-DEMO-TECH-001
title: NeoDev Demo Technical Design
aliases:
  - NeoDev Demo Technical Design
tags:
  - neodev/docs
  - neodev/tech-design
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV-DEMO
product_code: NEODEV-DEMO
version_name: V1.0
status: active
relations:
  target:
    - NEODEV-DEMO-PRD-001
related:
  - "[[NEODEV-DEMO-V1]]"
component: demo-service
---

# NeoDev Demo Technical Design

The sample implementation lives in `project-repo/src/demo_service.py`.

## Design

The service keeps the behavior deliberately small so DocChange registration, graph impact, Git verification, and post-push refresh can be demonstrated without unrelated application code.
