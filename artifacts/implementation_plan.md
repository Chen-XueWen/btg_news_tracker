# implementation_plan.md

## Document Purpose
This document converts the architecture for **Breaking News Tracker (BNT)** into a phased delivery and operationalization plan. The sequencing is intentionally quality-first: the program should prove signal quality and operator control before expanding channels or domains.

## Delivery Principles
1. **Ship a narrow but credible end-to-end loop first.**
2. **Validate alert quality before broadening scope.**
3. **Preserve architectural seams even when MVP infrastructure is lightweight.**
4. **Operational readiness is part of MVP, not a post-launch cleanup task.**

## Workstreams
### WS-1 Product and Topic Definition
Define the quantum Topic Profile, approval criteria, success metrics, and pilot review workflow.

### WS-2 Source Onboarding
Stand up the Source Registry and implement approved Source Adapters.

### WS-3 Core Intelligence Pipeline
Implement normalization, deduplication, relevance scoring, summarization, and Alert Record persistence.

### WS-4 Delivery and Routing
Implement one production Delivery Connector, routing logic, retry behavior, and channel-safe alert templates.

### WS-5 Operations and Quality
Implement telemetry, dashboards, runbooks, replay support, and pilot review loops.

## Roles and Ownership
- **Program lead / product owner:** decision-making on scope, quality bar, and acceptance.
- **Domain SMEs:** definition and review of the Topic Profile.
- **Engineering lead:** architecture integrity, implementation sequencing, and technical risk.
- **Operator / analyst reviewers:** pilot feedback on usefulness, noise, and misses.
- **Security / compliance reviewers:** approval for channel integrations, crawling, and retention where needed.

## Phase Plan

### Phase 0 — Alignment and Control Design
**Objective**  
Lock the decision frame before implementation begins.

**Activities**
- confirm approval or provisional acceptance of the value proposition
- nominate primary delivery channel
- finalize pilot source list
- define initial quantum Topic Profile
- define review labels for “useful,” “noisy,” and “missed”
- confirm compliance posture for any crawling targets

**Exit Criteria**
- approved pilot source list
- nominated channel owner and integration path
- initial Topic Profile documented
- pilot KPIs and review workflow agreed
- compliance disposition recorded for all non-feed acquisition methods

### Phase 1 — MVP End-to-End Pipeline
**Objective**  
Deliver a functioning pipeline from source ingestion to one-channel alerting.

**Activities**
- implement Source Registry
- build first Source Adapters
- define canonical Content Item schema
- implement normalization and deduplication
- implement baseline Relevance Policy
- generate concise summaries
- persist Alert Records
- ship one Delivery Connector
- stand up logs, metrics, and retry handling

**Exit Criteria**
- approved pilot sources ingest on schedule
- alertable items reach the MVP channel end to end
- failed deliveries are visible and replayable
- operators can tune at least thresholds and source status without code edits
- provenance is retained for every delivered alert

### Phase 2 — Quality Tuning and Operational Hardening
**Objective**  
Increase trust and stability before expanding outward.

**Activities**
- refine Topic Profile thresholds using pilot review data
- tune false-positive / false-negative balance
- improve rationale tags and channel formatting
- add source freshness monitoring
- harden retry / replay and dead-letter behavior
- create runbooks for source drift and connector failure

**Exit Criteria**
- high-priority alert precision meets agreed pilot target
- source and connector failures are detectable within agreed operating windows
- runbooks exist for the top failure modes
- operators can classify noisy and missed alerts consistently

### Phase 3 — Controlled Expansion
**Objective**  
Add breadth only after quality is credible.

**Activities**
- add second and third approved sources or source families
- add additional Delivery Connectors
- introduce digest generation from Alert Records
- improve clustering for multi-source events
- refine route policies by category and urgency

**Exit Criteria**
- two or more connectors operate through the common interface
- digest output can be produced from persisted alerts
- multi-source event handling reduces duplicate user experience
- source onboarding follows the governance workflow

### Phase 4 — Platformization and Domain Reuse
**Objective**  
Convert the pilot system into a reusable monitoring platform.

**Activities**
- onboard a second Topic Profile
- improve Operator Console ergonomics
- add analytics dashboards
- add structured feedback loops for threshold tuning
- package reusable source / domain onboarding patterns

**Exit Criteria**
- second domain is supported without core redesign
- operator workflow is efficient enough for routine administration
- analytics support quality review and sponsor reporting

## Priority Backlog

### Priority 1
- Source Registry
- approved pilot Source Adapters
- Content Item schema
- deduplication
- baseline Topic Profile
- Relevance Policy
- summary generation
- one Delivery Connector
- Alert Store
- telemetry and retry support

### Priority 2
- threshold tuning workflow
- rationale tag improvements
- replay tooling
- digest generation
- second connector
- source freshness dashboards

### Priority 3
- operator console UI
- analytics dashboard
- second Topic Profile
- advanced clustering and trend detection

## Dependency Map
- Phase 1 depends on Phase 0 decisions.
- Delivery Connector work depends on channel approval and credentials.
- Semantic scoring depth depends on availability of model tooling and cost guardrails.
- Digest mode depends on Alert Record persistence being correct and queryable.
- Multi-domain support depends on Topic Profile abstraction being implemented cleanly in Phase 1, not retrofitted later.

## Test and Validation Strategy

### Functional Validation
- acquisition success by source
- schema validation of Content Items
- deduplication and clustering behavior
- delivery payload correctness by channel

### Intelligence Validation
- precision / recall review against curated pilot samples
- review of rationale tags and confidence signals
- summary usefulness and factual grounding checks

### Resilience Validation
- source outage simulation
- parser drift simulation
- connector timeout / rate-limit simulation
- replay and recovery verification

### Operational Validation
- dashboard usefulness
- runbook dry-runs
- operator ability to suspend a source, tune a threshold, and replay a failure

## Deployment Approach
- containerized services or workers
- environment-separated configuration
- managed secrets
- scheduled acquisition plus queue-backed processing
- staged promotion from dev to test to production
- feature flags for risky source adapters or new connectors

## Monitoring and Feedback Loop
### Core Metrics
- publication-to-alert latency
- ingestion success rate
- normalization error rate
- duplicate suppression rate
- relevance pass / suppress distribution
- delivery success rate
- replay volume
- source freshness gap

### Human Feedback Signals
- useful alert
- noisy / low-value alert
- missed important item
- summary unclear
- wrong routing or wrong urgency

The feedback loop should be reviewed on a regular cadence during pilot and translated into Topic Profile and threshold updates.

## Risk Register and Mitigation Actions

### Risk: Alert Fatigue
**Mitigation**
- conservative initial thresholds
- explicit review loop
- restrict MVP source set to trusted publishers and feeds

### Risk: Missing Important Signals
**Mitigation**
- use curated pilot review samples
- inspect suppressed items during tuning
- add semantic methods after deterministic baseline is stable

### Risk: Parser Instability
**Mitigation**
- adapter isolation
- source health monitoring
- Source Registry suspension control

### Risk: Delivery Constraints by Channel
**Mitigation**
- start with one channel
- normalize alert payloads before rendering
- implement channel-specific formatting and fallback rules

### Risk: Architecture Becomes Hard to Extend
**Mitigation**
- preserve Topic Profile, Source Registry, and Delivery Connector abstractions in MVP
- avoid channel-specific rules in upstream services
- avoid source-specific logic in the Relevance Engine

## Definition of Done for MVP
The MVP is complete when:
- approved pilot sources are ingested reliably,
- relevant quantum items are summarized and delivered to the nominated channel,
- duplicates are controlled,
- provenance and delivery status are persisted,
- operators can manage essential controls,
- pilot reviewers judge the alerts useful enough to continue into expanded rollout.

## Immediate Next Decisions Required
1. approve the pilot source list
2. select the MVP delivery channel
3. nominate domain reviewers for the quantum Topic Profile
4. confirm whether any pilot sources require controlled crawling
5. agree on the target precision threshold for high-priority alerts
