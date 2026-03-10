# solution.md

## Document Purpose
This document describes how **Breaking News Tracker (BNT)** realizes the requirements in `requirements.md` through a modular, event-driven architecture. It emphasizes traceability, extensibility, and operational control rather than a one-off alert bot implementation.

## Architecture Goals
The solution must simultaneously achieve five goals:

1. **Timely discovery** of relevant quantum developments.
2. **Low-noise alerting** through explainable relevance controls.
3. **Operational resilience** despite source and channel variability.
4. **Configuration-driven extensibility** for new sources, channels, and Topic Profiles.
5. **Governable behavior** across acquisition, retention, delivery, and operator workflows.

## AI Guidance and Context
The AI-enabled components in this architecture are not intended to replace product or analyst judgment. They are used in bounded ways:

- to improve semantic recall beyond static keywords,
- to generate concise summaries,
- to provide richer rationale for alert decisions,
- to reduce manual triage effort during pilot.

Every AI-assisted decision is therefore paired with deterministic metadata, provenance, or threshold controls so the system remains reviewable.

## Logical Architecture Overview
BNT is composed of the following logical services:

1. **Source Registry Service**
2. **Acquisition Workers**
3. **Normalization and Enrichment Service**
4. **Deduplication and Clustering Service**
5. **Relevance Engine**
6. **Summarization Service**
7. **Alert Orchestrator**
8. **Delivery Connectors**
9. **Alert Store**
10. **Operator Console / Configuration Layer**
11. **Observability and Runbook Layer**

These services may be deployed as modular workers behind queues, or as a smaller set of services in an MVP environment, provided the logical boundaries remain intact.

## Canonical Data Objects

### 1. Source Registry Entry
Captures source governance and runtime control:
- source identifier
- source category
- acquisition method
- polling cadence
- parser version
- trust classification
- compliance notes
- operational state
- last successful fetch

### 2. Content Item
The normalized representation of a single external publication:
- source identifier
- source item identifier when available
- title
- canonical URL
- publication timestamp
- acquisition timestamp
- publisher / author metadata
- abstract / snippet / extracted text
- source category
- raw metadata reference
- Topic Profile candidate list

### 3. Alert Candidate
A Content Item after normalization and deduplication, enriched with:
- similarity references / cluster ID
- relevance scores
- confidence
- category labels
- rationale tags
- urgency
- suppression or route recommendation

### 4. Alert Record
The persisted operational record:
- Alert Candidate payload
- summary text
- routing outcome
- delivery status history
- retry history
- operator actions
- audit timestamps

## Component Design

### 1. Source Registry Service
**Purpose**  
Implements FR-01 and OR-01 by centralizing approved source metadata and compliance information.

**Responsibilities**
- maintain approved sources and schedules
- record acquisition method and parser assignment
- preserve trust classification and compliance notes
- enable rapid source suspension when a source fails or becomes non-compliant

**Architectural Decision**  
This must be externalized from application code. Hard-coding source behavior would directly undermine extensibility and operator control.

### 2. Acquisition Workers
**Purpose**  
Implements FR-02 and FR-03.

**Acquisition Strategy Order**
1. API
2. RSS / Atom
3. structured site metadata
4. controlled crawling for approved sites only

**Responsibilities**
- fetch new items on schedule
- perform basic freshness filtering
- validate source reachability
- enforce politeness, rate limiting, and backoff
- emit raw payloads plus acquisition metadata

**Deep-Dive Consideration**  
Crawling should be isolated from business logic. Parser drift and legal review are materially different concerns from relevance scoring, so acquisition adapters should fail independently without blocking the rest of the system.

### 3. Normalization and Enrichment Service
**Purpose**  
Implements FR-04 and supports NFR-11.

**Responsibilities**
- transform heterogeneous source payloads into the canonical Content Item schema
- reconcile timestamps and canonical URLs
- apply source-specific cleanup rules
- attach preliminary source category and domain hints

**Design Note**  
Normalization is where many hidden failures occur. Bad timestamp normalization or poor canonical URL extraction will degrade deduplication, freshness, and trust. This service therefore deserves explicit validation and schema checks rather than being treated as simple parsing glue.

### 4. Deduplication and Clustering Service
**Purpose**  
Implements FR-05.

**Deduplication Strategy**
- exact match on source item IDs where available
- canonical URL normalization
- title normalization
- semantic similarity checks for near duplicates
- optional cluster ID for multi-source coverage of the same event

**Why This Matters**  
For news-style sources, duplicate suppression is not enough. BTG may benefit from seeing that several credible sources are discussing the same event, but not from receiving three nearly identical alerts. Clustering supports this distinction.

### 5. Topic Profile and Relevance Engine
**Purpose**  
Implements FR-06 and FR-07.

**Topic Profile Contents**
- mandatory keywords and named entities
- exclusions and negative indicators
- concept exemplars / embedding references
- category taxonomy
- threshold rules
- route mappings
- optional human-review conditions

**Relevance Evaluation Pipeline**
1. deterministic pre-filtering
2. semantic classification
3. source trust weighting
4. novelty / urgency evaluation
5. final score composition
6. threshold / routing decision

**Why Use a Hybrid Model**
- deterministic rules provide precision and explainability
- semantic scoring reduces false negatives for conceptually relevant but lexically diverse items
- source-trust weighting avoids treating all sources as equal
- a single-model black box would be harder to tune during pilot

**Example Decision Factors**
- Is the item directly about quantum technologies?
- Is it a paper, commercial signal, policy change, partnership, regulatory event, funding announcement, or technical breakthrough?
- Does it mention entities, technologies, or applications defined in the Topic Profile?
- Is it novel relative to recent alerts?
- Does the source meet the trust threshold for immediate delivery?

### 6. Summarization Service
**Purpose**  
Implements FR-08.

**Output Requirements**
- one concise message suitable for the destination channel
- what happened
- why BTG should care
- source attribution
- link
- rationale tags or short “why surfaced” statement

**Risk Control**
Summary generation must not invent facts. The service should be grounded on extracted source text and structured metadata, with truncation and source citation preserved where applicable.

### 7. Alert Orchestrator
**Purpose**  
Implements FR-09.

**Responsibilities**
- apply threshold rules from the Relevance Policy
- distinguish immediate alerts from suppressed items or future digest candidates
- evaluate route mapping by urgency, category, or source class
- apply optional human-review gates for designated conditions
- hand off to Delivery Connectors with channel-safe payloads

**Important Design Choice**
The Orchestrator should own routing policy, not the Delivery Connectors. This prevents each connector from accumulating divergent business rules.

### 8. Delivery Connectors
**Purpose**  
Implements FR-10.

**Connector Contract**
Each connector should:
- accept a normalized alert payload
- render channel-specific formatting
- respect rate limits and delivery constraints
- return structured delivery outcomes
- support retry semantics and dead-letter behavior

**Connector Strategy**
MVP should ship with one primary connector. Additional connectors can then be added behind the same interface without reworking scoring or routing logic.

### 9. Alert Store
**Purpose**  
Implements FR-11, FR-12, and FR-16.

**Responsibilities**
- persist Alert Records
- support replay and audit review
- retain pipeline timestamps and delivery history
- provide input for digest generation and analytics
- preserve provenance for later tuning and incident review

### 10. Operator Console / Configuration Layer
**Purpose**  
Implements FR-13 and supports OR-02 through OR-05.

**Minimum MVP Form**
The console may begin as a configuration-backed administrative surface plus dashboards and runbooks rather than a full UI.

**Core Controls**
- source enable / disable
- parser version or adapter mapping
- Topic Profile editing
- threshold tuning
- route changes
- replay actions
- visibility into failures and freshness

### 11. Observability and Runbook Layer
**Purpose**  
Implements NFR-06 and supports operational readiness.

**Required Telemetry**
- source fetch success / failure
- time since last successful source acquisition
- normalization errors by source
- deduplication hit rate
- relevance pass / suppress distribution
- delivery success and retry rates by channel
- alert latency from publication to delivery

**Why This Layer Matters**
Without observability, teams cannot tell whether silence means “nothing relevant happened” or “the system is broken.”

## Event-Driven Deployment Pattern
The recommended technical pattern is an event-driven pipeline with queues or topics separating acquisition, analysis, and delivery.

### Benefits
- independent scaling of ingestion and analysis workers
- failure isolation between connectors and acquisition
- replay support without re-fetching all source data
- easier insertion of review gates or digest generation later

### MVP Adaptation
If implementation simplicity requires a smaller initial footprint, services may run in fewer deployables as long as:
- the data contracts remain explicit,
- queues or internal job stages remain separable,
- connector logic stays isolated from business rules.

## Security and Compliance Design
### Security Controls
- centralized secret management
- role-based access for operator actions
- environment separation for dev / test / prod
- immutable audit logs for critical operator changes where practical

### Compliance Controls
- record source-specific crawling restrictions in the Source Registry
- prefer metadata, summaries, and links over unnecessary full-text retention
- preserve provenance for every alert
- provide rapid source suspension capability

## Failure Modes and Mitigations
### Source Failure or Parser Drift
Mitigation:
- source health monitoring
- adapter isolation
- rapid source disable / fallback controls

### Delivery Connector Failure
Mitigation:
- retry with backoff
- dead-letter queue or failed-delivery store
- operator replay workflow

### Scoring Drift / Poor Relevance Quality
Mitigation:
- pilot review workflow
- threshold tuning by Topic Profile
- reason-code inspection for false positives and false negatives

### Cost or Latency Growth from AI Services
Mitigation:
- selective invocation rules
- hierarchical scoring pipeline
- cheaper models for first-pass classification
- summary generation only after threshold pass

## Architectural Decisions and Trade-Offs

### ADR-01: RSS/API First, Controlled Crawling Second
Chosen to reduce operational fragility and compliance risk.

### ADR-02: Hybrid Rules + Semantic Relevance
Chosen to balance explainability, precision, and recall.

### ADR-03: Connector-Based Delivery
Chosen to separate channel-specific behavior from business policy.

### ADR-04: Topic Profiles as First-Class Configuration
Chosen to make domain expansion operationally tractable.

### ADR-05: Persist Alert Records, Not Just Outbound Messages
Chosen so the platform can support replay, digests, audits, analytics, and threshold tuning.

## MVP Technical Slice
The MVP implementation should include:
- Source Registry
- small set of approved Source Adapters
- canonical Content Item schema
- deduplication and basic clustering
- one active Topic Profile for quantum technologies
- hybrid relevance scoring
- summary generation
- one production Delivery Connector
- Alert Store
- core telemetry and replay support

## Traceability Matrix
### Requirements to Components
- **FR-01 to FR-03:** Source Registry Service + Acquisition Workers
- **FR-04:** Normalization and Enrichment Service
- **FR-05:** Deduplication and Clustering Service
- **FR-06 to FR-07:** Topic Profile and Relevance Engine
- **FR-08:** Summarization Service
- **FR-09:** Alert Orchestrator
- **FR-10:** Delivery Connectors
- **FR-11 to FR-12 and FR-16:** Alert Store + replay workflow
- **FR-13:** Operator Console / Configuration Layer
- **FR-14:** Alert Store + scheduled orchestration
- **FR-15:** Topic Profile abstraction + Source Registry design
- **NFR-01 to NFR-12:** realized through queue-based decoupling, observability, compliance metadata, secret management, and bounded AI invocation

## Extensibility Model
The system is considered genuinely extensible only if three kinds of change are low-friction:

1. **New source:** add or configure a Source Registry entry and, if needed, a Source Adapter.
2. **New channel:** add a Delivery Connector that implements the existing connector contract.
3. **New domain:** define a Topic Profile, thresholds, and route mappings without re-architecting the pipeline.

That is the design standard against which future changes should be judged.
