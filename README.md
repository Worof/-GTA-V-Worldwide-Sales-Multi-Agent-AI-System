# 🎮 GTA V Worldwide Sales — Multi-Agent AI Analytics System

A fully orchestrated multi-agent AI system that retrieves, analyzes, and acts on video-game
sales data — built as a final project demonstrating end-to-end AI agent orchestration and
automation, with **zero paid LLM API calls**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-ff4b4b)
![Transformers](https://img.shields.io/badge/HuggingFace-flan--t5-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [The Agents](#-the-agents)
- [Pipeline Run Sequence](#-pipeline-run-sequence)
- [Schema Agent — Column Classification Logic](#-schema-agent--column-classification-logic)
- [Reliability Model — Retry & Parallel Execution](#-reliability-model--retry--parallel-execution)
- [Report Types & Content Structure](#-report-types--content-structure)
- [The UI](#️-the-ui)
- [Sample Output](#-sample-output)
- [Reliability & Testing](#-reliability--testing)
- [Tech Stack](#️-tech-stack)
- [Running It](#-running-it)
- [Dataset](#-dataset)
- [Possible Extensions](#-possible-extensions)
- [Author](#-author)
- [License](#-license)

---

## 📌 Overview

This project simulates a real-world marketing analytics workflow: a dataset lands, and instead
of a human manually pulling numbers into a slide deck, a coordinated team of AI agents does it —
retrieves the data, figures out what its columns actually mean, computes and interprets the
numbers, writes a bilingual report, charts it, and emails it to a decision-maker. Every run.

Built and demoed entirely in **Google Colab**, with a public **Streamlit** UI served through
**ngrok**.

---

## 🧠 System Architecture

\`\`\`mermaid
flowchart TD
    A[📄 CSV Dataset] --> R[🔎 Retrieval Agent]
    W[🌐 Wikipedia API] --> R
    FX[💱 Exchange Rate API] --> R
    R <-->|column role mapping| S[🧩 Schema Agent]
    S -.->|reads/writes| CACHE[(💾 column_map_cache.json)]
    R --> AN[📊 Analysis Agent]
    LLM[🤖 Local LLM<br/>flan-t5-base] -.->|shared instance| S
    LLM -.->|shared instance| AN
    AN --> AC[⚙️ Action Agent]
    AC --> PDF[📑 Bilingual PDF Report]
    AC --> DASH[📈 Live Dashboard JSON]
    AC --> MAIL[📧 Email to Marketing Team Lead]

    subgraph Orchestrator["🎛️ Orchestrator — retry + parallel control"]
    R
    AN
    AC
    end

    style Orchestrator fill:#1a1d24,stroke:#3E7CB1,color:#fff
    style LLM fill:#4a2b5c,stroke:#8E44AD,color:#fff
    style CACHE fill:#2b3a1a,stroke:#5c8e44,color:#fff
\`\`\`

**Design principles behind the pipeline:**
- **Sequential where order matters, parallel where it doesn't** — report generation and
  dashboard update fire concurrently via threads; retrieval → analysis → action stays sequential
  because each stage depends on the last.
- **Retry-with-backoff** wraps every stage, so a transient failure (a flaky API call, a model
  hiccup) self-heals instead of failing the whole run.
- **Fail loud, not silent** — a failed report or dashboard write now correctly marks the whole
  run as failed, instead of being swallowed by a background thread.
- **One shared local LLM instance** — loaded once by the Orchestrator, used by both the Schema
  Agent (column classification) and Analysis Agent (AI commentary), rather than each agent
  loading its own copy.

---

## 🤖 The Agents

\`\`\`mermaid
classDiagram
    class Orchestrator {
        +run(csv_path, report_type, send_email)
        -_retry(func)
    }
    class RetrievalAgent {
        +retrieve_all(csv_path)
        +fetch_exchange_rate()
        +fetch_context_summary()
    }
    class SchemaAgent {
        +detect_columns(df)
        -_classify_column(col)
        -_keyword_guess(col)
        -_validate_role(role)
    }
    class AnalysisAgent {
        +compute_stats(df, columns)
        +detect_anomalies(df, columns)
        +build_bilingual_summary()
        +generate_recommendations()
        +generate_ai_commentary()
    }
    class ActionAgent {
        +generate_report()
        +send_email()
        +update_dashboard()
    }
    class LocalLLM {
        +generate(prompt)
    }

    Orchestrator --> RetrievalAgent
    Orchestrator --> AnalysisAgent
    Orchestrator --> ActionAgent
    RetrievalAgent --> SchemaAgent
    SchemaAgent --> LocalLLM
    AnalysisAgent --> LocalLLM
\`\`\`

| Agent | Responsibility | Key techniques |
|---|---|---|
| **Retrieval Agent** | Loads the CSV, fetches live USD→EGP FX rate, pulls Wikipedia background context | \`requests\`, live public APIs |
| **Schema Agent** | Figures out which column is \`country\`, \`platform\`, \`sales\`, \`players\`, \`date\` | Local LLM asked **twice** with independently-worded few-shot prompts; disagreements resolved by keyword heuristic; unresolved columns flagged \`needs_review\` instead of guessed |
| **Analysis Agent** | Computes stats, detects anomalies, writes the report content | pandas z-score anomaly detection; **deterministic bilingual (EN/AR) templates** for every number (numbers are never machine-translated); optional qualitative AI commentary from \`flan-t5-base\` |
| **Action Agent** | Turns analysis into real outputs | \`fpdf2\` (bilingual PDF with embedded charts), \`matplotlib\`, SMTP email delivery, live dashboard JSON |
| **Orchestrator** | Coordinates all of the above | Retry-with-backoff, parallel thread execution, structured run logs |

---

## 🔁 Pipeline Run Sequence

\`\`\`mermaid
sequenceDiagram
    participant U as User (Streamlit UI)
    participant O as Orchestrator
    participant R as Retrieval Agent
    participant S as Schema Agent
    participant AN as Analysis Agent
    participant AC as Action Agent
    participant E as Email (SMTP)

    U->>O: Run Pipeline (report_type)
    O->>R: retrieve_all(csv_path)
    R->>S: detect_columns(df)
    S-->>R: {country, platform, sales, players, date}
    R->>R: fetch FX rate + Wikipedia context
    R-->>O: data bundle
    O->>AN: compute_stats + detect_anomalies
    AN->>AN: build_bilingual_summary (EN/AR)
    AN->>AN: generate_ai_commentary (local LLM)
    AN-->>O: stats, anomalies, insights, recommendations
    par Report generation
        O->>AC: generate_report()
        AC-->>O: PDF path
    and Dashboard update
        O->>AC: update_dashboard()
        AC-->>O: dashboard JSON path
    end
    O->>AC: send_email(report, insights)
    AC->>E: SMTP send
    E-->>AC: delivered
    AC-->>O: email_sent = true
    O-->>U: run log (stats, charts, PDF, dashboard, email status)
\`\`\`

---

## 🩺 Schema Agent — Column Classification Logic

Real-world datasets don't ship with predictable column names. Instead of hardcoding
\`df["Country"]\`, the Schema Agent classifies every column through a dual-verification process
designed specifically to catch hallucination from a small local model:

\`\`\`mermaid
flowchart TD
    START([Column: name + sample values + dtype]) --> P1[Prompt A<br/>few-shot style 1]
    START --> P2[Prompt B<br/>few-shot style 2]
    P1 --> V1{Vote A}
    P2 --> V2{Vote B}
    V1 --> AGREE{Do A and B<br/>agree?}
    V2 --> AGREE
    AGREE -->|Yes| VALID[Rule-based validation<br/>dtype + uniqueness check]
    AGREE -->|No| KW[Keyword heuristic tiebreaker]
    KW --> KWMATCH{Keyword matches<br/>either vote?}
    KWMATCH -->|Yes| VALID
    KWMATCH -->|No| FLAG[🚩 Mark 'other'<br/>needs_review = true]
    VALID --> ROLEOK{Passes dtype/<br/>uniqueness rules?}
    ROLEOK -->|Yes| ASSIGN[✅ Assign role]
    ROLEOK -->|No| FLAG
    ASSIGN --> CACHE[(💾 Cache mapping<br/>per dataset schema)]
    FLAG --> UI[⚠️ Surface in UI<br/>for manual correction]
    UI --> CACHE

    style FLAG fill:#5c2b2b,stroke:#c0392b,color:#fff
    style ASSIGN fill:#2b5c2b,stroke:#27ae60,color:#fff
    style CACHE fill:#2b3a1a,stroke:#5c8e44,color:#fff
\`\`\`

This is the project's actual "learning" loop: not model retraining, but a persistent,
user-correctable memory of what each column means — a wrong guess can never silently ship into
a report, because both classification passes must agree *and* pass a hard rule-based check
before a role is assigned.

---

## ♻️ Reliability Model — Retry & Parallel Execution

\`\`\`mermaid
stateDiagram-v2
    [*] --> Retrieval
    Retrieval --> RetrievalRetry: fails
    RetrievalRetry --> Retrieval: attempt < max_retries
    RetrievalRetry --> Failed: attempt = max_retries
    Retrieval --> Analysis: success

    Analysis --> AnalysisRetry: fails
    AnalysisRetry --> Analysis: attempt < max_retries
    AnalysisRetry --> Failed: attempt = max_retries
    Analysis --> Actions: success

    state Actions {
        [*] --> ReportGen
        [*] --> DashboardUpdate
        ReportGen --> [*]
        DashboardUpdate --> [*]
    }
    Actions --> EmailSend: report + dashboard ok
    Actions --> Failed: either fails

    EmailSend --> EmailRetry: fails
    EmailRetry --> EmailSend: attempt < max_retries
    EmailRetry --> PartialSuccess: attempt = max_retries
    EmailSend --> Success: sent

    Success --> [*]
    PartialSuccess --> [*]
    Failed --> [*]
\`\`\`

Every stage uses exponential backoff (\`RETRY_BACKOFF_SECONDS * attempt\`) between attempts, and
report generation + dashboard update run as **parallel threads** since neither depends on the
other's output.

---

## 📊 Report Types & Content Structure

\`\`\`mermaid
flowchart LR
    SELECT[User selects report type] --> OVERALL[Overall Performance]
    SELECT --> REGIONAL[Regional Deep-Dive]
    SELECT --> PLATFORM[Platform Performance]
    SELECT --> ENGAGEMENT[Player Engagement]
    SELECT --> RISK[Anomaly & Risk]

    OVERALL --> CONTENT1[Totals + top country<br/>+ top platform + engagement<br/>+ background context]
    REGIONAL --> CONTENT2[Country-by-country<br/>breakdown + market recs]
    PLATFORM --> CONTENT3[Platform-by-platform<br/>breakdown + platform recs]
    ENGAGEMENT --> CONTENT4[Player-count trends<br/>+ retention recs]
    RISK --> CONTENT5[Z-score anomalies<br/>+ investigation priorities]

    CONTENT1 --> OUTPUT[📑 PDF + 📈 Dashboard + 📧 Email]
    CONTENT2 --> OUTPUT
    CONTENT3 --> OUTPUT
    CONTENT4 --> OUTPUT
    CONTENT5 --> OUTPUT
\`\`\`

Every report — regardless of type — is addressed to the **Marketing Team Lead** and contains:

\`\`\`mermaid
flowchart TD
    PDF[📑 PDF Report] --> T[Title + Prepared For + Timestamp]
    PDF --> SUM[Bilingual Summary — EN/AR]
    PDF --> AI[Optional AI Commentary]
    PDF --> REC[Recommendations — type-specific]
    PDF --> ANOM[Anomalies table — Risk report only]
    PDF --> CHARTS[Charts — bar/histogram, type-dependent]
    PDF --> CTX[Background Context — Overall report only]
    PDF --> RAW[Raw stats JSON — appendix]
\`\`\`

Reports are generated as a detailed PDF (summary, recommendations, anomalies where relevant,
charts, background context, Arabic translation), and **emailed automatically** on every run —
no manual send step.

---

## 🖥️ The UI

\`\`\`mermaid
flowchart TD
    APP[Streamlit App] --> SIDEBAR[Sidebar: Pipeline Controls]
    SIDEBAR --> SEL[Report type selector]
    SIDEBAR --> RCPT[Recipient email]
    SIDEBAR --> RUN[▶ Run Pipeline button]
    SIDEBAR --> EVAL[🧪 Run Evaluation button]
    SIDEBAR --> MAP[🔧 Column Mapping panel<br/>view + correct Schema Agent output]

    APP --> TABS[Main tabs]
    TABS --> T1[📊 Data Overview<br/>raw data + distribution chart]
    TABS --> T2[🧠 AI Insights<br/>bilingual summary + anomalies + recs]
    TABS --> T3[⚙️ Automated Actions<br/>status + PDF download + dashboard JSON]
    TABS --> T4[✅ Evaluation<br/>success rate + latency metrics]
\`\`\`

<!-- 📸 Add your own screenshots here once you have them, e.g.: -->
<!-- ![UI Overview](screenshots/overview.png) -->
<!-- ![AI Insights Tab](screenshots/insights.png) -->
<!-- ![Sample PDF Report](screenshots/report_page1.png) -->

---

## 🔎 Sample Output

**Terminal-style run log:**
\`\`\`
🔎 Retrieval Agent: loaded 14,780 rows from CSV; FX rate USD→EGP fetched; Wikipedia context fetched.
🧠 Analysis Agent: computed stats; found 2 anomaly(ies); generated bilingual EN/AR summary + AI commentary.
⚙️ Action Agent: PDF report generated, dashboard updated, email sent to worofyousef@gmail.com.
\`\`\`

**Example anomaly output:**

| Country/Platform | Group | Total Sales | Z-score |
|---|---|---|---|
| Argentina | country | 41,203.5 | 2.72 |

**Example recommendations output (Overall report):**

\`\`\`mermaid
graph LR
    A[Top country: Colombia] --> R1[Increase marketing<br/>investment in Colombia]
    B[Top platform: PC] --> R2[Prioritize PC-specific<br/>content & optimization]
    C[Anomaly: Argentina<br/>z-score 2.72] --> R3[Investigate Argentina's<br/>unusual sales pattern]
    D[Avg players: 31,627] --> R4[Monitor engagement<br/>trend closely]
\`\`\`

---

## ✅ Reliability & Testing

\`evaluate.py\` runs the full pipeline multiple times back-to-back (no email sent during testing)
and reports:

- **Success rate** across runs
- **Average latency per stage** (retrieval / analysis / actions)

Every stage is wrapped in retry-with-backoff, and thread-level exceptions in report generation
or dashboard updates are now captured into the run log instead of silently passing.

\`\`\`python
{
  'runs': 3,
  'success_rate': '3/3',
  'avg_seconds_per_step': {'retrieval': 0.4, 'analysis': 9.8, 'actions': 1.2}
}
\`\`\`

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Data | \`pandas\`, \`requests\` |
| Local LLM | \`transformers\` (\`google/flan-t5-base\`) — no paid API |
| Visualization | \`matplotlib\`, \`plotly\` |
| PDF generation | \`fpdf2\`, \`arabic-reshaper\`, \`python-bidi\` |
| UI | \`streamlit\` |
| Public demo hosting | \`pyngrok\` |
| Automation | \`smtplib\` (Gmail SMTP, App Password auth) |

---

## 🚀 Running It

Built and run entirely in **Google Colab** — see
[\`notebook/Final_Project_Worof_Ahmed.ipynb\`](notebook/Final_Project_Worof_Ahmed.ipynb) for the
full cell-by-cell setup.

1. Open the notebook in Colab.
2. Run the install cell.
3. Enter your Gmail App Password and ngrok auth token when prompted (never hardcode these).
4. Upload the dataset once to \`/content/\`.
5. Run the agent-file cells (\`%%writefile\` cells build \`agents/\`, \`orchestrator.py\`, \`app.py\`).
6. The final cell launches Streamlit + ngrok and prints a public URL.

### Running locally instead
\`\`\`bash
git clone https://github.com/Worof/gta-v-multi-agent-analytics.git
cd gta-v-multi-agent-analytics
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
\`\`\`
You'll still need a Gmail App Password (\`EMAIL_APP_PASSWORD\` env var) for the email step, and
the dataset placed at the path set in \`config.py\`.

---

## 📂 Dataset

[GTA V Worldwide Sales and Player Analytics](https://www.kaggle.com/datasets/crystalbaby/gta-v-worldwide-sales-and-player-analytics)
(Kaggle) — worldwide sales figures and player engagement metrics.

---

## 🔮 Possible Extensions

- Swap \`flan-t5-base\` for a larger local model on a GPU runtime for richer AI commentary
- Add a second file-based retrieval source (PDF ingestion) alongside the CSV + APIs
- Persist historical dashboard snapshots to chart trend-over-time, not just latest run
- Add a lightweight embeddings-based Q&A agent over the dataset rows

---

## 👤 Author

**Worof Ahmed** — Marketing Data Scientist & Content Team Lead
[GitHub](https://github.com/Worof) · Building AI agents for marketing and content systems.

---

## 📄 License

MIT — see [LICENSE](LICENSE).