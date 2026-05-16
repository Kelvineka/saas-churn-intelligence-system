# ================================================================
#  SaaS Customer Retention & Churn Intelligence System
#  Stage 3: Churn Prediction Model
#
#  Model: Logistic Regression
#  Why Logistic Regression?
#    - Outputs a probability (0-100%) not just a yes/no label
#    - Every coefficient is explainable in plain English
#    - Appropriate for a junior portfolio — simpler is more defensible
#
#  Outputs:
#    model_performance.csv    accuracy, precision, recall, AUC
#    feature_importance.csv   which factors drive churn most
#    churn_predictions.csv    every customer's churn probability
#    confusion_matrix.png     visual model evaluation
#    feature_importance.png   visual of top churn drivers
# ================================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model    import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing   import StandardScaler
from sklearn.metrics         import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)

C_BLUE  = "#0F4C81"
C_RED   = "#D94F3D"
C_AMBER = "#F5A623"
C_GREEN = "#2ECC71"
C_LIGHT = "#F2F6FC"
C_GREY  = "#6B7280"

print("=" * 60)
print("  SaaS Churn Prediction Model")
print("=" * 60)

# ── 1. LOAD ───────────────────────────────────────────────────────
print("\n[1/6] Loading data...")
df = pd.read_csv("/home/claude/customers.csv")
print(f"      {len(df):,} customers loaded")

# ── 2. FEATURE ENGINEERING ────────────────────────────────────────
print("\n[2/6] Engineering features...")

plan_tier = {"Starter": 1, "Professional": 2, "Business": 3, "Enterprise": 4}
df["plan_tier"]          = df["plan_name"].map(plan_tier)
df["is_annual"]          = (df["billing_cycle"] == "Annual").astype(int)
size_map = {"1-10": 5, "11-50": 25, "51-200": 100, "201-500": 350, "500+": 750}
df["company_size_n"]     = df["company_size"].map(size_map)
df["near_renewal"]       = df["tenure_months"].apply(lambda m: 1 if 10 <= m <= 14 else 0)
df["high_support"]       = (df["support_tickets"] > 3).astype(int)
df["high_churn_channel"] = df["acquisition_channel"].apply(
    lambda c: 1 if c in ("Paid Ads", "Social Media") else 0
)

features = [
    "usage_score",
    "plan_tier",
    "is_annual",
    "company_size_n",
    "monthly_price",
    "tenure_months",
    "support_tickets",
    "near_renewal",
    "high_support",
    "high_churn_channel",
]
print(f"      {len(features)} features engineered")

# ── 3. SPLIT ──────────────────────────────────────────────────────
print("\n[3/6] Train / test split (80/20)...")
X = df[features]
y = df["is_churned"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
scaler    = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)
print(f"      Train: {len(X_train):,}  |  Test: {len(X_test):,}")

# ── 4. TRAIN ──────────────────────────────────────────────────────
print("\n[4/6] Training model...")
model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
model.fit(X_train_s, y_train)
print("      Done ✓")

# ── 5. EVALUATE ───────────────────────────────────────────────────
print("\n[5/6] Evaluating...")
y_pred      = model.predict(X_test_s)
y_pred_prob = model.predict_proba(X_test_s)[:, 1]

accuracy  = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
auc       = roc_auc_score(y_test, y_pred_prob)
cm        = confusion_matrix(y_test, y_pred)

print(f"\n  Accuracy  : {accuracy*100:.1f}%")
print(f"  Precision : {precision*100:.1f}%")
print(f"  Recall    : {recall*100:.1f}%")
print(f"  F1 Score  : {f1*100:.1f}%")
print(f"  AUC-ROC   : {auc:.3f}")
print(f"\n  Confusion Matrix:")
print(f"                   Predicted No  Predicted Yes")
print(f"  Actual No              {cm[0][0]:>4}          {cm[0][1]:>4}")
print(f"  Actual Yes             {cm[1][0]:>4}          {cm[1][1]:>4}")

pd.DataFrame([
    {"metric": "Accuracy",  "value": round(accuracy,  4)},
    {"metric": "Precision", "value": round(precision, 4)},
    {"metric": "Recall",    "value": round(recall,    4)},
    {"metric": "F1 Score",  "value": round(f1,        4)},
    {"metric": "AUC-ROC",   "value": round(auc,       4)},
]).to_csv("/home/claude/sql_outputs/model_performance.csv", index=False)

# ── FEATURE IMPORTANCE ────────────────────────────────────────────
coef_df = pd.DataFrame({
    "feature":     features,
    "coefficient": model.coef_[0],
    "abs_impact":  abs(model.coef_[0])
}).sort_values("abs_impact", ascending=False)
coef_df["direction"] = coef_df["coefficient"].apply(
    lambda c: "Increases churn risk" if c > 0 else "Reduces churn risk"
)
print("\n  Feature Importance:")
for _, row in coef_df.iterrows():
    arrow = "▲" if row["coefficient"] > 0 else "▼"
    print(f"    {row['feature']:<25} {row['coefficient']:>+.4f}  {arrow}")
coef_df.to_csv("/home/claude/sql_outputs/feature_importance.csv", index=False)

# ── 6. SCORE ALL CUSTOMERS ────────────────────────────────────────
print("\n[6/6] Scoring all customers...")
X_all_s = scaler.transform(df[features])
df["churn_probability_pct"] = (model.predict_proba(X_all_s)[:, 1] * 100).round(1)
df["predicted_churn"]       = (df["churn_probability_pct"] >= 50).astype(int)
df["risk_band"] = pd.cut(
    df["churn_probability_pct"],
    bins=[0, 25, 50, 75, 100],
    labels=["Low (<25%)", "Medium (25-50%)", "High (50-75%)", "Critical (>75%)"]
)

out_cols = ["customer_id","plan_name","billing_cycle","industry",
            "usage_score","tenure_months","monthly_price","is_churned",
            "churn_probability_pct","predicted_churn","risk_band"]
df[out_cols].sort_values("churn_probability_pct", ascending=False)\
            .to_csv("/home/claude/sql_outputs/churn_predictions.csv", index=False)

active     = df[df["is_churned"] == 0]
band_stats = active["risk_band"].value_counts().sort_index()
print("\n  Active customers by risk band:")
for band, count in band_stats.items():
    pct = count / len(active) * 100
    bar = "█" * int(pct / 2)
    print(f"    {str(band):<22}  {count:>3} customers ({pct:.0f}%)  {bar}")

# ── CHARTS ────────────────────────────────────────────────────────
# Chart 1 — Confusion Matrix
fig, ax = plt.subplots(figsize=(6, 5))
fig.patch.set_facecolor(C_LIGHT)
ax.set_facecolor(C_LIGHT)
colors = [[C_GREEN, C_AMBER], [C_AMBER, C_BLUE]]
labels = [["True Negative", "False Positive"], ["False Negative", "True Positive"]]
for i in range(2):
    for j in range(2):
        ax.add_patch(plt.Rectangle((j, 1-i), 1, 1, color=colors[i][j], alpha=0.88))
        ax.text(j+0.5, 1-i+0.58, str(cm[i][j]),
                ha="center", va="center", fontsize=26, fontweight="bold", color="white")
        ax.text(j+0.5, 1-i+0.38, f"({cm[i][j]/cm.sum()*100:.1f}%)",
                ha="center", va="center", fontsize=11, color="white", alpha=0.9)
        ax.text(j+0.5, 1-i+0.20, labels[i][j],
                ha="center", va="center", fontsize=9, color="white", alpha=0.8,
                style="italic")
ax.set_xlim(0, 2); ax.set_ylim(0, 2)
ax.set_xticks([0.5, 1.5])
ax.set_xticklabels(["Predicted\nNot Churned", "Predicted\nChurned"],
                   fontsize=11, color=C_BLUE, fontweight="bold")
ax.set_yticks([0.5, 1.5])
ax.set_yticklabels(["Actual\nChurned", "Actual\nNot Churned"],
                   fontsize=11, color=C_BLUE, fontweight="bold", rotation=90, va="center")
ax.set_title("Churn Prediction — Confusion Matrix",
             fontsize=14, fontweight="bold", color=C_BLUE, pad=14)
ax.text(1.0, 2.07, f"AUC-ROC: {auc:.3f}   |   Accuracy: {accuracy*100:.1f}%   |   Recall: {recall*100:.1f}%",
        ha="center", fontsize=10, color=C_GREY)
ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
plt.tight_layout()
plt.savefig("/home/claude/sql_outputs/confusion_matrix.png",
            dpi=150, bbox_inches="tight", facecolor=C_LIGHT)
plt.close()

# Chart 2 — Feature Importance
fig, ax = plt.subplots(figsize=(9, 6))
fig.patch.set_facecolor(C_LIGHT); ax.set_facecolor(C_LIGHT)
plot_df    = coef_df.sort_values("coefficient")
bar_colors = [C_RED if c > 0 else C_BLUE for c in plot_df["coefficient"]]
bars = ax.barh(plot_df["feature"], plot_df["coefficient"],
               color=bar_colors, edgecolor="white", linewidth=0.4, height=0.62)
for bar, val in zip(bars, plot_df["coefficient"]):
    xp = val + 0.012 if val >= 0 else val - 0.012
    ha = "left"      if val >= 0 else "right"
    ax.text(xp, bar.get_y() + bar.get_height()/2,
            f"{val:+.3f}", va="center", ha=ha, fontsize=9, color=C_GREY)
ax.axvline(0, color=C_GREY, linewidth=1, linestyle="--", alpha=0.5)
ax.set_xlabel("Standardised Coefficient", fontsize=11, color=C_GREY)
ax.set_title("What Drives Churn? — Feature Importance",
             fontsize=14, fontweight="bold", color=C_BLUE, pad=14)
patches = [mpatches.Patch(color=C_RED,  label="▲ Increases churn risk"),
           mpatches.Patch(color=C_BLUE, label="▼ Reduces churn risk")]
ax.legend(handles=patches, fontsize=10, frameon=False, loc="lower right")
ax.tick_params(axis="y", labelsize=10, colors=C_BLUE)
ax.tick_params(axis="x", labelsize=9,  colors=C_GREY)
for s in ["top","right"]: ax.spines[s].set_visible(False)
ax.spines["left"].set_color(C_GREY); ax.spines["bottom"].set_color(C_GREY)
plt.tight_layout()
plt.savefig("/home/claude/sql_outputs/feature_importance.png",
            dpi=150, bbox_inches="tight", facecolor=C_LIGHT)
plt.close()

print("\n" + "=" * 60)
print("  All outputs saved to sql_outputs/")
print("=" * 60)
