# Objectives

One measurable objective, in the required format. Two people running this method on the same
machine would agree on whether it was met.

## MO-1 — Latency of the per-class annotation count endpoint

| Field | Entry |
|-------|-------|
| What is measured | Time from sending the request to receiving the full response for `GET /api/test/tasks/{task_id}/annotation-count` on the sample task (1000 COCO val2017 images, annotations imported). |
| How | `curl` against `http://localhost:8080` from the host, 5 consecutive requests, session cookie of the task owner; `time_total` recorded from curl's own output. Raw output pasted below. |
| Target | Median of 5 runs at or below **150 ms**. |
| Conditions | Windows 11 Pro host, AMD Ryzen 5 4500U (6 cores), 16 GB RAM; local Docker stack on drive D:; nothing else running against the stack; task `{sample_task_id}`; server warm (one untimed request first). |
| Not included | First request after a cold start, video tasks, the page load time (frontend), WebSocket latency. |

### Why 150 ms

The endpoint performs one aggregate SQL query over a few thousand rows plus one OPA authorization
round-trip (localhost) and DRF serialization. On this stack that is expected to complete in well
under 100 ms. A target of 150 ms is therefore achievable without gaming (no caching, no
precomputation) but still meaningful: any regression to a per-shape query or an unindexed join
would blow well past it. The point is to prove the read path is a single fast query.

### Raw measurement (5 runs)

```
<pasted raw curl -w output here>
```

Median: `TBD ms` · Spread (min–max): `TBD ms` · Target met / missed + reason: `TBD`

### Machine and build

- OS: Windows 11 Pro
- CPU: AMD Ryzen 5 4500U with Radeon Graphics, 6 cores
- RAM: 16 GB (15.3 GB visible)
- CVAT commit: `b36a49bd5cc7e5fe3fc36ecb6036659c8136b780`
- Docker Desktop: 4.97.0, WSL2 backend
