import json
import os
import re
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

import config


class ActionAgent:
    def __init__(self):
        os.makedirs(config.REPORTS_DIR, exist_ok=True)
        self._arabic_font_path = self._ensure_arabic_font()

    def _ensure_arabic_font(self):
        font_path = os.path.join(config.REPORTS_DIR, "NotoNaskhArabic-Regular.ttf")
        if os.path.exists(font_path):
            return font_path
        try:
            url = "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            with open(font_path, "wb") as f:
                f.write(resp.content)
            return font_path
        except Exception:
            return None

    def _shape_arabic(self, text: str) -> str:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text

    def _sanitize_pdf_text(self, text, max_word_len: int = 50) -> str:
        if text is None:
            return ""
        text = str(text)
        text = text.encode("latin-1", "replace").decode("latin-1")

        def _break(match):
            word = match.group(0)
            return " ".join(word[i:i + max_word_len] for i in range(0, len(word), max_word_len))

        return re.sub(r"\S{%d,}" % (max_word_len + 1), _break, text)

    def _safe_multicell(self, pdf, h, text, **kwargs):
        try:
            pdf.multi_cell(0, h, self._sanitize_pdf_text(text), **kwargs)
        except Exception:
            try:
                pdf.multi_cell(0, h, "[content omitted]")
            except Exception:
                pass

    def _bar_chart(self, data_dict: dict, title: str, path: str):
        if not data_dict:
            return None
        try:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.bar([str(k)[:20] for k in data_dict.keys()], list(data_dict.values()), color="#3E7CB1")
            ax.set_title(title)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            fig.savefig(path)
            plt.close(fig)
            return path
        except Exception:
            return None

    def _histogram(self, values: list, title: str, path: str):
        if not values:
            return None
        try:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.hist(values, bins=30, color="#8E44AD")
            ax.set_title(title)
            plt.tight_layout()
            fig.savefig(path)
            plt.close(fig)
            return path
        except Exception:
            return None

    def generate_report(
        self, report_type: str, stats: dict, insights: dict, ai_commentary: str = "",
        anomalies: list = None, context_summary: str = None,
        recommendations: list = None, sales_values: list = None,
    ) -> str:
        anomalies = anomalies or []
        recommendations = recommendations or []
        meta = config.REPORT_TYPES.get(report_type, config.REPORT_TYPES["overall"])

        chart_country = None
        chart_platform = None
        chart_hist = None
        if report_type in ("overall", "regional"):
            chart_country = self._bar_chart(stats.get("top_countries"), "Top countries by sales",
                                             os.path.join(config.REPORTS_DIR, "chart_country.png"))
        if report_type in ("overall", "platform"):
            chart_platform = self._bar_chart(stats.get("top_platforms"), "Top platforms by sales",
                                              os.path.join(config.REPORTS_DIR, "chart_platform.png"))
        if report_type in ("overall", "engagement"):
            chart_hist = self._histogram(sales_values, "Sales distribution across records",
                                          os.path.join(config.REPORTS_DIR, "chart_hist.png"))

        pdf = FPDF()
        pdf.add_page()

        try:
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, f"GTA V Analytics — {meta['title']}", ln=True)
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 6, f"Prepared for: {config.PREPARED_FOR}", ln=True)
            pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            pdf.ln(3)
        except Exception:
            pass

        try:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Summary", ln=True)
            pdf.set_font("Helvetica", size=11)
            self._safe_multicell(pdf, 6, insights.get("en", ""))
            pdf.ln(2)
        except Exception:
            pass

        if ai_commentary:
            try:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 7, "AI Commentary", ln=True)
                pdf.set_font("Helvetica", "I", 10)
                self._safe_multicell(pdf, 5, ai_commentary)
                pdf.ln(2)
            except Exception:
                pass

        try:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Recommendations", ln=True)
            pdf.set_font("Helvetica", size=10)
            for r in recommendations:
                self._safe_multicell(pdf, 5, f"- {r}")
            pdf.ln(2)
        except Exception:
            pass

        if report_type == "risk" and anomalies:
            try:
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Detected Anomalies", ln=True)
                pdf.set_font("Helvetica", size=10)
                for a in anomalies:
                    self._safe_multicell(pdf, 5, f"- {a.get('name')} ({a.get('group')}): z-score {a.get('z_score')}, total {a.get('value', 0):.2f}")
                pdf.ln(2)
            except Exception:
                pass

        for chart_path, caption in ((chart_country, "Top countries by sales"),
                                     (chart_platform, "Top platforms by sales"),
                                     (chart_hist, "Sales distribution")):
            if chart_path and os.path.exists(chart_path):
                try:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.cell(0, 6, caption, ln=True)
                    pdf.image(chart_path, w=170)
                    pdf.set_xy(pdf.l_margin, pdf.get_y())
                    pdf.ln(3)
                except Exception:
                    pass

        if context_summary and report_type == "overall":
            try:
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Background Context", ln=True)
                pdf.set_font("Helvetica", "I", 9)
                self._safe_multicell(pdf, 5, context_summary)
                pdf.ln(2)
            except Exception:
                pass

        if insights.get("ar") and self._arabic_font_path:
            try:
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, f"{meta['title_ar']} — الملخص", ln=True)
                pdf.add_font("NotoArabic", "", self._arabic_font_path)
                pdf.set_font("NotoArabic", size=11)
                pdf.multi_cell(0, 6, self._shape_arabic(insights["ar"]), align="R")
                pdf.ln(2)
            except Exception:
                pass

        try:
            pdf.set_font("Helvetica", "I", 8)
            self._safe_multicell(pdf, 5, f"Raw stats: {json.dumps(stats, default=str)}")
        except Exception:
            pass

        out_path = os.path.join(config.REPORTS_DIR, f"gta_v_report_{report_type}.pdf")
        pdf.output(out_path)
        return out_path

    def send_email(self, report_type: str, report_path: str, insights: dict, recipient: str = None) -> bool:
        recipient = recipient or config.RECIPIENT_EMAIL
        if not config.EMAIL_APP_PASSWORD:
            raise RuntimeError("EMAIL_APP_PASSWORD is not set.")
        meta = config.REPORT_TYPES.get(report_type, config.REPORT_TYPES["overall"])

        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_ADDRESS
        msg["To"] = recipient
        msg["Subject"] = meta["email_subject"]
        body = (
            f"Hi,\n\nPlease find attached the {meta['title']} — prepared for the {config.PREPARED_FOR}.\n\n"
            f"{insights.get('en', '')}\n\n---\n{insights.get('ar', '')}\n"
        )
        msg.attach(MIMEText(body, "plain"))

        with open(report_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=os.path.basename(report_path))
            msg.attach(part)

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.sendmail(config.EMAIL_ADDRESS, recipient, msg.as_string())
        return True

    def update_dashboard(self, report_type: str, stats: dict, insights: dict, ai_commentary: str,
                          anomalies: list = None, context_summary: str = None, recommendations: list = None) -> str:
        payload = {
            "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "report_type": report_type,
            "prepared_for": config.PREPARED_FOR,
            "stats": stats,
            "insights": insights,
            "ai_commentary": ai_commentary,
            "anomalies": anomalies or [],
            "context_summary": context_summary,
            "recommendations": recommendations or [],
        }
        with open(config.DASHBOARD_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        return config.DASHBOARD_STATE_PATH
