import pandas as pd
import plotly.express as px

# --- Change this path to your file ---
file_path = "portfolio.csv"  # or "portfolio.xlsx"

# Automatically handle CSV or Excel
if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
elif file_path.endswith(".xlsx"):
    df = pd.read_excel(file_path)
else:
    raise ValueError("File must be a .csv or .xlsx")

# ---- 2️⃣ Validate and clean data ----
required_cols = {"Category", "Subcategory", "Asset", "Value"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"Input file must contain columns: {required_cols}")

df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

# ---- 3️⃣ Compute summaries ----
summary = (
    df.groupby(["Category", "Subcategory"], as_index=False)["Value"]
    .sum()
    .sort_values("Value", ascending=False)
)
summary["% of Total"] = 100 * summary["Value"] / summary["Value"].sum()

print("\nHierarchical Portfolio Allocation:\n")
print(summary.to_string(index=False))

# ---- 4️⃣ Visualize hierarchy ----
fig = px.sunburst(
    df,
    path=["Category", "Subcategory", "Asset"],
    values="Value",
    title="Portfolio Allocation Hierarchy",
)
fig.update_traces(textinfo="label+percent entry")
fig.show()
