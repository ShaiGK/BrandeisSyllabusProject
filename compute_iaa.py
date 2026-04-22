"""
Compute Inter-Annotator Agreement (IAA) for double-annotated syllabi.

Input:
  - annotations/all_annotations.json   (must contain >=2 entries per doc_id
                                         for any double-annotated docs)
  - label_studio_tasks.json            (for raw text, to reconstruct line offsets)

Output:
  - Printed report: overall Cohen's kappa, per-label F1, confusion matrix
  - results/iaa_results.json

To double-annotate a syllabus, two annotators simply both annotate the same
doc_id.  The annotate.py workflow does not prevent this — just note which
doc_ids overlap when you run 'python annotate.py start'.

Run:
  python compute_iaa.py
"""

import json
import os
import sys
from collections import defaultdict

from evaluate import (
    LABELS,
    compute_kappa,
    compute_metrics,
    load_jsonl,
    plot_confusion_matrix,
    print_results,
    save_results,
)

TASKS_FILE = "label_studio_tasks.json"
ANNOTATIONS_FILE = "annotations/all_annotations.json"
OUTPUT_FILE = "results/iaa_results.json"
CONFUSION_PNG = "results/iaa_confusion_matrix.png"


def load_tasks(path):
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    return {t["data"]["doc_id"]: t["data"] for t in tasks}


def load_all_annotations(path):
    """
    Return a dict {doc_id: [annotation, annotation, ...]} preserving ALL
    entries (unlike the version in convert_to_sentences.py which keeps only
    the last).  Invalid docs are still dropped.
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
    """Same logic as convert_to_sentences.py."""
    lines = []
    pos = 0
    for raw_line in text.split("\n"):
        line_start = pos
        line_end = pos + len(raw_line)
        stripped = raw_line.strip()
        if stripped:
            lines.append((line_start, line_end, stripped))
        pos = line_end + 1
    return lines


def assign_label(line_start, line_end, spans):
    """Same logic as convert_to_sentences.py."""
    line_len = line_end - line_start
    if line_len == 0:
        return "O"
    best_label = "O"
    best_overlap = 0
    for span in spans:
        overlap = min(line_end, span["end"]) - max(line_start, span["start"])
        if overlap > 0 and overlap / line_len > 0.5 and overlap > best_overlap:
            best_overlap = overlap
            best_label = span["label"]
    return best_label


def annotation_to_line_labels(ann, text):
    """Convert one annotation entry → list of (line_text, label) pairs."""
    spans = ann.get("spans", [])
    lines = get_line_offsets(text)
    return [(line_text, assign_label(cs, ce, spans)) for cs, ce, line_text in lines]


def main():
    print()
    print("=== INTER-ANNOTATOR AGREEMENT ===")
    print()

    if not os.path.exists(TASKS_FILE):
        print(f"  ERROR: {TASKS_FILE} not found.")
        sys.exit(1)
    if not os.path.exists(ANNOTATIONS_FILE):
        print(f"  ERROR: {ANNOTATIONS_FILE} not found.")
        print("  Run 'python annotate.py finish' first.")
        sys.exit(1)

    tasks = load_tasks(TASKS_FILE)
    by_doc = load_all_annotations(ANNOTATIONS_FILE)

    # Find docs with exactly 2 annotations (double-annotated)
    double_docs = {doc_id: anns for doc_id, anns in by_doc.items() if len(anns) >= 2}

    if not double_docs:
        print("  No double-annotated documents found.")
        print("  To compute IAA, two annotators must annotate the same doc_id.")
        print("  Check your annotations/all_annotations.json for repeated doc_ids.")
        sys.exit(0)

    print(f"  Found {len(double_docs)} double-annotated document(s).")
    print()

    all_y1, all_y2 = [], []
    per_doc_kappas = []

    for doc_id, anns in sorted(double_docs.items()):
        if doc_id not in tasks:
            print(f"  WARNING: {doc_id} not found in tasks file, skipping.")
            continue

        text = tasks[doc_id].get("text", "")
        ann1, ann2 = anns[0], anns[1]  # use first two if >2 exist

        labels1 = [lbl for _, lbl in annotation_to_line_labels(ann1, text)]
        labels2 = [lbl for _, lbl in annotation_to_line_labels(ann2, text)]

        # Both sequences must be same length (same text → same lines)
        min_len = min(len(labels1), len(labels2))
        labels1 = labels1[:min_len]
        labels2 = labels2[:min_len]

        kappa = compute_kappa(labels1, labels2)
        per_doc_kappas.append(kappa)
        annotator1 = ann1.get("annotator", "annotator1")
        annotator2 = ann2.get("annotator", "annotator2")
        print(f"  {doc_id[:60]}")
        print(f"    Annotators: {annotator1} vs {annotator2}  |  κ = {kappa:.4f}  |  lines = {min_len}")

        all_y1.extend(labels1)
        all_y2.extend(labels2)

    if not all_y1:
        print("  No valid double-annotated pairs found.")
        sys.exit(0)

    print()
    print(f"  Overall Cohen's κ: {compute_kappa(all_y1, all_y2):.4f}")
    if len(per_doc_kappas) > 1:
        import statistics
        print(f"  Mean per-doc κ:    {statistics.mean(per_doc_kappas):.4f}")
        print(f"  Std  per-doc κ:    {statistics.stdev(per_doc_kappas):.4f}")
    print()

    # Treat annotator 1 as "reference", annotator 2 as "predicted"
    metrics = compute_metrics(all_y1, all_y2, labels=LABELS)
    metrics["kappa"] = compute_kappa(all_y1, all_y2)
    metrics["num_docs"] = len(double_docs)
    metrics["num_lines"] = len(all_y1)

    print_results(metrics, model_name="Inter-Annotator Agreement")

    os.makedirs("results", exist_ok=True)
    save_results(metrics, OUTPUT_FILE)
    plot_confusion_matrix(all_y1, all_y2, LABELS, CONFUSION_PNG)

    print()
    print("  Interpretation guide for κ:")
    print("    0.0 – 0.2  slight    |  0.2 – 0.4  fair")
    print("    0.4 – 0.6  moderate  |  0.6 – 0.8  substantial")
    print("    0.8 – 1.0  almost perfect")
    print()


if __name__ == "__main__":
    main()
