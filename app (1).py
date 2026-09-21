import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from orchestrator import Orchestrator
from evaluate import run_evaluation

st.set_page_config(page_title="GTA V Multi-Agent Analytics", page_icon="🎮", layout="wide")

st.markdown("""
<style>
.main {background-color: #0e1117;}
h1, h2, h3 {font-family: 'Segoe UI', sans-serif;}
.stButton>button {border-radius: 8px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

st.title("🎮 GTA V Worldwide Sales — Multi-Agent AI System")
st.caption("Choose a report, run the pipeline, and it's emailed to the Marketing Team Lead automatically.")

csv_path = config.DEFAULT_CSV_PATH

@st.cache_resource
def get_orchestrator():
    return Orchestrator()

report_options = {v["title"]: k for k, v in config.REPORT_TYPES.items()}

with st.sidebar:
    st.header("Pipeline Controls")
    st.caption(f"Dataset path: `{csv_path}`")
    report_label = st.selectbox("Choose a report to generate", list(report_options.keys()))
    report_type = report_options[report_label]
    recipient = st.text_input("Send report to", value=config.RECIPIENT_EMAIL)
    st.caption(f"Prepared for: {config.PREPARED_FOR} — email is always sent on run.")
    run_btn = st.button("▶ Run Multi-Agent Pipeline", use_container_width=True)
    eval_btn = st.button("🧪 Run Evaluation (3x, no email)", use_container_width=True)

    st.divider()
    with st.expander("🔧 Column Mapping (auto-detected — correct if wrong)"):
        if os.path.exists(csv_path):
            df_preview = pd.read_csv(csv_path)
            df_preview.columns = [c.strip() for c in df_preview.columns]
            orch_preview = get_orchestrator()
            current_map = orch_preview.schema_agent.detect_columns(df_preview)
            st.caption("The Schema Agent classified these using the local model. Fix any mistake and save — it will be remembered for this dataset going forward.")
            all_cols = ["(none)"] + list(df_preview.columns)
            role_choices = {}
            for role in ["country", "platform", "sales", "players", "date"]:
                default = current_map.get(role, "(none)")
                idx = all_cols.index(default) if default in all_cols else 0
                choice = st.selectbox(f"{role.capitalize()} column", all_cols, index=idx, key=f"map_{role}")
                role_choices[role] = choice
            if st.button("💾 Save corrected mapping"):
                orch_preview.schema_agent.detect_columns(df_preview, manual_overrides=role_choices)
                st.success("Saved — this mapping will be reused automatically for this dataset from now on.")
        else:
            st.caption("CSV not found yet.")

tab_overview, tab_insights, tab_actions, tab_eval = st.tabs(
    ["📊 Data Overview", "🧠 AI Insights", "⚙️ Automated Actions", "✅ Evaluation"]
)

if run_btn:
    if not os.path.exists(csv_path):
        st.error(f"CSV not found at {csv_path}.")
    else:
        status = st.status(f"Running: {report_label}...", expanded=True)
        status.write("🔎 Retrieval Agent: loading CSV (using learned column mapping) + FX rate + background context...")
        orch = get_orchestrator()
        result = orch.run(csv_path, report_type=report_type, send_email=True, recipient=recipient)
        if result["success"]:
            status.write("🧠 Analysis Agent: stats + anomalies + bilingual summary + AI commentary done.")
            tail = ", email sent." if result["steps"]["actions"]["email_sent"] else ", email FAILED."
            status.write(f"⚙️ Action Agent: {report_label} generated" + tail)
            status.update(label="Pipeline complete ✅", state="complete")
            st.session_state["last_result"] = result
        else:
            status.update(label="Pipeline failed ❌", state="error")
            st.json(result)

if eval_btn:
    with st.spinner("Running pipeline 3 times for evaluation..."):
        summary, runs = run_evaluation(csv_path, report_type=report_type)
    st.session_state["eval_summary"] = summary

result = st.session_state.get("last_result")

with tab_overview:
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        st.dataframe(df.head(20), use_container_width=True)
        numeric_cols = df.select_dtypes("number").columns.tolist()
        if numeric_cols:
            col = st.selectbox("Chart a numeric column", numeric_cols)
            st.plotly_chart(px.histogram(df, x=col, nbins=30, title=f"Distribution of {col}"), use_container_width=True)
    else:
        st.warning(f"CSV not found at {csv_path}.")

with tab_insights:
    if result:
        st.caption(f"Report type: **{config.REPORT_TYPES[result['report_type']]['title']}** — Prepared for: {config.PREPARED_FOR}")
        if result.get("columns_used"):
            st.caption(f"Columns used: {result['columns_used']}")
        col_en, col_ar = st.columns(2)
        with col_en:
            st.subheader("Summary (English)")
            st.write(result["insights"].get("en", ""))
        with col_ar:
            st.subheader("الملخص (Arabic)")
            st.write(result["insights"].get("ar", ""))

        if result.get("ai_commentary"):
            st.subheader("🤖 AI Commentary")
            st.caption(result["ai_commentary"])

        st.subheader("✅ Recommendations")
        for r in result.get("recommendations", []):
            st.write("• " + r)

        if result.get("anomalies"):
            st.subheader("⚠️ Detected anomalies")
            st.table(result["anomalies"])

        st.subheader("Underlying stats")
        st.json(result["stats"])
    else:
        st.info("Run the pipeline to generate AI insights.")

with tab_actions:
    if result:
        c1, c2, c3 = st.columns(3)
        c1.metric("Report", "✅ Generated" if result.get("report_path") else "—")
        c2.metric("Dashboard", "✅ Updated" if result.get("dashboard_path") else "—")
        c3.metric("Email", "✅ Sent" if result["steps"]["actions"]["email_sent"] else "❌ Failed")

        if result.get("report_path") and os.path.exists(result["report_path"]):
            with open(result["report_path"], "rb") as f:
                st.download_button("⬇ Download PDF report", f, file_name=os.path.basename(result["report_path"]))

        if os.path.exists(config.DASHBOARD_STATE_PATH):
            with open(config.DASHBOARD_STATE_PATH) as f:
                st.json(json.load(f))
    else:
        st.info("Run the pipeline to trigger automated actions.")

with tab_eval:
    summary = st.session_state.get("eval_summary")
    if summary:
        st.subheader("Reliability & Efficiency")
        st.write(f"Success rate: **{summary['success_rate']}**")
        st.json(summary["avg_seconds_per_step"])
    else:
        st.info("Click 'Run Evaluation' in the sidebar to test reliability & speed across multiple runs.")
