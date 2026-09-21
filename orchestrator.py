import time
import threading

from agents.local_llm import LocalLLM
from agents.schema_agent import SchemaAgent
from agents.retrieval_agent import RetrievalAgent
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent
import config


class Orchestrator:
    def __init__(self):
        self.llm = LocalLLM(config.LLM_MODEL_NAME)
        self.schema_agent = SchemaAgent(self.llm, config.COLUMN_MAP_CACHE_PATH)
        self.retrieval = RetrievalAgent(self.schema_agent)
        self.analysis = AnalysisAgent(self.llm)
        self.action = ActionAgent()

    def _retry(self, func, max_retries=None, backoff=None):
        max_retries = max_retries or config.MAX_RETRIES
        backoff = backoff or config.RETRY_BACKOFF_SECONDS
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exc = e
                if attempt < max_retries:
                    time.sleep(backoff * attempt)
        raise last_exc

    def run(self, csv_path: str, report_type: str = "overall", send_email: bool = True,
            recipient: str = None, manual_overrides: dict = None) -> dict:
        log = {"steps": {}, "success": True, "report_type": report_type}

        t0 = time.time()
        try:
            data = self._retry(lambda: self.retrieval.retrieve_all(csv_path, manual_overrides=manual_overrides))
            log["steps"]["retrieval"] = {"ok": True, "seconds": round(time.time() - t0, 2)}
        except Exception as e:
            log["steps"]["retrieval"] = {"ok": False, "error": str(e)}
            log["success"] = False
            return log

        t0 = time.time()
        try:
            def _analyze():
                stats = self.analysis.compute_stats(data["sales_df"], data["columns"])
                anomalies = self.analysis.detect_anomalies(data["sales_df"], data["columns"])
                recommendations = self.analysis.generate_recommendations(report_type, stats, anomalies)
                insights = self.analysis.build_bilingual_summary(report_type, stats, data["usd_to_egp"], anomalies)
                ai_commentary = self.analysis.generate_ai_commentary(report_type, stats)
                sales_values = self.analysis.get_sales_series(data["sales_df"], data["columns"])
                return stats, anomalies, recommendations, insights, ai_commentary, sales_values

            stats, anomalies, recommendations, insights, ai_commentary, sales_values = self._retry(_analyze)
            log["steps"]["analysis"] = {"ok": True, "seconds": round(time.time() - t0, 2)}
        except Exception as e:
            log["steps"]["analysis"] = {"ok": False, "error": str(e)}
            log["success"] = False
            return log

        t0 = time.time()
        results = {}

        def _report():
            try:
                results["report_path"] = self.action.generate_report(
                    report_type, stats, insights, ai_commentary, anomalies,
                    data.get("context_summary"), recommendations, sales_values
                )
            except Exception as e:
                results["report_error"] = str(e)

        def _dashboard():
            try:
                results["dashboard_path"] = self.action.update_dashboard(
                    report_type, stats, insights, ai_commentary, anomalies,
                    data.get("context_summary"), recommendations
                )
            except Exception as e:
                results["dashboard_error"] = str(e)

        threads = [threading.Thread(target=_report), threading.Thread(target=_dashboard)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        email_ok = False
        if send_email and "report_path" in results:
            try:
                email_ok = self._retry(lambda: self.action.send_email(report_type, results["report_path"], insights, recipient))
            except Exception as e:
                results["email_error"] = str(e)

        actions_ok = "report_path" in results and "dashboard_path" in results
        log["steps"]["actions"] = {"ok": actions_ok, "seconds": round(time.time() - t0, 2), "email_sent": email_ok}
        if "report_error" in results:
            log["steps"]["actions"]["report_error"] = results["report_error"]
        if "dashboard_error" in results:
            log["steps"]["actions"]["dashboard_error"] = results["dashboard_error"]
        if not actions_ok:
            log["success"] = False

        log["stats"] = stats
        log["anomalies"] = anomalies
        log["recommendations"] = recommendations
        log["insights"] = insights
        log["ai_commentary"] = ai_commentary
        log["context_summary"] = data.get("context_summary")
        log["report_path"] = results.get("report_path")
        log["dashboard_path"] = results.get("dashboard_path")
        log["columns_used"] = data.get("columns")
        return log
