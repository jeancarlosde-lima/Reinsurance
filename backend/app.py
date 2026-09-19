from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pandas as pd
import joblib
import os

app = FastAPI(title="Resseguro XL Agregado API")

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

# Carregamento do modelo de estresse climático em memória (inferência)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "cat_model.pkl")
cat_model_metadata = None

try:
    if os.path.exists(MODEL_PATH):
        cat_model_metadata = joblib.load(MODEL_PATH)
        print("Modelo de estresse climático carregado para inferência.")
except Exception as e:
    print(f"Erro ao carregar o modelo de estresse: {e}")


class SimulationRequest(BaseModel):
    # Prioridade e capacidade do XL AGREGADO, em milhões de R$, aplicadas ao
    # sinistro acumulado do ano inteiro da carteira (não a cada evento).
    prioridade: float = Field(ge=0)
    capacidade: float = Field(ge=0)
    # Taxa do contrato (rate on line): prêmio de resseguro como % da capacidade.
    # Sem custo, o resseguro sai de graça e prioridade zero com capacidade
    # infinita vira sempre a melhor escolha.
    taxa_rol: float = Field(default=10.0, ge=0, le=100)
    # UF é só o recorte de LEITURA. O contrato é um só, nacional: a UF recebe
    # a parcela que lhe cabe do resultado do tratado, nunca um tratado próprio.
    uf: str = "Todas"


def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'dados_resseguro.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError("Arquivo dados_resseguro.csv não encontrado. Rode susep_scraper.py primeiro.")

    df = pd.read_csv(csv_path)

    for col in ['Premio_Ganho', 'Sinistro_Bruto']:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    df['Premio_Ganho'] = df['Premio_Ganho'].astype('float64')
    df['Sinistro_Bruto'] = df['Sinistro_Bruto'].astype('float64')

    # A base aberta da SUSEP não traz "Prêmio Retido" pré-calculado.
    # Premissa: não há cessão proporcional antes do XL, então o prêmio retido
    # pela seguradora é o próprio prêmio ganho.
    if 'Premio_Retido' not in df.columns:
        df['Premio_Retido'] = df['Premio_Ganho']
    df['Premio_Retido'] = df['Premio_Retido'].astype('float64')

    if 'Ramo' in df.columns:
        df = df[df['Ramo'] == 11].copy()
    return df


def validar_uf(df, uf):
    if uf != "Todas" and uf not in set(df['UF']):
        raise HTTPException(status_code=404, detail=f"Sem dados para a UF {uf}")


@app.get("/api/calculate")
def calculate_xl_get(prioridade: float = 0.0, capacidade: float = 0.0, taxa_rol: float = 10.0, uf: str = "Todas"):
    req = SimulationRequest(prioridade=prioridade, capacidade=capacidade, taxa_rol=taxa_rol, uf=uf)
    return calculate_xl(req)


@app.post("/api/calculate")
def calculate_xl(req: SimulationRequest):
    try:
        df = load_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    validar_uf(df, req.uf)
    return process_resseguro_engine(df, req)


# Cenário extremo de El Niño usado no estresse
STRESS_ANOMALIA = 2.8             # ONI de El Niño muito forte
STRESS_PRECIPITACAO_SUL = 400.0   # excesso de chuva / granizo no Sul
# Fora do Sul, o gerador de treino (ml_engine.py) só modela o calor do El
# Niño; a chuva ali vai de 50 a 300 mm e não tem efeito. O valor antigo, 30 mm
# ("seca absoluta"), ficava fora dessa faixa e jogava esses estados no regime
# de seca que a árvore aprendeu com RS e PR — todos saíam com a mesma
# sinistralidade, acima do próprio Sul. Usamos o meio da faixa de treino.
STRESS_PRECIPITACAO_DEMAIS = 175.0


@app.post("/api/predict-stress")
def predict_stress_xl(req: SimulationRequest):
    """
    Recalcula a carteira sob um El Niño severo antes de aplicar o tratado.

    O modelo prevê a SINISTRALIDADE de cada linha, que é multiplicada pelo
    prêmio real. Prever o sinistro em reais fazia a Random Forest travar no
    teto da faixa de prêmio vista no treino — e os estados maiores (RS, PR),
    justamente os mais expostos ao granizo, quase não sofriam estresse.
    """
    if cat_model_metadata is None:
        raise HTTPException(status_code=503, detail="Modelo de estresse indisponível. Rode ml_engine.py primeiro.")

    try:
        df = load_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    validar_uf(df, req.uf)

    model = cat_model_metadata['model']
    features = cat_model_metadata['features']

    # O estresse é aplicado à carteira INTEIRA: o tratado é nacional, e o
    # recorte por UF só acontece depois, na leitura do resultado.
    X = pd.DataFrame({
        'Anomalia_El_Nino': STRESS_ANOMALIA,
        'Precipitacao_mm': df['UF'].map(
            lambda uf: STRESS_PRECIPITACAO_SUL if uf in ('RS', 'PR') else STRESS_PRECIPITACAO_DEMAIS
        ),
    }, index=df.index)
    for f in features:
        if f.startswith('UF_'):
            X[f] = (df['UF'] == f[3:]).astype(float)
    X = X[features]

    df = df.copy()
    df['Sinistro_Bruto'] = model.predict(X) * df['Premio_Ganho']

    return process_resseguro_engine(df, req)


def _ratio(num, den):
    return (num / den) * 100 if den > 0 else 0.0


def process_resseguro_engine(df, req):
    """
    XL Agregado (Aggregate Excess of Loss) sobre o ano da carteira.

    A prioridade e a capacidade valem para o sinistro ACUMULADO do período,
    não para cada evento — é o que separa este contrato de um XL catastrófico
    por evento.
    """
    prioridade = req.prioridade * 1_000_000
    capacidade = req.capacidade * 1_000_000

    premio_ganho = df['Premio_Ganho'].sum()
    premio_retido = df['Premio_Retido'].sum()
    sinistro_bruto = df['Sinistro_Bruto'].sum()

    # Motor XL: min(capacidade, max(0, sinistro - prioridade))
    recuperacao = min(capacidade, max(0.0, sinistro_bruto - prioridade))
    retencao = sinistro_bruto - recuperacao

    # Custo do contrato: taxa (rate on line) sobre a capacidade comprada
    premio_resseguro = (req.taxa_rol / 100) * capacidade
    premio_liquido = premio_retido - premio_resseguro

    resultado_sem_resseguro = premio_retido - sinistro_bruto
    resultado_com_resseguro = premio_liquido - retencao

    nacional = {
        "Premio_Total": float(premio_ganho),
        "Sinistro_Bruto": float(sinistro_bruto),
        "Recuperacao_RE": float(recuperacao),
        "Premio_Resseguro": float(premio_resseguro),
        "Retencao_Liquida": float(retencao),
        "Sinistralidade_Bruta": float(_ratio(sinistro_bruto, premio_ganho)),
        "Sinistralidade_Retida": float(_ratio(retencao, premio_liquido)),
        "Resultado_Sem_Resseguro": float(resultado_sem_resseguro),
        "Resultado_Com_Resseguro": float(resultado_com_resseguro),
        # Positivo: o contrato pagou mais do que custou nesse cenário
        "Beneficio_Resseguro": float(resultado_com_resseguro - resultado_sem_resseguro),
    }

    # Alocação do tratado nacional por UF: a recuperação é rateada pelo
    # sinistro e o custo do contrato, pelo prêmio de cada estado.
    por_uf = df.groupby('UF', as_index=False).agg(
        Premio_Ganho=('Premio_Ganho', 'sum'),
        Premio_Retido=('Premio_Retido', 'sum'),
        Sinistro_Bruto=('Sinistro_Bruto', 'sum'),
    )

    grafico = []
    alocacao = {}
    for _, row in por_uf.iterrows():
        peso_sinistro = row['Sinistro_Bruto'] / sinistro_bruto if sinistro_bruto > 0 else 0
        peso_premio = row['Premio_Retido'] / premio_retido if premio_retido > 0 else 0

        rec_uf = recuperacao * peso_sinistro
        custo_uf = premio_resseguro * peso_premio
        ret_uf = row['Sinistro_Bruto'] - rec_uf
        liquido_uf = row['Premio_Retido'] - custo_uf

        alocacao[row['UF']] = {
            "Premio_Total": float(row['Premio_Ganho']),
            "Sinistro_Bruto": float(row['Sinistro_Bruto']),
            "Recuperacao_RE": float(rec_uf),
            "Premio_Resseguro": float(custo_uf),
            "Retencao_Liquida": float(ret_uf),
            "Sinistralidade_Bruta": float(_ratio(row['Sinistro_Bruto'], row['Premio_Ganho'])),
            "Sinistralidade_Retida": float(_ratio(ret_uf, liquido_uf)),
            "Resultado_Sem_Resseguro": float(row['Premio_Retido'] - row['Sinistro_Bruto']),
            "Resultado_Com_Resseguro": float(liquido_uf - ret_uf),
            "Beneficio_Resseguro": float(rec_uf - custo_uf),
        }
        grafico.append({
            "uf": row['UF'],
            "sinistro_bruto": float(row['Sinistro_Bruto']),
            "recuperacao": float(rec_uf),
            "retencao": float(ret_uf),
        })

    visao = nacional if req.uf == "Todas" else alocacao[req.uf]

    return {
        **visao,
        "escopo": req.uf,
        "contrato": nacional,
        "grafico": grafico,
    }
