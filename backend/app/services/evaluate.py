import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
from .dataset import load_array

def metrics_from_labels(y, p, names):
    if len(y) == 0: raise ValueError("Test set is empty")
    labels = list(range(len(names))); pr, rc, f1, sup = precision_recall_fscore_support(y, p, labels=labels, average=None, zero_division=0)
    wp, wr, wf, _ = precision_recall_fscore_support(y, p, labels=labels, average="weighted", zero_division=0)
    return {"accuracy": float(accuracy_score(y, p)), "precision": float(wp), "recall": float(wr), "f1": float(wf), "classes": names,
            "confusion_matrix": confusion_matrix(y, p, labels=labels).tolist(),
            "per_class": [{"class": n, "precision": float(pr[i]), "recall": float(rc[i]), "f1": float(f1[i]), "support": int(sup[i])} for i, n in enumerate(names)],
            "report": classification_report(y, p, labels=labels, target_names=names, zero_division=0), "test_samples": int(len(y))}

def evaluate_model(model, test_items, names):
    X = np.stack([load_array(p) for p, _ in test_items]); y = np.array([i for _, i in test_items])
    return metrics_from_labels(y, model.predict(X, verbose=0).argmax(1), names)
