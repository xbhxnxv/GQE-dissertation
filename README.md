# Greenwashing Quantification Engine — code and data

MSc Financial Technology dissertation, University of Birmingham.
Supervisor: Professor Andrew Urquhart.

Everything behind the dissertation: the scripts in the order they were run, the
data files they read and write, and two Colab notebooks that reproduce the
results in a browser with nothing to install.

## What is in this repository

The full code and data are in **`GQE-dissertation.zip`** — download and unzip it
to get the folder layout described below. **`GQE_Terminal.html`** is the saved
terminal log of the pipeline runs, viewable in any browser. The rest of this
page is the guide to what the zip contains and how it fits together.

## Quickest route

Open `07_colab_notebooks/GQE_Analysis.ipynb` in Google Colab and run all cells.
It rebuilds every table in Chapter 4 from the data files in about three minutes,
including recomputing the abnormal returns from raw prices rather than reading
them from store. Set `DRIVE_FOLDER_URL` in the first cell to the shared folder
holding `data/`.

## Folders

| Folder | Contents |
|---|---|
| `01_acquisition` | Daily prices and the market benchmark; retrieval of standalone BRSR filings from the NSE corporate-filings archive |
| `02_name_resolution` | Filename to company-year mapping, plus the dry-run harness used before scoring |
| `03_extraction_and_scoring` | Locating the BRSR section inside an annual report, the three sentiment scorers, and the pipeline that produces `LPS_scores.csv` |
| `04_validation` | Corpus checks run before anything is computed: extraction quality, completeness, recovery reporting |
| `05_score_construction` | `gds_build.py` — the operational composite, the crosswalk, the quality filter, and the divergence score |
| `06_analysis` | Descriptives, event study, hypothesis tests, topic model, FDR correction, robustness, driver analysis. `console_output/` holds the output of each as run |
| `07_colab_notebooks` | Browser-runnable versions of the whole pipeline |
| `08_superseded` | Five abandoned extractors and an early Colab pipeline, kept for audit |
| `data` | Every CSV and workbook the scripts read or write |

## Execution order

```
# Stages 1-2: acquisition (needs network access to NSE and Yahoo Finance)
python 01_acquisition/india_top100_download.py
python 01_acquisition/fetch_nse_brsr.py
python 01_acquisition/redownload_list.py

# Stages 3-5: scoring and validation (needs the BRSR corpus + Hugging Face)
python 02_name_resolution/test_mapping.py     # dry run: which PDFs map where
python 03_extraction_and_scoring/main.py      # writes LPS_scores.csv, resumable
python 04_validation/validate.py
python 04_validation/completeness_check.py

# Stage 6: the score
python 05_score_construction/gds_build.py GQE_OPS_Data_Tracker_v4.xlsx LPS_scores.csv

# Stages 7-8: analysis (CSV inputs only)
python 06_analysis/09_descriptive_stats.py
python 06_analysis/10_event_study.py
python 06_analysis/11_event_study_tests.py
python 06_analysis/12_hypothesis_tests.py
python 06_analysis/13_lda_topics.py           # local only: needs the PDF corpus
python 06_analysis/14_topic_gds_fdr.py
python 06_analysis/15_robustness_pca_sector.py
python 06_analysis/16_ml_drivers_shap.py
```

## Method

GDS = z(LPS) − z(OPS), standardised within each fiscal year.

LPS is the mean FinBERT sentiment over the BRSR narrative, computed over 300-word
chunks so a long filing and a short one sit on the same scale. OPS is an
equal-weighted mean of standardised operational components covering emissions,
energy, renewables, workforce diversity and controversies, with components where
higher means worse sign-inverted before combining. A component absent for a firm
is skipped rather than filled with zero.

A high positive score is a firm whose language runs ahead of its measured
performance relative to that year's cohort. Because standardisation is
within-year, both years centre on zero by construction and scores are positions
in a ranking rather than absolute quantities.

## Environments

Sentiment scoring needs the BRSR PDF corpus (about 14 GB) and network access to
the Hugging Face model repository, so it ran locally rather than in the analysis
environment. Everything from `gds_build.py` onward runs from the CSV files in
`data/`. A reader with this folder reproduces every number in Chapter 4;
reproducing the language scores from source additionally needs the corpus, which
is available from the author.

## Model identifiers

```
FinBERT      : ProsusAI/finbert
               labels = positive / negative / neutral
               LPS    = mean over chunks of  P(positive) - P(negative)

ClimateBERT  : climatebert/distilroberta-base-climate-sentiment
               labels = opportunity / neutral / risk   <-- NOT positive/negative

Loughran-McDonald : pysentiment2.LM()
               score = (pos - neg) / (pos + neg) over the whole BRSR block
```

## Two figures that do not reproduce exactly

Both are flagged in the notebooks rather than hidden.

- SHAP importance for emissions is 0.73 in the dissertation and about 0.69 when
  re-run. The difference is library versions of `xgboost` and `shap`, not data.
  Ordering and conclusion are unchanged.
- The PCA weighting correlation is reported as 0.87 on 86 complete cases; the
  full-sample median-filled version gives 0.865.

## Note on the superseded folder

Five extractors were written and abandoned before the working pipeline. None
produced any number used in the dissertation — their best run managed four clean
extractions out of 195 attempts, which is why the operational data was collected
by hand. They are kept because the reasons they failed are findings about
automated ESG extraction: BRSR mandates what must be disclosed but not how the
table is laid out, so a form designed for standardisation still produces filings
no single parser can read.

## Generative AI

Parts of this code were written with AI assistance under the University of
Birmingham's policy on generative AI in assessed work. Every script was executed
by the author, every output inspected, and every design decision recorded in the
comments checked against the data before being accepted.
