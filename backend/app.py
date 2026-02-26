from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import os

app = FastAPI(title="Resseguro XL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def read_root():
    return FileResponse('frontend/index.html')

# Carregamento do Single Pipeline de MLOps na base memory (Otimização para inferência)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "cat_model.pkl")
cat_model_metadata = None

try:
    if os.path.exists(MODEL_PATH):
        cat_model_metadata = joblib.load(MODEL_PATH)
        print("MLOps Pipeline (Cat Model) carregado com sucesso para Inferência.")
except Exception as e:
    print(f"Erro ao carregar modelo MLOps: {e}")

class SimulationRequest(BaseModel):
    prioridade: float
    capacidade: float
    uf: str = "Todas"

def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'dados_resseguro.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError("Arquivo dados_resseguro.csv não encontrado. Rode data_generator.py primeiro.")
    
    df = pd.read_csv(csv_path)
    
    for col in ['Premio_Ganho', 'Sinistro_Bruto']:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
            
    df['Premio_Ganho'] = df['Premio_Ganho'].astype('float64')
    df['Sinistro_Bruto'] = df['Sinistro_Bruto'].astype('float64')
    
    # O dataset real da Susep não possui "Prêmio Retido" pré-calculado na base aberta.
    # Assumimos que o volume total de Prêmio Ganho no estado é a base da retenção primária.
    if 'Premio_Retido' not in df.columns:
        df['Premio_Retido'] = df['Premio_Ganho']
    df['Premio_Retido'] = df['Premio_Retido'].astype('float64')
    
    # O novo susep_scraper.py já traz o Dataset limpo exclusivamente para o Ramo 11
    if 'Ramo' in df.columns:
        df = df[df['Ramo'] == 11].copy()
    return df

@app.get("/api/calculate")
def calculate_xl_get(prioridade: float = 0.0, capacidade: float = 0.0, uf: str = "Todas"):
    # Corrigido o nome dos parâmetros para o padrão pt-BR
    req = SimulationRequest(prioridade=prioridade, capacidade=capacidade, uf=uf)
    return calculate_xl(req)

@app.post("/api/calculate")
def calculate_xl(req: SimulationRequest):
    try:
        df = load_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if req.uf != "Todas":
        df = df[df['UF'] == req.uf].copy()
        
    if df.empty:
        return {"error": "Sem dados para o filtro"}
        
    return process_resseguro_engine(df, req)

@app.post("/api/predict-stress")
def predict_stress_xl(req: SimulationRequest):
    """
    Simula cenário severo de El Niño usando ML Predictor antes de calcular Resseguro.
    Essa Rota de MLOps utiliza o classificador para inflar dados de Sinistro.
    """
    if cat_model_metadata is None:
        raise HTTPException(status_code=503, detail="Modelo Preditivo Offline indisponível. Treine-o primeiro.")
        
    try:
        df = load_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if req.uf != "Todas":
        df = df[df['UF'] == req.uf].copy()
        
    if df.empty:
        return {"error": "Sem dados para o filtro"}
        
    # Variáveis Extremas Simuladas para o Cenário "El Niño"
    STRESS_ANOMALIA = 2.8 # Super El Nino
    STRESS_PRECIPITACAO_SUL = 400.0 # Diluvio / Granizo
    STRESS_PRECIPITACAO_NORTE = 30.0 # Seca Absoluta
    
    # Vamos gerar predições para cada grupo de uf da tabela real
    model = cat_model_metadata['model']
    features = cat_model_metadata['features']
    
    # Adicionando predição de sinistro linha a linha no dataset original
    for idx, row in df.iterrows():
        uf = row['UF']
        premio_ganho = float(row['Premio_Ganho'])
        
        precipitacao = STRESS_PRECIPITACAO_SUL if uf in ['RS', 'PR'] else STRESS_PRECIPITACAO_NORTE
        
        # Cria vetor X unitário compatível com o Schema que a RandomForest aprendeu
        x_dict = {
            'Premio_Ganho': premio_ganho,
            'Anomalia_El_Nino': STRESS_ANOMALIA,
            'Precipitacao_mm': precipitacao
        }
        
        # O modelo usou One-Hot Encoding das UFs no Dataset de Treino (pd.get_dummies).
        # Devemos criar Dummies dinâmicos preenchendo as Features ausentes com Zero
        for f in features:
            if f.startswith('UF_'):
                x_dict[f] = 1.0 if f"UF_{uf}" == f else 0.0
                
        # Garante que o DataFrame final tenha exatamente as colunas e ordem do Treino
        X_infer = pd.DataFrame([x_dict])[features]
        predicted_sinistro = model.predict(X_infer)[0]
        
        # Injeta o valor predito pela Inteligência Artificial no lugar do Sinistro Real!
        df.loc[idx, 'Sinistro_Bruto'] = predicted_sinistro
        
    # Com os danos bilionários já engatilhados no DataFrame, a matemática de Resseguro XL assume:
    return process_resseguro_engine(df, req)
    
def process_resseguro_engine(df, req):
    """
    Engenharia Matemátiaca Extraída do Escopo Principal 
    para Reuso Arquitetural em Rotas Tradicionais e Rotas MLOps.
    """
    premio_ganho_total = df['Premio_Ganho'].sum()
    premio_retido_total = df['Premio_Retido'].sum()
    sinistro_bruto_total = df['Sinistro_Bruto'].sum()
    
    # MULTIPLICADOR DE ESCALA: Transforma o input da UI em Milhões
    prioridade_real = req.prioridade * 1_000_000
    capacidade_real = req.capacidade * 1_000_000
    
    sinistralidade_bruta = (sinistro_bruto_total / premio_ganho_total) * 100 if premio_ganho_total > 0 else 0
    
    # Motor XL aplicando a regra exata
    recuperacao_resseguro = max(0.0, min(sinistro_bruto_total - prioridade_real, capacidade_real))
    retencao_liquida = sinistro_bruto_total - recuperacao_resseguro
    
    sinistralidade_retida = (retencao_liquida / premio_retido_total) * 100 if premio_retido_total > 0 else 0
    
    uf_data = []
    df_uf = df.groupby('UF', as_index=False).agg({'Sinistro_Bruto': 'sum'})
    
    for _, row in df_uf.iterrows():
        uf_sigla = row['UF']
        s_bruto = row['Sinistro_Bruto']
        
        peso = (s_bruto / sinistro_bruto_total) if sinistro_bruto_total > 0 else 0
        recuperacao_uf = recuperacao_resseguro * peso
        retencao_uf = s_bruto - recuperacao_uf
        
        uf_data.append({
            "uf": uf_sigla,
            "sinistro_bruto": float(s_bruto),
            "recuperacao": float(recuperacao_uf),
            "retencao": float(retencao_uf)
        })
        
    return {
        "Premio_Total": float(premio_ganho_total),
        "Sinistro_Bruto": float(sinistro_bruto_total),
        "Recuperacao_RE": float(recuperacao_resseguro),
        "Retencao_Liquida": float(retencao_liquida),
        "Sinistralidade_Retida": float(sinistralidade_retida),
        "grafico": uf_data
    }