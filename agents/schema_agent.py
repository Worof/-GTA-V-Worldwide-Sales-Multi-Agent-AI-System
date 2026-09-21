import hashlib
import json
import os
import pandas as pd


class SchemaAgent:
    """Classifies each CSV column's role using the local LLM (semantic, not keyword-matching),
    validates the guess against hard dtype/uniqueness rules, and caches the result per dataset
    schema so it 'remembers' the mapping across runs. A manual correction from the UI overwrites
    the cache permanently for that schema — this is the learning/feedback loop."""

    ROLES = ["country", "platform", "sales", "players", "date", "other"]

    def __init__(self, llm, cache_path: str):
        self.llm = llm
        self.cache_path = cache_path

    def _fingerprint(self, df: pd.DataFrame) -> str:
        return hashlib.md5(",".join(sorted(df.columns)).encode()).hexdigest()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)

    def _profile_column(self, series: pd.Series) -> dict:
        sample = series.dropna().astype(str).head(5).tolist()
        return {
            "is_numeric": bool(pd.api.types.is_numeric_dtype(series)),
            "n_unique": int(series.nunique(dropna=True)),
            "n_rows": int(len(series)),
            "sample_values": sample,
        }

    def _classify_column_llm(self, col_name: str, profile: dict) -> str:
        prompt = (
            "You are classifying a column of a video-game worldwide sales dataset. "
            f"Column name: '{col_name}'. Sample values: {profile['sample_values']}. "
            f"Data type: {'numeric' if profile['is_numeric'] else 'text'}. "
            "Which single category best fits this column? Choose exactly one word from: "
            "country, platform, sales, players, date, other. Answer with only that one word."
        )
        answer = self.llm.generate(prompt, max_new_tokens=6).lower()
        for role in self.ROLES:
            if role in answer:
                return role
        return "other"

    def _validate_role(self, role: str, profile: dict) -> str:
        """Rule-based safety net — an LLM guess can never override these hard constraints,
        which is what stops a numeric region-code column from being accepted as 'country'."""
        if role in ("sales", "players") and not profile["is_numeric"]:
            return "other"
        if role in ("country", "platform"):
            if profile["is_numeric"]:
                return "other"
            uniqueness_ratio = profile["n_unique"] / max(profile["n_rows"], 1)
            avg_len = (sum(len(s) for s in profile["sample_values"]) / max(len(profile["sample_values"]), 1)) if profile["sample_values"] else 999
            if uniqueness_ratio > 0.5 or avg_len > 40:
                return "other"
        return role

    def profile_all(self, df: pd.DataFrame) -> dict:
        """Exposed so the UI can show sample values per column when letting the user correct a mapping."""
        return {col: self._profile_column(df[col]) for col in df.columns}

    def detect_columns(self, df: pd.DataFrame, manual_overrides: dict = None) -> dict:
        fingerprint = self._fingerprint(df)
        cache = self._load_cache()

        if manual_overrides is not None:
            cleaned = {k: v for k, v in manual_overrides.items() if v and v != "(none)"}
            cache[fingerprint] = cleaned
            self._save_cache(cache)
            return cleaned

        if fingerprint in cache:
            return cache[fingerprint]

        role_to_col = {}
        for col in df.columns:
            profile = self._profile_column(df[col])
            role = self._classify_column_llm(col, profile)
            role = self._validate_role(role, profile)
            if role != "other" and role not in role_to_col:
                role_to_col[role] = col

        cache[fingerprint] = role_to_col
        self._save_cache(cache)
        return role_to_col
