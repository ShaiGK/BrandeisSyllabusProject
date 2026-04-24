"""
Compute Inter-Annotator Agreement (IAA) for double-annotated syllabi.

Input:
  - annotations/all_annotations.json   (must contain >=2 entries per doc_id
                                         for any double-annotated docs)
  - label_studio_tasks.json            (for raw text, to reconstruct line offsets)

Output:
  Printed report:
    - Per-pair Cohen's κ + per-label F1 breakdown
    - Overall: average pairwise κ, Fleiss' κ, percent agreement
    - Per-label average pairwise F1 summary
  Saved files (results/):
    - iaa_results.json
    - iaa_confusion_<A>_vs_<B>.png   (one per annotator pair)
    - iaa_confusion_aggregate.png    (all pairs pooled)
    - iaa_pairwise_kappa.png         (bar chart of pairwise κ values)
    - iaa_label_agreement.png        (per-label avg pairwise F1 bar chart)

Run:
  python compute_iaa.py
"""

import itertools
import json
import os
import statistics
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
)

from evaluate import (
    LABELS,
    compute_kappa,
    load_jsonl,
    save_results,
)

TASKS_FILE = "label_studio_tasks.json"
ANNOTATIONS_FILE = "annotations/all_annotations.json"
OUTPUT_FILE = "results/iaa/iaa_results.json"
RESULTS_DIR = "results/iaa"


# ── Data loading ───────────────────────────────────────────────────────────────

def load_tasks(path):
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    return {t["data"]["doc_id"]: t["data"] for t in tasks}


def load_all_annotations(path):
    """
    Return {doc_id: [annotation, ...]} — ALL entries (not just the last one).
    Invalid docs are dropped.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    by_doc = defaultdict(list)
    for entry in raw:
        if entry.get("validity") == "Invalid":
            continue
        by_doc[entry["doc_id"]].append(entry)
    return by_doc


def get_line_offsets(text):
    """
    Split text into non-empty lines, filtering bare page numbers
    (lone ascending integers) just like convert_to_sentences.py does.
    """
    lines = []
    pos = 0
    next_page = None
    for raw_line in text.split("\n"):
        line_start = pos
        line_end = pos + len(raw_line)
        stripped = raw_line.strip()
        if stripped:
            if stripped.isdigit():
                n = int(stripped)
                if next_page is None or n == next_page:
                    next_page = n + 1
                else:
                    lines.append((line_start, line_end, stripped))
            else:
                lines.append((line_start, line_end, stripped))
        pos = line_end + 1
    return lines


def assign_label(line_start, line_end, spans):
    """Majority-overlap rule: assign the label covering >50% of the line."""
    line_len = line_end - line_start
    if line_len == 0:
        return "O"
    best_label, best_overlap = "O", 0
    for span in spans:
        overlap = min(line_end, span["end"]) - max(line_start, span["start"])
        if overlap > 0 and overlap / line_len > 0.5 and overlap > best_overlap:
            best_overlap = overlap
            best_label = span["label"]
    return best_label


def annotation_to_line_labels(ann, text):
    spans = ann.get("spans", [])
    lines = get_line_offsets(text)
    return [assign_label(cs, ce, spans) for cs, ce, _ in lines]


# ── Fleiss' kappa ──────────────────────────────────────────────────────────────

def fleiss_kappa(ratings_matrix):
    """
    Compute Fleiss' kappa for multiple raters.

    ratings_matrix : np.ndarray of shape (N_subjects, N_categories)
        Each row sums to the number of raters (n).
        ratings_matrix[i, j] = number of raters who assigned category j to subject i.

    Returns the Fleiss' kappa coefficient (float).
    """
    N, k = ratings_matrix.shape
    n = ratings_matrix[0].sum()   # number of raters per subject (assumed constant)

    # p_j: proportion of all assignments in category j
    p_j = ratings_matrix.sum(axis=0) / (N * n)

    # P_i: proportion of agreeing pairs for each subject
    P_i = (np.sum(ratings_matrix ** 2, axis=1) - n) / (n * (n - 1))

    P_bar = P_i.mean()
    P_e   = (p_j ** 2).sum()

    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1.0 - P_e)


def build_ratings_matrix(label_sequences, label_list):
    """
    Build the ratings matrix needed by fleiss_kappa.

    label_sequences : list of lists, one list per rater, each of length N_subjects.
    Returns np.ndarray of shape (N_subjects, len(label_list)).
    """
    label2idx = {l: i for i, l in enumerate(label_list)}
    N = len(label_sequences[0])
    k = len(label_list)
    matrix = np.zeros((N, k), dtype=float)
    for seq in label_sequences:
        for i, lbl in enumerate(seq):
            if lbl in label2idx:
                matrix[i, label2idx[lbl]] += 1
    return matrix


# ── Metrics helpers ────────────────────────────────────────────────────────────

def per_label_f1(y_true, y_pred, label_list):
    """Return {label: f1} for every label in label_list that has support > 0."""
    present = set(y_true)
    active  = [l for l in label_list if l in present]
    report  = classification_report(
        y_true, y_pred, labels=label_list, output_dict=True, zero_division=0
    )
    return {
        lbl: round(report[lbl]["f1-score"], 4)
        for lbl in active
        if lbl in report
    }


def percent_agreement(sequences):
    """Fraction of lines where ALL raters agree."""
    n = len(sequences[0])
    agree = sum(
        1 for i in range(n)
        if len({seq[i] for seq in sequences}) == 1
    )
    return agree / n if n else 0.0


# ── Plotting ───────────────────────────────────────────────────────────────────

def _active_labels(y_true, label_list):
    """Labels that appear in y_true (support > 0)."""
    present = set(y_true)
    return [l for l in label_list if l in present]


def save_confusion_matrix(y_true, y_pred, label_list, path, title):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    active = _active_labels(y_true, label_list)
    cm = confusion_matrix(y_true, y_pred, labels=active)
    row_sums = cm.sum(axis=1, keepdims=True)
    cm_norm  = np.where(row_sums > 0, cm / row_sums, 0)

    fig, ax = plt.subplots(figsize=(max(8, len(active)), max(7, len(active) - 1)))
    sns.heatmap(
        cm_norm,
        annot=cm,
        fmt="d",
        cmap="Blues",
        xticklabels=active,
        yticklabels=active,
        ax=ax,
        linewidths=0.5,
        vmin=0, vmax=1,
    )
    ax.set_xlabel("Annotator 2 (predicted)", fontsize=11)
    ax.set_ylabel("Annotator 1 (reference)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"    → {path}")


def save_pairwise_kappa_chart(pair_labels, kappa_values, path):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    colours = ["#4C72B0" if k >= 0.6 else "#DD8452" if k >= 0.4 else "#C44E52"
               for k in kappa_values]
    fig, ax = plt.subplots(figsize=(max(5, len(pair_labels) * 1.4), 4))
    bars = ax.bar(pair_labels, kappa_values, color=colours, edgecolor="white", width=0.5)
    ax.axhline(0.8, color="green",  linestyle="--", linewidth=1, label="0.8 (almost perfect)")
    ax.axhline(0.6, color="orange", linestyle="--", linewidth=1, label="0.6 (substantial)")
    ax.axhline(0.4, color="red",    linestyle="--", linewidth=1, label="0.4 (moderate)")
    for bar, val in zip(bars, kappa_values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.3f}", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Cohen's κ", fontsize=11)
    ax.set_title("Pairwise Cohen's κ", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"    → {path}")


def save_label_agreement_chart(label_avg_f1, path):
    """Bar chart of per-label average pairwise F1, sorted descending."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    labels_sorted = sorted(label_avg_f1, key=label_avg_f1.get, reverse=True)
    values        = [label_avg_f1[l] for l in labels_sorted]
    colours       = ["#4C72B0" if v >= 0.7 else "#DD8452" if v >= 0.5 else "#C44E52"
                     for v in values]

    fig, ax = plt.subplots(figsize=(max(8, len(labels_sorted) * 0.9), 4))
    bars = ax.bar(labels_sorted, values, color=colours, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Average pairwise F1", fontsize=11)
    ax.set_title("Per-label average pairwise F1 (excludes zero-support labels)", fontsize=12,
                 fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"    → {path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=== INTER-ANNOTATOR AGREEMENT ===")
    print()

    for path in (TASKS_FILE, ANNOTATIONS_FILE):
        if not os.path.exists(path):
            print(f"  ERROR: {path} not found.")
            if path == ANNOTATIONS_FILE:
                print("  Run 'python annotate.py finish' first.")
            sys.exit(1)

    tasks  = load_tasks(TASKS_FILE)
    by_doc = load_all_annotations(ANNOTATIONS_FILE)

    # Keep only docs annotated by at least 2 people
    multi_docs = {doc_id: anns for doc_id, anns in by_doc.items() if len(anns) >= 2}

    if not multi_docs:
        print("  No double-annotated documents found.")
        print("  To compute IAA, two or more annotators must annotate the same doc_id.")
        sys.exit(0)

    annotator_names_all = sorted({
        ann.get("annotator", f"ann_{i}")
        for anns in multi_docs.values()
        for i, ann in enumerate(anns)
    })
    print(f"  Multi-annotated docs : {len(multi_docs)}")
    print(f"  Annotators involved  : {', '.join(annotator_names_all)}")
    print()

    # ── Build per-doc, per-annotator label sequences ───────────────────────────
    # doc_labels[doc_id][annotator_name] = [label, label, ...]
    doc_labels = {}
    for doc_id, anns in sorted(multi_docs.items()):
        if doc_id not in tasks:
            print(f"  WARNING: {doc_id} not found in tasks file, skipping.")
            continue
        text = tasks[doc_id].get("text", "")
        doc_labels[doc_id] = {}
        for ann in anns:
            name = ann.get("annotator", f"annotator_{len(doc_labels[doc_id])}")
            doc_labels[doc_id][name] = annotation_to_line_labels(ann, text)

    if not doc_labels:
        print("  No valid documents to compare.")
        sys.exit(0)

    # Collect all annotator names that actually contributed
    all_annotators = sorted({name for d in doc_labels.values() for name in d})
    pairs = list(itertools.combinations(all_annotators, 2))

    # ── Per-pair analysis ──────────────────────────────────────────────────────
    print("=" * 60)
    print("  PAIRWISE AGREEMENT")
    print("=" * 60)

    pair_results   = {}   # (a1, a2) → {kappa, f1_per_label, n_lines, n_docs}
    agg_y1_all     = []   # pooled y_true across all pairs (for aggregate confusion)
    agg_y2_all     = []   # pooled y_pred across all pairs

    for a1, a2 in pairs:
        y1_flat, y2_flat = [], []
        n_docs_pair = 0

        for doc_id, ann_map in sorted(doc_labels.items()):
            if a1 not in ann_map or a2 not in ann_map:
                continue
            seq1 = ann_map[a1]
            seq2 = ann_map[a2]
            min_len = min(len(seq1), len(seq2))
            y1_flat.extend(seq1[:min_len])
            y2_flat.extend(seq2[:min_len])
            n_docs_pair += 1

        if not y1_flat:
            continue

        kappa  = compute_kappa(y1_flat, y2_flat)
        pct    = percent_agreement([y1_flat, y2_flat])
        lf1    = per_label_f1(y1_flat, y2_flat, LABELS)
        non_o  = {l: v for l, v in lf1.items() if l != "O"}
        macro  = round(statistics.mean(non_o.values()), 4) if non_o else 0.0

        pair_results[(a1, a2)] = {
            "kappa":          kappa,
            "percent_agree":  round(pct, 4),
            "macro_f1":       macro,
            "f1_per_label":   lf1,
            "n_lines":        len(y1_flat),
            "n_docs":         n_docs_pair,
        }

        agg_y1_all.extend(y1_flat)
        agg_y2_all.extend(y2_flat)

        print()
        print(f"  Pair: {a1}  vs  {a2}")
        print(f"    Docs: {n_docs_pair}   Lines: {len(y1_flat)}")
        print(f"    Cohen's κ       : {kappa:.4f}")
        print(f"    Percent agree   : {pct * 100:.1f}%")
        print(f"    Macro F1 (non-O): {macro * 100:.2f}")
        print()
        print(f"    {'Label':<12} {'F1':>8}")
        print("    " + "-" * 22)
        for lbl in LABELS:
            if lbl in lf1:
                marker = "  ← low" if lf1[lbl] < 0.5 and lbl != "O" else ""
                print(f"    {lbl:<12} {lf1[lbl] * 100:>7.2f}{marker}")
        print()

        # Confusion matrix for this pair
        safe_a1 = a1.replace(" ", "_")
        safe_a2 = a2.replace(" ", "_")
        cm_path = os.path.join(RESULTS_DIR, f"iaa_confusion_{safe_a1}_vs_{safe_a2}.png")
        save_confusion_matrix(
            y1_flat, y2_flat, LABELS, cm_path,
            title=f"IAA Confusion: {a1} (ref) vs {a2}",
        )

    # ── Overall multi-annotator statistics ────────────────────────────────────
    print()
    print("=" * 60)
    print("  OVERALL MULTI-ANNOTATOR AGREEMENT")
    print("=" * 60)
    print()

    kappas = [v["kappa"] for v in pair_results.values()]
    avg_kappa = statistics.mean(kappas)

    print(f"  Annotators            : {', '.join(all_annotators)}")
    print(f"  Number of pairs       : {len(pairs)}")
    print(f"  Average pairwise κ    : {avg_kappa:.4f}")
    if len(kappas) > 1:
        print(f"  Std dev pairwise κ    : {statistics.stdev(kappas):.4f}")
        print(f"  Min / Max κ           : {min(kappas):.4f} / {max(kappas):.4f}")

    # Fleiss' kappa — requires same set of annotators for every doc
    # Compute over docs where all annotators contributed
    common_docs = [
        doc_id for doc_id, ann_map in doc_labels.items()
        if all(a in ann_map for a in all_annotators)
    ]

    fleiss_k = None
    if len(all_annotators) >= 2 and common_docs:
        # Concatenate all lines across common docs
        combined_seqs = {a: [] for a in all_annotators}
        for doc_id in sorted(common_docs):
            ann_map = doc_labels[doc_id]
            min_len = min(len(ann_map[a]) for a in all_annotators)
            for a in all_annotators:
                combined_seqs[a].extend(ann_map[a][:min_len])

        label_seqs = [combined_seqs[a] for a in all_annotators]
        ratings = build_ratings_matrix(label_seqs, LABELS)
        fleiss_k = round(float(fleiss_kappa(ratings)), 4)
        print(f"  Fleiss' κ             : {fleiss_k:.4f}  (over {len(common_docs)} docs with all annotators)")

    # Percent agreement across all pairs pooled
    if agg_y1_all:
        pct_agg = percent_agreement([agg_y1_all, agg_y2_all])
        print(f"  Overall percent agree : {pct_agg * 100:.1f}%  (all pairs pooled)")

    # ── Per-label average pairwise F1 ─────────────────────────────────────────
    print()
    print("=" * 60)
    print("  PER-LABEL AVERAGE PAIRWISE F1")
    print("=" * 60)
    print()

    # Collect F1 per label across all pairs
    label_f1_lists = defaultdict(list)
    for res in pair_results.values():
        for lbl, val in res["f1_per_label"].items():
            if lbl != "O":
                label_f1_lists[lbl].append(val)

    label_avg_f1 = {
        lbl: round(statistics.mean(vals), 4)
        for lbl, vals in label_f1_lists.items()
        if vals
    }

    print(f"  {'Label':<12} {'Avg F1':>8}  {'Per-pair F1'}")
    print("  " + "-" * 60)
    for lbl in LABELS:
        if lbl == "O" or lbl not in label_avg_f1:
            continue
        per_pair_str = "  ".join(
            f"{a1[0]}/{a2[0]}={pair_results[(a1, a2)]['f1_per_label'].get(lbl, float('nan')):.2f}"
            for (a1, a2) in pairs
            if (a1, a2) in pair_results
        )
        print(f"  {lbl:<12} {label_avg_f1[lbl] * 100:>7.2f}   {per_pair_str}")

    # ── Interpretation guide ───────────────────────────────────────────────────
    print()
    print("  κ interpretation:")
    print("    0.0–0.2  slight  |  0.2–0.4  fair  |  0.4–0.6  moderate")
    print("    0.6–0.8  substantial  |  0.8–1.0  almost perfect")
    print()

    # ── Plots ──────────────────────────────────────────────────────────────────
    print("  Saving plots...")

    # Aggregate confusion matrix (all pairs pooled)
    if agg_y1_all:
        save_confusion_matrix(
            agg_y1_all, agg_y2_all, LABELS,
            os.path.join(RESULTS_DIR, "iaa_confusion_aggregate.png"),
            title="IAA Confusion Matrix (all pairs pooled)",
        )

    # Pairwise kappa bar chart
    pair_labels_chart = [f"{a1}\nvs\n{a2}" for (a1, a2) in pair_results]
    save_pairwise_kappa_chart(
        pair_labels_chart,
        list(kappas),
        os.path.join(RESULTS_DIR, "iaa_pairwise_kappa.png"),
    )

    # Per-label average pairwise F1
    if label_avg_f1:
        save_label_agreement_chart(
            label_avg_f1,
            os.path.join(RESULTS_DIR, "iaa_label_agreement.png"),
        )

    # ── Save JSON ──────────────────────────────────────────────────────────────
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results = {
        "annotators":         all_annotators,
        "num_docs":           len(multi_docs),
        "avg_pairwise_kappa": round(avg_kappa, 4),
        "fleiss_kappa":       fleiss_k,
        "pairwise": {
            f"{a1}_vs_{a2}": v
            for (a1, a2), v in pair_results.items()
        },
        "label_avg_f1": label_avg_f1,
    }
    save_results(results, OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()
