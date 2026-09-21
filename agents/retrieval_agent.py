import pandas as pd
import requests

import config


class RetrievalAgent:
    def __init__(self, schema_agent):
        self.schema_agent = schema_agent

    def load_sales_data(self, csv_path: str, manual_overrides: dict = None) -> dict:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        columns = self.schema_agent.detect_columns(df, manual_overrides=manual_overrides)
        return {"df": df, "columns": columns}

    def fetch_exchange_rate(self, base="USD", target="EGP"):
        try:
            resp = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}", timeout=8)
            resp.raise_for_status()
            return resp.json()["rates"].get(target)
        except Exception:
            return None

    def fetch_context_summary(self):
        try:
            resp = requests.get(config.WIKI_SUMMARY_URL, timeout=8)
            resp.raise_for_status()
            return resp.json().get("extract")
        except Exception:
            return None

    def retrieve_all(self, csv_path: str, manual_overrides: dict = None) -> dict:
        sales = self.load_sales_data(csv_path, manual_overrides=manual_overrides)
        fx_rate = self.fetch_exchange_rate()
        context_summary = self.fetch_context_summary()
        return {
            "sales_df": sales["df"],
            "columns": sales["columns"],
            "usd_to_egp": fx_rate,
            "context_summary": context_summary,
        }
