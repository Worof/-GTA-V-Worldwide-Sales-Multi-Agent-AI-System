from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class LocalLLM:
    """Loaded once, shared by SchemaAgent (column classification) and AnalysisAgent (AI commentary)."""

    def __init__(self, model_name: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def generate(self, prompt: str, max_new_tokens: int = 100) -> str:
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            output_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        except Exception:
            return ""
