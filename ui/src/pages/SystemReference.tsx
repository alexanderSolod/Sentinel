import { motion } from 'framer-motion';
import Markdown from 'react-markdown';
import Card from '../components/ui/Card.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import MermaidDiagram from '../components/ui/MermaidDiagram.tsx';
import { SCORE_DEFINITIONS } from '../lib/scoreDefinitions.ts';

// ---------------------------------------------------------------------------
// Mermaid chart definitions
// ---------------------------------------------------------------------------

const PIPELINE_CHART = `graph LR
  A[Trade Detection] --> B[OSINT Correlation]
  B --> C[Stage 1: Triage]
  C --> D{BSS >= 40?}
  D -->|Yes| E[Stage 2: Deep Analysis]
  D -->|No| F[Sentinel Index]
  E --> G[Stage 3: SAR Generation]
  G --> F
`;

const FP_GATE_CHART = `graph TD
  A[Anomaly Detected] --> B{Gate 1: Statistical Filter}
  B -->|Pass| C{Gate 2: Random Forest}
  B -->|Fail| H[Cleared]
  C -->|Pass| D{Gate 3: Autoencoder}
  C -->|Fail| H
  D -->|Pass| E{Gate 4: Game Theory}
  D -->|Fail| H
  E -->|Pass| F{Gate 5: Mistral BSS}
  E -->|Fail| H
  F -->|Suspicious| G[Flagged for Review]
  F -->|Not Suspicious| H
`;

const LLM_CHART = `graph TD
  A[Anomaly + OSINT Context] --> B[Stage 1: mistral-small-latest]
  B --> C{Classification + BSS/PES}
  C -->|INSIDER / OSINT_EDGE / BSS>=40| D[Stage 2: mistral-large-latest]
  C -->|FAST_REACTOR / SPECULATOR| G[Sentinel Index]
  D --> E{INSIDER or BSS>=60?}
  E -->|Yes| F[Stage 3: mistral-large-latest]
  E -->|No| G
  F --> G
  H[OSINT Events] --> I[mistral-embed]
  I --> J[ChromaDB Vector Store]
  J -->|RAG Context| D
`;

const DETECTION_CHART = `graph LR
  A[Raw Trades] --> B[Volume Detector]
  A --> C[Price Detector]
  A --> D[Fresh Wallet Detector]
  B --> E[Anomaly Events]
  C --> E
  D --> E
  E --> F[DBSCAN Clustering]
  F --> G[Composite Risk Scorer]
`;

// ---------------------------------------------------------------------------
// LLM Analysis markdown content
// ---------------------------------------------------------------------------

const LLM_CONTENT = `
## Stage 1 — Triage (\`mistral-small-latest\`)

Performs rapid **4-class classification** using a finetuned mistral small model 4 gold-standard examples from real events (including the **Iran Strike** and **Axiom/ZachXBT** cases).

**Input:** The model receives a structured JSON containing:
- Wallet age, trade count, trade size
- Hours before news, OSINT signal count
- Z-score, win rate, cluster membership
- Funding risk, RF suspicion score, game theory score

**Output:** JSON response with classification, BSS score (0–100), PES score (0–100), confidence (0.0–1.0), and reasoning text.

- **Temperature:** 0.1 (near-deterministic)
- **Max tokens:** 500
- When a fine-tuned model is available (via \`SENTINEL_FINETUNED_MODEL\` env var), it is automatically preferred over the base model.
- **Fallback:** When the Mistral API is unavailable, a rule-based classifier provides deterministic heuristic scoring using the same input features.

---

## Stage 2 — Magistral Deep Analysis (\`mistral-large-latest\`)

Only triggered for **INSIDER/OSINT_EDGE** classifications or when **BSS ≥ 40**. Uses chain-of-thought reasoning for deep explainability.

The model receives the full anomaly event data, Stage 1 triage result, and up to **5 OSINT signals** retrieved via RAG from the ChromaDB vector store.

**Output:**
- **XAI Narrative** — detailed, human-readable explanation (powers the AI Analysis panel)
- **Fraud Triangle** — Pressure, Opportunity, Rationalization analysis
- **Temporal Gap Analysis** — timing breakdown between trade and public signals
- **Evidence Summary** — bullet points of key evidence
- **Recommendation** — suggested action

- **Temperature:** 0.3 (moderate reasoning flexibility)
- **Max tokens:** 2,000

---

## Stage 3 — SAR Generation (\`mistral-large-latest\`)

Only triggered for **INSIDER** classification or **BSS ≥ 60**. Generates formal, structured **Suspicious Activity Reports** suitable for regulatory submission.

**Report structure:**
1. Executive Summary (2–3 sentences)
2. Evidence Timeline (chronological bullet points)
3. Fraud Analysis (Fraud Triangle assessment)
4. Classification Rationale
5. Confidence Assessment
6. Recommendations

**Severity** is determined by BSS: **HIGH** (>80), **MEDIUM** (>60), or **LOW**.

- **Temperature:** 0.2 (objective, evidence-based tone)
- **Max tokens:** 3,000

---

## OSINT Embeddings (\`mistral-embed\`)

OSINT events from GDELT, GDACS, ACLED, and NASA FIRMS are embedded using \`mistral-embed\` in **batches of 25** and stored in a **ChromaDB** collection with cosine similarity.

Stage 2 retrieves the **top 5 semantically similar** OSINT events as RAG context for the deep analysis prompt.

**Search modes:**
- General semantic queries
- Market-specific keyword filtering
- Time-windowed retrieval

**Fallback:** ChromaDB's default embedding function (MiniLM) when the Mistral API is unavailable.

---

## Fine-Tuning Pipeline (\`open-mistral-nemo\`)

Generates **500 training examples** with distribution:
- 25% INSIDER
- 25% OSINT_EDGE
- 15% FAST_REACTOR
- 15% SPECULATOR
- 20% Hard/ambiguous cases

Includes **3 gold-standard examples** from real events:
- Iran Strike — Wallet A (INSIDER, BSS: 94, 812% return)
- Iran Strike — Vivaldi007 (OSINT_EDGE, BSS: 12)
- Axiom/ZachXBT — predictorxyz (INSIDER, BSS: 91, 625% return)

**Training:** 100 steps at learning rate 1e-4. The fine-tuned model ID is set via \`SENTINEL_FINETUNED_MODEL\` and is automatically preferred by Stage 1 when available.
`;

const PIPELINE_OVERVIEW_CONTENT = `
Sentinel processes prediction market trades through a **three-stage AI classification pipeline**. Each trade is enriched with OSINT correlation data before entering the pipeline. Only cases that exceed the BSS threshold advance to deeper analysis.

- **Stage 1 — Triage:** Mistral Small performs fast 4-class classification with a fine-tuned model. Outputs BSS and PES scores.
- **Stage 2 — Deep Analysis:** Magistral reasoning engine applies chain-of-thought Fraud Triangle analysis (Pressure, Opportunity, Rationalization). Runs only for INSIDER/OSINT\_EDGE cases or BSS ≥ 40.
- **Stage 3 — SAR Generation:** Generates Suspicious Activity Reports for high-suspicion cases, suitable for regulatory submission.
`;

const FP_GATE_CONTENT = `
A **5-gate cascade** filters anomalies to minimize false positives. Each gate uses an independent detection method. A case must pass all five gates to be flagged for review.

- **Gate 1 — Statistical Filter:** Z-score threshold and baseline comparison. Eliminates normal volume variance.
- **Gate 2 — Random Forest:** Ensemble classifier trained on 13-feature vectors (wallet age, trade count, win rate, funding risk, z-score, OSINT signal count, etc.).
- **Gate 3 — Autoencoder:** Reconstruction error anomaly detection. High error indicates the feature vector deviates from normal trading patterns.
- **Gate 4 — Game Theory:** Behavioral entropy analysis, pattern mining, network graph analysis, and player type fitness scoring.
- **Gate 5 — Mistral BSS:** Final LLM-based behavioral suspicion assessment. Provides the BSS score used throughout the system.
`;

const DETECTION_CONTENT = `
- **Volume Spike Detection:** Z-score based detection where z = (current\_volume - mean) / stdev. Anomalies flagged at z ≥ 2.0, with high confidence at z > 3.0. Baseline computed from rolling 30-day window.
- **Price Jump Detection:** Detects rapid price movements exceeding 15 percentage points within a short time window. Correlates price jumps with trade timing to identify potential front-running.
- **Fresh Wallet Detection:** Confidence scoring for newly created wallets. High risk when nonce ≤ 5 and age < 48 hours. Fresh wallets placing large bets on specific outcomes are strong insider indicators.
- **DBSCAN Clustering:** Density-Based Spatial Clustering of Applications with Noise (Ester et al., 1996). Groups wallets by behavioral similarity to detect coordinated sniping activity.
- **Composite Risk Scorer:** Weighted signal aggregation combining wallet risk, cluster membership, temporal gap score, and z-score. Multi-signal bonuses applied when multiple independent indicators align.
`;

const OSINT_CONTENT = `
Sentinel correlates trades against multiple open-source intelligence feeds to determine if publicly available information could explain trading activity.

OSINT events are embedded into a **ChromaDB vector store** using Mistral Embed (with MiniLM fallback). Semantic similarity search matches market context against OSINT signals. Temporal gap analysis measures the time difference between trade execution and the nearest correlated public information event.
`;

const REFERENCES_CONTENT = `
The Sentinel system draws on established research in fraud detection, anomaly detection, and market microstructure.
`;

// ---------------------------------------------------------------------------
// Page entrance animation
// ---------------------------------------------------------------------------

const fadeUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] as const },
};

// ---------------------------------------------------------------------------
// System Reference page
// ---------------------------------------------------------------------------

export default function SystemReference() {
  return (
    <div className="space-y-8">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// SYSTEM REFERENCE</p>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          System Reference
        </h1>
      </div>

      {/* ================================================================== */}
      {/* Section 1: Pipeline Overview */}
      {/* ================================================================== */}
      <motion.div {...fadeUp}>
        <Card title="Pipeline Overview">
          <MermaidDiagram chart={PIPELINE_CHART} className="mb-4" />
          <div className="prose-terminal">
            <Markdown>{PIPELINE_OVERVIEW_CONTENT}</Markdown>
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 2: LLM Analysis — Mistral Models */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.05 }}>
        <Card title="LLM Analysis — Mistral Models">
          <div className="prose-terminal mb-6">
            <p>
              Sentinel uses four Mistral models across the classification
              pipeline and OSINT enrichment. Each stage is configured with
              specific temperature and token limits to balance accuracy with
              reasoning depth.
            </p>
          </div>
          <MermaidDiagram chart={LLM_CHART} className="mb-6" />

          {/* Model table */}
          <div className="overflow-x-auto -mx-5 mb-6">
            <table className="w-full min-w-[700px]">
              <thead>
                <tr className="bg-bg-tertiary">
                  <th className="overline text-left px-5 py-2.5">Stage</th>
                  <th className="overline text-left px-3 py-2.5">Model</th>
                  <th className="overline text-left px-3 py-2.5">Temp</th>
                  <th className="overline text-left px-3 py-2.5">Max Tokens</th>
                  <th className="overline text-left px-3 py-2.5">Purpose</th>
                </tr>
              </thead>
              <tbody>
                <ModelRow
                  stage="Stage 1"
                  model="mistral-small-latest"
                  temp="0.1"
                  tokens="500"
                  purpose="Fast 4-class triage classification with a fine-tuned model"
                />
                <ModelRow
                  stage="Stage 2"
                  model="mistral-large-latest"
                  temp="0.3"
                  tokens="2,000"
                  purpose="Chain-of-thought deep analysis with Fraud Triangle framework"
                />
                <ModelRow
                  stage="Stage 3"
                  model="mistral-large-latest"
                  temp="0.2"
                  tokens="3,000"
                  purpose="Formal Suspicious Activity Report generation"
                />
                <ModelRow
                  stage="Embeddings"
                  model="mistral-embed"
                  temp="—"
                  tokens="—"
                  purpose="OSINT event vectorization for semantic similarity search"
                />
                <ModelRow
                  stage="Fine-tune"
                  model="open-mistral-nemo"
                  temp="—"
                  tokens="—"
                  purpose="Base model for custom Stage 1 fine-tuned classifier"
                />
              </tbody>
            </table>
          </div>

          {/* Full markdown content */}
          <div className="prose-terminal">
            <Markdown>{LLM_CONTENT}</Markdown>
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 3: Score Definitions */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.1 }}>
        <Card title="Score Definitions">
          <div className="prose-terminal mb-5">
            <p>
              The LLM produces two primary scores per case. Two additional scores
              are computed by the detection pipeline and community voting system.
            </p>
          </div>
          <div className="space-y-5">
            {Object.values(SCORE_DEFINITIONS).map((def) => (
              <div key={def.label} className="border-l-2 border-accent pl-4 py-1">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="font-mono text-base font-bold text-text-primary">
                    {def.label}
                  </span>
                  <span className="font-mono text-sm text-text-tertiary">
                    — {def.short}
                  </span>
                </div>
                <p className="font-mono text-sm text-text-secondary leading-relaxed">
                  {def.long}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 4: Classification Types */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.15 }}>
        <Card title="Classification Types">
          <div className="space-y-4">
            <ClassRow
              classification="INSIDER"
              description="Trade based on material non-public information. Characterized by high BSS (>60), low PES (<30), and trading activity that precedes public information events. Triggers full SAR generation."
            />
            <ClassRow
              classification="OSINT_EDGE"
              description="Trade based on superior public intelligence gathering. Low BSS (<40), high PES (>60). Trader has legitimately faster access to or better analysis of publicly available information."
            />
            <ClassRow
              classification="FAST_REACTOR"
              description="Quick reaction to breaking news. Trade occurs shortly after news publication. Moderate BSS/PES scores. Temporal gap analysis shows trade timestamp follows the public information event."
            />
            <ClassRow
              classification="SPECULATOR"
              description="Normal market speculation with no detectable information edge. Low BSS, moderate PES. No anomalous trading patterns or timing correlations."
            />
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 5: False Positive Gate */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.2 }}>
        <Card title="False Positive Gate">
          <MermaidDiagram chart={FP_GATE_CHART} className="mb-4" />
          <div className="prose-terminal">
            <Markdown>{FP_GATE_CONTENT}</Markdown>
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 6: Detection Methods */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.25 }}>
        <Card title="Detection Methods">
          <MermaidDiagram chart={DETECTION_CHART} className="mb-4" />
          <div className="prose-terminal">
            <Markdown>{DETECTION_CONTENT}</Markdown>
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 7: OSINT Sources */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.3 }}>
        <Card title="OSINT Sources">
          <div className="overflow-x-auto -mx-5 mb-4">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="bg-bg-tertiary">
                  <th className="overline text-left px-5 py-2.5">Source</th>
                  <th className="overline text-left px-3 py-2.5">Type</th>
                  <th className="overline text-left px-3 py-2.5">Access</th>
                  <th className="overline text-left px-3 py-2.5">Refresh</th>
                </tr>
              </thead>
              <tbody>
                <OsintRow source="GDELT" type="Global news with tone analysis" access="Public (no key)" refresh="5 min" />
                <OsintRow source="GDACS" type="Disaster & emergency alerts" access="Public (no key)" refresh="15 min" />
                <OsintRow source="ACLED" type="Armed conflict event data" access="API key required" refresh="15 min" />
                <OsintRow source="NASA FIRMS" type="Satellite fire detection" access="API key required" refresh="On demand" />
              </tbody>
            </table>
          </div>
          <div className="prose-terminal">
            <Markdown>{OSINT_CONTENT}</Markdown>
          </div>
        </Card>
      </motion.div>

      {/* ================================================================== */}
      {/* Section 8: Research References */}
      {/* ================================================================== */}
      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.35 }}>
        <Card title="Research References">
          <div className="prose-terminal mb-4">
            <Markdown>{REFERENCES_CONTENT}</Markdown>
          </div>
          <div className="space-y-4">
            <Reference
              authors="Cressey, D. R."
              year={1953}
              title="Other People's Money: A Study in the Social Psychology of Embezzlement"
              detail="Foundation of the Fraud Triangle framework (Pressure, Opportunity, Rationalization) used in Stage 2 deep analysis."
            />
            <Reference
              authors="Akerlof, G. A."
              year={1970}
              title="The Market for 'Lemons': Quality Uncertainty and the Market Mechanism"
              detail="Information asymmetry theory. Sentinel detects asymmetric information advantages in prediction market trading."
            />
            <Reference
              authors="Ester, M., Kriegel, H.-P., Sander, J., & Xu, X."
              year={1996}
              title="A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise"
              detail="DBSCAN clustering algorithm used for detecting coordinated wallet behavior and sniping patterns."
            />
            <Reference
              authors="Benford, F."
              year={1938}
              title="The Law of Anomalous Numbers"
              detail="Benford's Law for digit distribution analysis. Used as an additional statistical check in the anomaly detection pipeline."
            />
            <Reference
              authors="Liu, F. T., Ting, K. M., & Zhou, Z.-H."
              year={2008}
              title="Isolation Forest"
              detail="Tree-based anomaly detection. Isolation Forest principles inform the autoencoder gate in the false positive cascade."
            />
            <Reference
              authors="Nash, J. F."
              year={1950}
              title="Equilibrium Points in N-Person Games"
              detail="Game theory foundations applied in the behavioral entropy and player type fitness analysis (Gate 4)."
            />
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ClassRow({
  classification,
  description,
}: {
  classification: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 p-4 rounded-md bg-bg-tertiary border border-border-subtle">
      <div className="shrink-0 mt-0.5">
        <ClassificationBadge classification={classification} />
      </div>
      <p className="font-mono text-sm text-text-secondary leading-relaxed">
        {description}
      </p>
    </div>
  );
}

function ModelRow({
  stage,
  model,
  temp,
  tokens,
  purpose,
}: {
  stage: string;
  model: string;
  temp: string;
  tokens: string;
  purpose: string;
}) {
  return (
    <tr className="hover:bg-bg-hover transition-colors">
      <td className="px-5 py-3 font-mono text-sm font-semibold text-text-primary">
        {stage}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-accent">
        {model}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-secondary text-center">
        {temp}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-secondary text-center">
        {tokens}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-secondary">
        {purpose}
      </td>
    </tr>
  );
}

function OsintRow({
  source,
  type,
  access,
  refresh,
}: {
  source: string;
  type: string;
  access: string;
  refresh: string;
}) {
  return (
    <tr className="hover:bg-bg-hover transition-colors">
      <td className="px-5 py-3 font-mono text-sm font-semibold text-accent">
        {source}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-secondary">
        {type}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-tertiary">
        {access}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-tertiary">
        {refresh}
      </td>
    </tr>
  );
}

function Reference({
  authors,
  year,
  title,
  detail,
}: {
  authors: string;
  year: number;
  title: string;
  detail: string;
}) {
  return (
    <div className="border-l-2 border-accent-muted pl-4 py-1">
      <div className="font-mono text-sm text-text-primary leading-relaxed">
        <span className="text-text-secondary">{authors}</span>{' '}
        <span className="text-text-tertiary">({year})</span>.{' '}
        <em className="text-text-primary">{title}</em>.
      </div>
      <p className="font-mono text-sm text-text-tertiary leading-relaxed mt-1">
        {detail}
      </p>
    </div>
  );
}
