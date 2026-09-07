"""
GQE - Stage 6a. LDA topic modelling of the BRSR corpus.

Runs on the same extracted BRSR page-blocks used for FinBERT scoring, so the
language being modelled is exactly the language being scored. Each filing is
split into passages, the corpus is fitted with an 8-topic LDA, and every
company-year gets a vector of topic shares.

The point is not the topics themselves but the link between what a firm chooses
to talk ABOUT and how far its talk diverges from its performance - the thematic
deflection result.

Must run in the local environment (Claude Code), not the analysis sandbox: it
needs the BRSR PDF corpus, which is ~14 GB and never leaves the machine.

Inputs : the BRSR PDF corpus + extract_brsr.py
Output : lda_topics.txt, topic_assignments.csv
"""
import os
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from company_mapping import match_company, parse_fiscal_year
from extract_brsr import extract_brsr_section

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
OUT_TOPICS = "lda_topics.txt"
OUT_ASSIGN = "topic_assignments.csv"

N_TOPICS = 8
PASSAGE_WORDS = 200
RANDOM_STATE = 42

# Hand-read from the top-20 terms of each fitted topic. Labels are descriptive,
# not imposed: the model was fitted first and read afterwards.
TOPIC_LABELS = {
    0: "Workforce/wages/rights",
    1: "Customers/product/data",
    2: "Waste/packaging/circularity",
    3: "Energy/water/emissions",
    4: "Public policy advocacy",
    5: "Health & safety",
    6: "Ethics/anti-corruption",
    7: "Stakeholder/community",
}

# Boilerplate that appears in every BRSR because SEBI prescribes the form.
# Left in, it dominates every topic and the model learns the template, not the firm.
BRSR_STOPWORDS = [
    "principle", "essential", "leadership", "indicator", "indicators",
    "section", "disclosure", "disclosures", "entity", "entities", "company",
    "limited", "ltd", "financial", "year", "fy", "yes", "no", "na", "nil",
    "please", "specify", "details", "detail", "provide", "provided",
    "applicable", "not", "any", "if", "the", "and", "of", "for", "in", "to",
]


def passages(text, size=PASSAGE_WORDS):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


def build_corpus():
    """One record per passage, tagged with its company-year."""
    recs = []
    for fname in sorted(os.listdir(DATASET_DIR)):
        if not fname.lower().endswith(".pdf"):
            continue
        stem = os.path.splitext(fname)[0]
        company, fy = match_company(stem), parse_fiscal_year(stem)
        if company is None or fy is None:
            continue
        try:
            res = extract_brsr_section(os.path.join(DATASET_DIR, fname))
        except Exception:
            continue
        if not res["text"].strip():
            continue
        for p in passages(res["text"]):
            if len(p.split()) >= 50:
                recs.append({"company": company, "year": fy, "passage": p})
    return pd.DataFrame(recs)


def main():
    df = build_corpus()
    print(f"passages: {len(df)} across {df.groupby(['company','year']).ngroups} company-years")

    vec = CountVectorizer(
        max_df=0.85, min_df=10, stop_words="english",
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b",
    )
    X = vec.fit_transform(df["passage"])
    vocab = np.array(vec.get_feature_names_out())

    # drop the prescribed-form vocabulary after vectorising so the min_df cut is
    # made on the real corpus rather than on a pre-pruned one
    keep = ~np.isin(vocab, BRSR_STOPWORDS)
    X = X[:, keep]
    vocab = vocab[keep]

    lda = LatentDirichletAllocation(
        n_components=N_TOPICS, learning_method="batch",
        max_iter=50, random_state=RANDOM_STATE,
    )
    W = lda.fit_transform(X)
    print(f"perplexity: {lda.perplexity(X):.1f}")

    with open(OUT_TOPICS, "w", encoding="utf-8") as f:
        for k, comp in enumerate(lda.components_):
            top = vocab[np.argsort(comp)[::-1][:20]]
            line = f"Topic {k} [{TOPIC_LABELS.get(k,'')}]: " + ", ".join(top)
            print(line)
            f.write(line + "\n")

    shares = pd.DataFrame(W, columns=[f"topic_{k}_share" for k in range(N_TOPICS)])
    shares[["company", "year"]] = df[["company", "year"]].values
    agg = shares.groupby(["company", "year"], as_index=False).mean()

    share_cols = [f"topic_{k}_share" for k in range(N_TOPICS)]
    agg["n_passages"] = (df.groupby(["company", "year"]).size()
                           .reindex(pd.MultiIndex.from_frame(agg[["company", "year"]]))
                           .values)
    agg["dominant_topic"] = agg[share_cols].values.argmax(axis=1)
    agg["dominant_topic_share"] = agg[share_cols].max(axis=1)
    agg["topic_label"] = agg["dominant_topic"].map(TOPIC_LABELS)

    # A firm's dominant topic is usually the corpus-wide dominant topic, which
    # says nothing about that firm. The distinctive topic - highest share
    # relative to the corpus mean - is what actually separates filings.
    lift = agg[share_cols] / agg[share_cols].mean()
    agg["distinctive_topic"] = lift.values.argmax(axis=1)
    agg["distinctive_topic_lift"] = lift.max(axis=1)
    agg["distinctive_topic_label"] = agg["distinctive_topic"].map(TOPIC_LABELS)

    agg.to_csv(OUT_ASSIGN, index=False)
    print(f"\nwritten: {OUT_TOPICS}, {OUT_ASSIGN}")


if __name__ == "__main__":
    main()
