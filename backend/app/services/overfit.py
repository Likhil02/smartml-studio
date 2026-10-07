def detect(history):
    """Rule-based overfitting detection on [{epoch,acc,val_acc,loss,val_loss}]."""
    if len(history) < 3: return {"overfitting": False, "severity": "none", "warnings": ["Too few epochs to judge overfitting."]}
    w, last = [], history[-1]; gap = last["acc"] - last["val_acc"]
    k = max(3, len(history) // 4); tail = history[-k:]
    if gap > 0.15: w.append(f"Training accuracy exceeds validation accuracy by {gap*100:.1f} points.")
    loss_down = tail[-1]["loss"] < tail[0]["loss"]; vloss_up = tail[-1]["val_loss"] > tail[0]["val_loss"] * 1.05
    if loss_down and vloss_up: w.append("Training loss is falling while validation loss is rising over the last epochs.")
    sev = "high" if len(w) == 2 or gap > 0.3 else "moderate" if w else "none"
    return {"overfitting": bool(w), "severity": sev, "gap": round(gap, 4), "warnings": w or ["No overfitting pattern detected."]}
