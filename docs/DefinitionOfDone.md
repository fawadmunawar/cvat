# Definition of Done

My checklist, written before implementation. Each line is ticked only with evidence beside it.

## Functionality (items 1–5)

- [ ] Endpoint `GET /api/test/tasks/{id}/annotation-count` returns correct counts for the sample task, cross-checked against a direct DB query.
  Evidence: ___
- [ ] Anonymous request is refused. Evidence: ___
- [ ] A second user with no access to the task is refused. Evidence: ___
- [ ] Page at `/tasks/{id}/annotation-counts` renders the graph with correct numbers for the sample task. Evidence: ___
- [ ] Empty state shown for a task with no annotations. Evidence: ___
- [ ] Error state shown when the request fails, with a working retry. Evidence: ___

## Objective (item 6)

- [ ] MO-1 measured: 5 runs, raw output pasted into `docs/Objectives.md`, median and spread reported.
- [ ] Target met, or missed with the reason written down. Evidence: ___

## Beyond the plain count (item 7)

- [ ] Extra grouping (by shape type) implemented and the reason for choosing it written in the docs. Evidence: ___

## Live updates (items 8–9)

- [ ] Graph updates over WebSocket when annotations change, without reloading the page. Evidence: ___
- [ ] Page recovers automatically when the WebSocket connection drops and comes back. Evidence: ___

## Process

- [ ] Decision record appended to `docs/Plan.md` (approach taken, approach rejected, cost of rejecting it).
- [ ] Commits are incremental, messages explain what and why; first commit holds docs, not finished code.
- [ ] Everything not finished is listed. Evidence: ___
- [ ] PR opened from `dev-test01` into the main branch of my own fork, not the upstream repository.
- [ ] Loom recording (≤ 5 min) submitted with the PR link.
