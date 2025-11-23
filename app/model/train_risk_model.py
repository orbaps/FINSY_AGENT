# app/train_risk_model.py
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

# create synthetic dataset
def gen_data(n=1000):
    import random
    rows = []
    for i in range(n):
        amount = random.uniform(100, 200000)
        has_po = random.choice([0,1])
        vendor_suspicious = random.choices([0,1],[0.95,0.05])[0]
        # label: fraud if amount large and vendor suspicious or missing PO
        label = 1 if (amount>50000 and vendor_suspicious==1) or (has_po==0 and amount>10000) else 0
        rows.append([amount, has_po, vendor_suspicious, label])
    df = pd.DataFrame(rows, columns=['amount','has_po','vendor_suspicious','label'])
    return df

def train_and_save(out_path="app/models/risk_model.pkl"):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df = gen_data(1500)
    X = df[['amount','has_po','vendor_suspicious']]
    y = df['label']
    # scale amount
    scaler = StandardScaler()
    X_scaled = X.copy()
    X_scaled['amount'] = scaler.fit_transform(X[['amount']])
    model = LogisticRegression()
    model.fit(X_scaled, y)
    # store both model and scaler as tuple
    joblib.dump((model, scaler), out_path)
    print("Saved model to", out_path)

if __name__ == "__main__":
    train_and_save()
