import pandas as pd


class AnalysisAgent:
    def __init__(self, llm):
        self.llm = llm

    # ---------- Stats ----------
    def compute_stats(self, df: pd.DataFrame, columns: dict) -> dict:
        stats = {"rows": len(df)}
        sales_col = columns.get("sales")
        country_col = columns.get("country")
        platform_col = columns.get("platform")
        players_col = columns.get("players")

        if sales_col:
            sales_numeric = pd.to_numeric(df[sales_col], errors="coerce")
            stats["total_sales"] = float(sales_numeric.sum(skipna=True))
            stats["avg_sales"] = float(sales_numeric.mean(skipna=True))
        if country_col and sales_col:
            grouped = df.assign(_sales=pd.to_numeric(df[sales_col], errors="coerce"))
            stats["top_countries"] = (
                grouped.groupby(country_col)["_sales"].sum().sort_values(ascending=False).head(5).to_dict()
            )
        if platform_col and sales_col:
            grouped = df.assign(_sales=pd.to_numeric(df[sales_col], errors="coerce"))
            stats["top_platforms"] = (
                grouped.groupby(platform_col)["_sales"].sum().sort_values(ascending=False).head(5).to_dict()
            )
        if players_col:
            players_numeric = pd.to_numeric(df[players_col], errors="coerce")
            stats["total_players"] = float(players_numeric.sum(skipna=True))
            stats["avg_players"] = float(players_numeric.mean(skipna=True))
        return stats

    def get_sales_series(self, df: pd.DataFrame, columns: dict):
        sales_col = columns.get("sales")
        if not sales_col:
            return None
        return pd.to_numeric(df[sales_col], errors="coerce").dropna().tolist()

    # ---------- Anomalies ----------
    def detect_anomalies(self, df: pd.DataFrame, columns: dict, z_threshold: float = 2.0) -> list:
        anomalies = []
        sales_col = columns.get("sales")
        if not sales_col:
            return anomalies
        sales_numeric = pd.to_numeric(df[sales_col], errors="coerce")

        for group_field in ("country", "platform"):
            col = columns.get(group_field)
            if not col:
                continue
            grouped = df.assign(_sales=sales_numeric).groupby(col)["_sales"].sum().dropna()
            if len(grouped) < 3:
                continue
            mean, std = grouped.mean(), grouped.std()
            if not std or pd.isna(std) or std == 0:
                continue
            z_scores = (grouped - mean) / std
            outliers = z_scores[z_scores.abs() >= z_threshold]
            for name, z in outliers.items():
                anomalies.append({
                    "group": group_field, "name": str(name),
                    "value": float(grouped[name]), "z_score": round(float(z), 2),
                })
        return anomalies[:5]

    # ---------- Recommendations ----------
    def generate_recommendations(self, report_type: str, stats: dict, anomalies: list) -> list:
        recs = []
        top_country = next(iter(stats["top_countries"]), None) if stats.get("top_countries") else None
        top_platform = next(iter(stats["top_platforms"]), None) if stats.get("top_platforms") else None

        if report_type == "regional":
            if top_country:
                recs.append(f"Allocate additional regional marketing budget to {top_country}, the current leading market.")
            for country, val in list(stats.get("top_countries", {}).items())[1:3]:
                recs.append(f"Consider a growth campaign in {country} (current sales: {val:,.2f}) to close the gap with the top market.")
        elif report_type == "platform":
            if top_platform:
                recs.append(f"Prioritize {top_platform}-specific promotions and store placement, the current best-performing platform.")
            for plat, val in list(stats.get("top_platforms", {}).items())[1:3]:
                recs.append(f"Evaluate platform-specific bundles for {plat} (current sales: {val:,.2f}).")
        elif report_type == "engagement":
            if "avg_players" in stats:
                recs.append(f"Average engagement is {stats['avg_players']:,.0f} players per entry — set up retention campaigns if this trend declines.")
            recs.append("Consider in-game events or seasonal content to sustain player engagement across regions.")
        elif report_type == "risk":
            if anomalies:
                for a in anomalies:
                    recs.append(f"Investigate the anomaly in {a['name']} ({a['group']}, z-score {a['z_score']}) before the next budget cycle.")
            else:
                recs.append("No statistically significant anomalies detected this run — no immediate risk action needed.")
        else:
            if top_country:
                recs.append(f"Increase marketing investment in {top_country}, the leading market by sales.")
            if top_platform:
                recs.append(f"Prioritize platform-specific content and optimization for {top_platform}.")
            for a in anomalies[:2]:
                recs.append(f"Investigate the unusual sales pattern in {a['name']} ({a['group']}) — z-score {a['z_score']}.")
            if "avg_players" in stats:
                recs.append(f"Average engagement is {stats['avg_players']:,.0f} players per entry — monitor this trend closely.")

        if not recs:
            recs.append("Not enough detected columns to generate specific recommendations — verify column mapping.")
        return recs

    # ---------- Deterministic bilingual core (numbers are Python-formatted, never machine-translated) ----------
    def _core_numbers(self, stats: dict, fx_rate):
        rows = stats.get("rows", 0)
        total_sales = stats.get("total_sales")
        egp = (total_sales * fx_rate) if (total_sales and fx_rate) else None
        top_country = next(iter(stats.get("top_countries", {})), None)
        top_platform = next(iter(stats.get("top_platforms", {})), None)
        avg_players = stats.get("avg_players")
        total_players = stats.get("total_players")
        return rows, total_sales, egp, top_country, top_platform, avg_players, total_players

    def build_bilingual_summary(self, report_type: str, stats: dict, fx_rate, anomalies: list) -> dict:
        rows, total_sales, egp, top_country, top_platform, avg_players, total_players = self._core_numbers(stats, fx_rate)
        egp_en = f" (~{egp:,.0f} EGP)" if egp else ""
        egp_ar = f" (حوالي {egp:,.0f} جنيه مصري)" if egp else ""

        if report_type == "regional":
            countries = stats.get("top_countries", {})
            lines = [f"{c}: {v:,.2f}" for c, v in countries.items()]
            en = (f"This regional deep-dive covers {rows} records across {len(countries)} tracked markets. "
                  f"Top markets by sales — " + "; ".join(lines) + ". "
                  + (f"{top_country} leads all markets." if top_country else ""))
            ar = (f"يغطي هذا التقرير الإقليمي التفصيلي {rows} سجلاً عبر {len(countries)} سوقاً. "
                  f"أفضل الأسواق من حيث المبيعات — " + "؛ ".join(lines) + ". "
                  + (f"يتصدر سوق {top_country} جميع الأسواق." if top_country else ""))

        elif report_type == "platform":
            platforms = stats.get("top_platforms", {})
            lines = [f"{p}: {v:,.2f}" for p, v in platforms.items()]
            en = (f"This platform performance report covers {rows} records across {len(platforms)} tracked platforms. "
                  f"Top platforms by sales — " + "; ".join(lines) + ". "
                  + (f"{top_platform} is the best-performing platform." if top_platform else ""))
            ar = (f"يغطي تقرير أداء المنصات هذا {rows} سجلاً عبر {len(platforms)} منصة. "
                  f"أفضل المنصات من حيث المبيعات — " + "؛ ".join(lines) + ". "
                  + (f"تُعد منصة {top_platform} الأفضل أداءً." if top_platform else ""))

        elif report_type == "engagement":
            en = (f"This player engagement report covers {rows} records. "
                  + (f"Total tracked players: {total_players:,.0f}. " if total_players else "")
                  + (f"Average players per record: {avg_players:,.0f}. " if avg_players else "")
                  + (f"{top_platform} shows the strongest platform engagement by sales." if top_platform else ""))
            ar = (f"يغطي تقرير تفاعل اللاعبين هذا {rows} سجلاً. "
                  + (f"إجمالي اللاعبين المسجلين: {total_players:,.0f}. " if total_players else "")
                  + (f"متوسط عدد اللاعبين لكل سجل: {avg_players:,.0f}. " if avg_players else "")
                  + (f"تُظهر منصة {top_platform} أقوى تفاعل من حيث المبيعات." if top_platform else ""))

        elif report_type == "risk":
            if anomalies:
                lines = [f"{a['name']} ({a['group']}, z-score {a['z_score']})" for a in anomalies]
                en = f"This risk report covers {rows} records. Detected anomalies: " + "; ".join(lines) + "."
                ar = f"يغطي تقرير المخاطر هذا {rows} سجلاً. الحالات الشاذة المكتشفة: " + "؛ ".join(lines) + "."
            else:
                en = f"This risk report covers {rows} records. No statistically significant anomalies were detected this run."
                ar = f"يغطي تقرير المخاطر هذا {rows} سجلاً. لم يتم اكتشاف أي حالات شاذة ذات دلالة إحصائية في هذا التشغيل."

        else:  # overall
            en = (f"The dataset covers {rows} records. Total sales stand at {total_sales:,.2f}{egp_en}. "
                  + (f"{top_country} is the top-performing market. " if top_country else "")
                  + (f"{top_platform} leads by platform. " if top_platform else "")
                  + (f"Average player count per entry is {avg_players:,.0f}." if avg_players else ""))
            ar = (f"تغطي مجموعة البيانات {rows} سجلاً. يبلغ إجمالي المبيعات {total_sales:,.2f} دولار{egp_ar}. "
                  + (f"{top_country} هي السوق الأعلى أداءً. " if top_country else "")
                  + (f"تتصدر منصة {top_platform} من حيث المبيعات. " if top_platform else "")
                  + (f"يبلغ متوسط عدد اللاعبين لكل سجل {avg_players:,.0f} لاعب." if avg_players else ""))

        return {"en": en.strip(), "ar": ar.strip()}

    # ---------- Optional AI commentary (local LLM — qualitative only, never carries numbers) ----------
    def generate_ai_commentary(self, report_type: str, stats: dict) -> str:
        prompt = (
            f"In two sentences, give a marketing-oriented interpretive comment (no numbers) about a "
            f"video game {report_type} analytics report. Focus on strategic implications, not data restatement."
        )
        text = self.llm.generate(prompt, max_new_tokens=80)
        if len(text.split()) < 6:
            return ""
        return text
