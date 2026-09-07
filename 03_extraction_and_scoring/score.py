"""
Scoring functions: FinBERT (primary), ClimateBERT (comparator), Loughran-McDonald (baseline).
"""
import re
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import pysentiment2 as ps

CHUNK_WORDS = 300
BATCH_SIZE = 8

_lm = ps.LM()


def chunk_text(text: str, chunk_words: int = CHUNK_WORDS):
    words = text.split()
    return [" ".join(words[i:i + chunk_words]) for i in range(0, len(words), chunk_words)] if words else []


class TransformerScorer:
    def __init__(self, model_name: str, pos_label: str, neg_label: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()
        id2label = {k: v.lower() for k, v in self.model.config.id2label.items()}
        label2id = {v: k for k, v in id2label.items()}
        self.pos_idx = label2id[pos_label]
        self.neg_idx = label2id[neg_label]

    def score_chunks(self, chunks):
        """Return mean(P_pos - P_neg) across all chunks, or None if no chunks."""
        if not chunks:
            return None
        diffs = []
        with torch.no_grad():
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                inputs = self.tokenizer(
                    batch, return_tensors="pt", truncation=True,
                    max_length=512, padding=True,
                )
                logits = self.model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)
                diffs.extend((probs[:, self.pos_idx] - probs[:, self.neg_idx]).tolist())
        return sum(diffs) / len(diffs) if diffs else None


def load_finbert():
    return TransformerScorer("ProsusAI/finbert", pos_label="positive", neg_label="negative")


def load_climatebert():
    return TransformerScorer(
        "climatebert/distilroberta-base-climate-sentiment",
        pos_label="opportunity", neg_label="risk",
    )


def score_lm(text: str):
    """Loughran-McDonald: LPS = (pos - neg) / (pos + neg), or None if text is empty."""
    if not text or not text.strip():
        return None
    tokens = _lm.tokenize(text)
    if not tokens:
        return None
    score = _lm.get_score(tokens)
    pos, neg = score["Positive"], score["Negative"]
    if pos + neg == 0:
        return 0.0
    return float((pos - neg) / (pos + neg))
