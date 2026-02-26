import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "cat_model.pkl")

def generate_synthetic_climate_data(n_samples=5000):
    """
    Gera um dataset sintético para treinar o modelo de Machine Learning.
    Relaciona a gravidade climática (El Nino / Precipitação) com o aumento
    percentual ou absoluto da Sinistralidade (Ramo 11).
    """
    print("Gerando features climáticas sintéticas...")
    np.random.seed(42)
    
    # UFs com maior representatividade no Agro
    ufs = ['RS', 'PR', 'SP', 'MG', 'MT', 'GO', 'MS']
    
    data = []
    for _ in range(n_samples):
        uf = np.random.choice(ufs, p=[0.35, 0.25, 0.15, 0.10, 0.08, 0.05, 0.02])
        
        # Oceanic Niño Index (ONI) - mede a anomalia da temperatura da água
        # Valores de -2 (La Nina Forte) a +3.0 (El Nino Muito Forte)
        anomalia_el_nino = np.random.uniform(-2.5, 3.0)
        
        # Precipitacao Media Mensal (mm). Varia muito com El Nino / La Nina dependo da UF
        # Sul sofre seca (baixa chuva) em La Nina, e chuvas torrenciais (pedra/granizo) no El Nino
        if uf in ['RS', 'PR']:
            if anomalia_el_nino > 1.5: # El Nino forte (Granizo)
                precipitacao_mm = np.random.uniform(200, 450)
            elif anomalia_el_nino < -1.0: # La Nina forte (Seca)
                precipitacao_mm = np.random.uniform(10, 80)
            else: # Neutro
                precipitacao_mm = np.random.uniform(90, 180)
        else:
            precipitacao_mm = np.random.uniform(50, 300)
            
        # Prêmio Ganho Base (Milhoes ficticios pro modelo aprender a relacao)
        premio_base = np.random.uniform(10_000_000, 100_000_000)
        
        # Sinistro Bruto (A variavel Alvo 'Y')
        # Historicamente base de 60%.  Mas clima extremo joga pra cima de 150% a 400%
        base_loss_ratio = np.random.uniform(0.5, 0.75)
        
        # Impacto Climatico (Feature Engineering)
        stress_factor = 1.0
        if uf in ['RS', 'PR']:
            if precipitacao_mm < 50: # Seca severa
                stress_factor = np.random.uniform(2.0, 4.5)
            elif precipitacao_mm > 350: # Excesso de chuva / granizo
                stress_factor = np.random.uniform(1.8, 3.5)
        elif anomalia_el_nino > 2.0: # Calor extremo no meio oeste
             stress_factor = np.random.uniform(1.3, 2.0)
             
        sinistro_bruto = premio_base * (base_loss_ratio * stress_factor)
        
        data.append({
            'UF': uf,
            'Premio_Ganho': premio_base,
            'Anomalia_El_Nino': anomalia_el_nino,
            'Precipitacao_mm': precipitacao_mm,
            'Sinistro_Bruto': sinistro_bruto
        })
        
    df = pd.DataFrame(data)
    
    # Feature Encoding para a Random Forest (One-Hot do Estado Categorico)
    df = pd.get_dummies(df, columns=['UF'], drop_first=True)
    return df

def train_and_export_model():
    print("\n--- Iniciando Pipeline de MLOps (Catastrophe Modeling) ---")
    df = generate_synthetic_climate_data(n_samples=10000)
    
    # Separando Features (X) e Target (y)
    # y = Sinistro_Bruto. Note que o modelo usará UF, Anomalia, Precipitacao E Premio_Ganho para prever.
    X = df.drop(columns=['Sinistro_Bruto'])
    y = df['Sinistro_Bruto']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"Treinando RandomForestRegressor com {len(X_train)} amostras...")
    # O Random Forest é ótimo porque capta relações não lineares (como o "meio termo" de chuvas ser bom, e os extremos ruins)
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    
    model.fit(X_train, y_train)
    
    print("Avaliando o modelo (Test Set):")
    predictions = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    
    print(f" - RMSE (Erro Médio): {rmse:,.2f}")
    print(f" - R² Score: {r2:.4f}")
    
    # Salva o pipeline pre-treinado junto com as colunas pra garantir o fit do schema
    metadata = {
        'model': model,
        'features': list(X.columns)
    }
    
    print(f"\nPersistindo artefato binário do modelo em: {MODEL_PATH}")
    joblib.dump(metadata, MODEL_PATH)
    print("--- Treinamento Concluído com Sucesso ---")

if __name__ == "__main__":
    train_and_export_model()
