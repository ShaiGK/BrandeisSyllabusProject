"""
Shared evaluation utilities for all model training scripts.
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    accuracy_score,
)

LABELS = [
    "ACCOM", "ATTEND", "GRADE", "ASSIGN", "MATERIAL",
    "INTEGRITY", "SCHEDULE", "CONDUCT", "DESCRIP", "ADMIN",
    "CTF", "LATE", "O",
]


def load_jsonl(path):
    """Load a .jsonl file into a list of dicts."""
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_metrics(y_true, y_pred, labels=None):
    """
    Compute per-label F1, macro F1, and accuracy.

    Returns a dict with:
      - accuracy
      - macro_f1
      - per_label: {label: {precision, recall, f1, support}}
    """
    if labels is None:
        labels = LABELS

    report = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    acc = accuracy_score(y_true, y_pred)

    per_label = {}
    for lbl in labels:
        if lbl in report:
            per_label[lbl] = {
                "precision": round(report[lbl]["precision"], 4),
                "recall": round(report[lbl]["recall"], 4),
                "f1": round(report[lbl]["f1-score"], 4),
                "support": int(report[lbl]["support"]),
            }

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "per_label": per_label,
    }


def print_results(metrics, model_name="Model"):
    """Print a formatted results table."""
    print()
    print(f"=== {model_name} Results ===")
    print(f"  Accuracy:  {metrics['accuracy'] * 100:.2f}")
    print(f"  Macro F1:  {metrics['macro_f1'] * 100:.2f}")
    print()
    print(f"  {'Label':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("  " + "-" * 52)
    for lbl, vals in sorted(metrics["per_label"].items()):
        print(
            f"  {lbl:<12} "
            f"{vals['precision'] * 100:>9.2f}  "
            f"{vals['recall'] * 100:>9.2f}  "
            f"{vals['f1'] * 100:>9.2f}  "
            f"{vals['support']:>9}"
        )
    print()


def save_results(metrics, path):
    """Write metrics dict to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Results saved to {path}")


def plot_confusion_matrix(y_true, y_pred, labels, path):
    """Save a confusion matrix heatmap as a PNG."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    # Normalize by row (true label) so colors reflect recall per class
    row_sums = cm.sum(axis=1, keepdims=True)
    cm_norm = np.where(row_sums > 0, cm / row_sums, 0)

    fig, ax = plt.subplots(figsize=(14, 11))
    sns.heatmap(
        cm_norm,
        annot=cm,          # show raw counts in cells
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
        linewidths=0.5,
    )
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.set_title(os.path.splitext(os.path.basename(path))[0].replace("_", " ").title())
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Confusion matrix saved to {path}")


def compute_kappa(y_true, y_pred):
    """Compute Cohen's kappa between two label sequences."""
    return round(cohen_kappa_score(y_true, y_pred), 4)
