# Plan — Annotation Analytics (xis.ai Full Stack Assessment)

**Baseline.** Forked CVAT at commit `b36a49bd5cc7e5fe3fc36ecb6036659c8136b780` (v2.81.0 development branch).
Machine: Windows 11 Pro, AMD Ryzen 5 4500U (6 cores), 16 GB RAM, Docker Desktop 4.97 with WSL2,
stack and data on drive D: (C: has insufficient free space).

**Goal.** Add per-class annotation counts to CVAT: an API endpoint that reads counts from the database,
a page in the web UI that shows them as a graph, live updates over WebSocket, and one measured
performance objective. Work happens in a new Django app `test`, committed to branch `dev-test01`.

**Dataset.** COCO 2017 validation set, first **1000 images** of `val2017.zip` with annotations imported
from `instances_val2017.json` (COCO 1.0). 1000 keeps image import, DB size and RAM comfortable on
this machine while still being the public dataset everyone uses. Exact frame count is recorded in
Definition of Done.

## Order of work and time estimates (out of 8 hours)

| # | Part | Est. |
|---|------|------|
| 1 | Environment + COCO import (images download/import run in background, excluded from the 8h per the brief) | 0:30 |
| 2 | Explore CVAT codebase: models (`engine/models.py`), IAM permissions (`iam/permissions.py`, `engine/permissions.py`), routing, UI structure | 0:45 |
| 3 | This Plan, Objectives, Definition of Done — committed before any code | 0:30 |
| 4 | Endpoint `GET /api/test/tasks/{task_id}/annotation-count` + auth (items 1, 5) | 1:15 |
| 5 | Page + graph + empty/error states (items 2–4) | 1:00 |
| 6 | Measure MO-1 (5 runs, raw output) (item 6) | 0:20 |
| 7 | Extra grouping by shape type (item 7) | 0:25 |
| 8 | WebSocket live updates + reconnect (items 8, 9) | 1:15 |
| 9 | Decision record (item 10) | 0:15 |
| 10 | Definition of Done evidence, final commits, PR | 0:30 |
| — | Buffer | 0:45 |
| 11 | Loom recording (5 min) | 0:10 |

## Technical approach

**Endpoint.** A DRF viewset in `cvat/apps/test` (no new database tables). The count is a single
aggregate query: `LabeledShape` and `LabeledTrack` grouped by `label__name`, filtered by
`job__segment__task_id`. The label of a shape lives on `Annotation.label` (FK to `Label`, field `name`);
the path from a task is Task → Segment → Job → shape. Reusing `TaskPermission` (`scope "view"`)
plus CVAT's default authentication gives us: anonymous → 401, user without task access → 403,
owner → counts. This satisfies items 1 and 5 with CVAT's own machinery rather than a hand-rolled check.

**Page.** New route `/tasks/:tid/annotation-counts` in `cvat-ui`, a menu entry in the task Actions menu,
bar chart with `chart.js`/`react-chartjs-2` (already a declared dependency, currently unused — no new
packages). Empty state for a task with no annotations, error state with retry for a failed request.

**Live updates.** A small WebSocket service (same `cvat/server` image, `websockets` library already in
the image requirements) listening on a published port; Django publishes a "task N annotations changed"
message to Redis pub/sub from a `post_save(Job)` signal (CVAT touches the job's `updated_date` after
every annotation save — verified in `dataset_manager/task.py::_set_updated_date`). The page re-fetches
counts over the authenticated HTTP API whenever it receives a message for its task, and reconnects
with exponential backoff when the socket drops. No annotation data travels over the socket itself.

## Already decided to skip

- MQTT-based delivery (no broker in the default stack) — see decision record at the end.
- Video track shape-per-frame counting: a track is counted as one annotation instance (the sample
  dataset is images, where this question does not arise).
- Skeleton/sublabel special-casing (COCO has no skeletons).

## Decision record (item 10)

_To be appended once item 8 is done._
