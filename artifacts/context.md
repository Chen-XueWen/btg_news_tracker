# context.md

## Document Purpose
This document establishes the operating context for **Breaking News Tracker (BNT)**. It defines the business problem, strategic intent, stakeholders, launch scope, constraints, risks, and measurable success criteria that govern the rest of the package.

## Executive Summary
BTG currently discovers quantum-technology news and papers through informal manual scanning and ad hoc sharing in messaging groups. That operating model is inconsistent, difficult to scale, and structurally weak: important developments can be missed, duplicate stories consume attention, and there is no repeatable mechanism to explain why a given item matters. BNT addresses this by creating a configurable intelligence workflow that continuously ingests trusted sources, normalizes and deduplicates content, evaluates relevance against BTG priorities, and distributes ranked alerts into collaboration channels.

## Problem Statement
BTG needs to automate the discovery of breaking news and research developments in **quantum technologies**. The system must monitor trusted scientific and technology sources, assess relevance to BTG’s interests, and notify the right audiences through collaboration platforms with low noise and clear rationale. The design must also make it straightforward to extend into additional domains of interest without rewriting core platform logic.

## Strategic Objective
Build a reusable monitoring and alerting platform that improves BTG’s speed of awareness while increasing trust in the signal quality of internal alerts.

This objective has four parts:

1. **Discovery:** continuously ingest content from approved sources.
2. **Interpretation:** distinguish high-value items from ambient information noise.
3. **Distribution:** route alerts to the correct channels in the correct format.
4. **Extensibility:** onboard new sources and new domains through configuration-first controls.

## Business Outcomes Sought
- Reduce manual scanning effort by analysts and staff.
- Increase the probability that material quantum developments are surfaced quickly.
- Create a defensible relevance model rather than relying on individual judgment alone.
- Establish an operating pattern that can later support adjacent domains such as semiconductors, AI hardware, biotech, cyber, or energy.

## Stakeholders
### Primary Stakeholders
- **BTG leadership:** accountable for strategic value, sponsorship, and acceptance of alert quality.
- **Analysts and researchers:** primary consumers of alerts and the main source of early feedback on relevance.
- **Engineering / platform team:** responsible for implementation, security, deployment, and maintainability.
- **Program / operations owners:** responsible for source governance, threshold tuning, and day-to-day reliability.

### Secondary Stakeholders
- **Channel owners / workspace administrators:** responsible for approving and managing platform integrations.
- **Compliance / legal reviewers:** consulted when controlled crawling, content storage, or external platform use raises policy questions.
- **Future domain sponsors:** stakeholders who may later request onboarding of other topic domains.

## Primary User Personas
### 1. Research Analyst
Needs timely alerts on papers, breakthroughs, commercialization signals, regulatory shifts, funding events, and lab announcements. Values precision, source credibility, and “why it matters” context.

### 2. Decision-Maker / Sponsor
Needs concise summaries with confidence indicators, relevance rationale, and evidence that major developments are not being missed.

### 3. Platform Operator
Needs to add or suspend sources, tune thresholds, observe pipeline health, inspect delivery failures, and manage Topic Profiles without invasive code changes.

## Launch Domain
### In Scope for Phase 1
**Quantum technologies**, including:
- quantum computing
- quantum communications
- quantum sensing
- quantum hardware components
- enabling materials, tooling, and commercial ecosystem signals where clearly relevant

### Potential Adjacent Domains for Later Expansion
- semiconductors
- AI infrastructure and hardware
- advanced materials
- cybersecurity
- energy technologies
- biotech / life sciences

## Source Landscape
### Preferred Source Categories
1. **Preprint and paper repositories**
   - arXiv
   - journal feeds where access and metadata are available

2. **Scientific publishers and journals**
   - Nature and related publications
   - other approved peer-reviewed sources

3. **Technology and science journalism**
   - MIT Technology Review
   - other approved high-credibility science and industry outlets

4. **Institutional / ecosystem signals**
   - national labs
   - university announcements
   - company research blogs
   - funding or regulatory announcements where clearly relevant

### Source Access Priority
1. API
2. RSS / Atom feed
3. site search or structured metadata feed
4. controlled crawling when explicitly permitted and operationally justified

## Notification Landscape
### Supported Delivery Targets
- Slack
- Telegram
- Discord
- WhatsApp
- future collaboration or incident-style channels through the Delivery Connector model

### MVP Delivery Principle
The platform must support multi-channel delivery by design, but **only one primary real-time channel** is required for MVP launch. Additional channels are phased after the core relevance pipeline is stable.

## Operating Assumptions
- BTG prefers **high signal quality** over exhaustive source coverage in the first release.
- BTG can define a first-pass set of quantum relevance criteria, or nominate domain experts to create proxy rules.
- At least one notification platform can be integrated in the pilot environment.
- Some sources provide stable feeds or metadata; not every source requires crawling.
- LLM or semantic models may be used for classification and summarization, subject to cost, compliance, and latency controls.
- Formal legal review may be required for some crawling targets or for storing extracted content beyond metadata and summaries.

## Constraints
### Product Constraints
- Alert fatigue is a critical failure mode.
- Explanation quality matters; users must understand why a story was sent.
- Manual review cannot be required for every alert if the system is to scale.

### Technical Constraints
- Sources vary in structure, freshness, and availability.
- Not all channels support the same message length, formatting, rate limits, or automation controls.
- The platform must remain maintainable by a small team.

### Compliance and Governance Constraints
- Crawling must respect robots.txt, terms of use, and publisher restrictions.
- Content retention should favor metadata, links, summaries, and traceable provenance over unnecessary storage of copyrighted full text.
- Access tokens and integration secrets must be centrally managed.

## Success Criteria
### Business Success
- BTG identifies relevant developments faster than the current manual process.
- Analysts report lower manual scanning effort and higher trust in alert quality.
- Decision-makers consider the alerts actionable rather than merely informative.

### Product Success
- The system surfaces a meaningful proportion of high-value quantum developments from the approved pilot source set.
- Duplicate or syndicated items are suppressed or clustered so users are not spammed with repeated alerts.
- The alert includes a readable summary, source attribution, and rationale tags.

### Platform Success
- A new approved source can be onboarded with limited code change and clear governance steps.
- A second Topic Profile can be created without redesigning the core pipeline.
- Operators can understand pipeline health, delivery failures, and source freshness from logs and metrics.

## Proposed KPIs
- **Median time from publication to alert**
- **Precision of high-priority alerts** during pilot review
- **Duplicate suppression rate**
- **Source freshness SLA adherence**
- **Delivery success rate by channel**
- **Operator effort to onboard one new source**
- **Operator effort to define one new Topic Profile**

## Risks
### 1. Over-alerting
If thresholds are too permissive, users will mute or distrust the channel.

### 2. Under-alerting
If the model is too conservative, BTG may miss strategically important early signals.

### 3. Source Volatility
Web layouts, feeds, and anti-bot measures can change without warning.

### 4. Compliance Exposure
Improper crawling or content retention may create legal or policy issues.

### 5. Architecture Drift
If domain logic, source parsing, and delivery formatting become tightly coupled, extensibility will degrade.

## Risk Controls Required
- conservative initial thresholds
- Source Registry with compliance metadata
- RSS/API-first acquisition policy
- event-level provenance and explainability
- observability for source health, delivery health, and threshold performance
- phased channel rollout rather than simultaneous connector expansion

## Approval Status
**Context accepted as working baseline; formal business approval still required for launch decisions on sources, channel priority, and policy constraints.**

## Decisions Needed
1. Which notification channel is the MVP launch destination?
2. Which pilot sources are mandatory versus optional?
3. What is the acceptable latency target for “breaking” alerts by source class?
4. Is daily digest mode required in Phase 2 or Phase 3?
5. Under what conditions, if any, should a human-review gate apply before delivery?

## Traceability Notes
This context intentionally drives the following downstream documents:
- `ideation.md` defines the recommended strategic posture: high-relevance, extensible monitoring.
- `requirements.md` converts this into requirement IDs and MVP boundaries.
- `solution.md` realizes those requirements through the Source Registry, Topic Profile, Relevance Policy, and Delivery Connector architecture.
- `implementation_plan.md` phases the work to control alert-quality risk before connector and domain expansion.
