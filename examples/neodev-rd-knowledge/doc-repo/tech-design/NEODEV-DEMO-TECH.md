---
doc_id: NEODEV-DEMO-TECH-001
title: NeoDev Demo Technical Design
doc_type: tech-design
product_code: NEODEV-DEMO
version_name: V1.0
relations:
  - type: supports
    target: NEODEV-DEMO-PRD-001
component: demo-service
---

# NeoDev Demo Technical Design

The sample implementation lives in `project-repo/src/demo_service.py`.

## Design

The service keeps the behavior deliberately small so DocChange registration, graph impact, Git verification, and post-push refresh can be demonstrated without unrelated application code.
