<div align="center">

# 📊 Simulador de Resseguro — XL Agregado (Aggregate Excess of Loss)

**Carteira de Seguro Rural (Grupo 11) · Subscrição e Engenharia de Dados**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![scikit-learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

</div>

---

## 🎯 1. O que é

Simulador de um contrato de **Excesso de Danos Agregado** para uma carteira de seguro rural. O subscritor define a prioridade, a capacidade e a taxa do contrato e vê, em tempo real, quanto o resseguro recupera, quanto ele custa e como fica a sinistralidade líquida da seguradora — num ano normal e num ano de El Niño severo, projetado por um modelo de machine learning.

**Por que "agregado":** a prioridade e o limite valem para o sinistro **acumulado do ano** da carteira, não para cada evento. É o mesmo desenho de um Stop Loss em valor, e é diferente de um XL catastrófico por evento, em que a prioridade se aplica a cada ocorrência.

```
Recuperação   = min(Capacidade, max(0, Sinistro anual − Prioridade))
Custo         = Taxa (rate on line) × Capacidade
Resultado     = Prêmio retido − Custo − (Sinistro − Recuperação)
Benefício     = Resultado com resseguro − Resultado sem resseguro
```

---

## 💻 2. Interface

### 2.1. Controles
- **Prioridade agregada anual (R$ milhões)** — o simulador mostra a equivalência em sinistralidade da carteira (ex.: R$ 8.300 mi ≈ 85% de sinistralidade).
- **Capacidade da camada (R$ milhões)** — em pontos de sinistralidade acima da prioridade.
- **Taxa do contrato (rate on line)** — prêmio de resseguro como % da capacidade comprada. É o que dá sentido à escolha: sem custo, prioridade zero e capacidade infinita seriam sempre a melhor opção.
- **Recorte de leitura (UF)** — o contrato é **um só, nacional**. Ao escolher uma UF, o painel mostra a parcela dela no resultado do contrato — nunca um tratado próprio para o estado.
- **Estresse climático (ML)** — recalcula a carteira sob um El Niño severo antes de aplicar o contrato.

### 2.2. Indicadores
- **Sinistro Bruto**, com a sinistralidade bruta.
- **Recuperação do Resseguro**.
- **Custo do Resseguro**, com o **benefício** do contrato no cenário: negativo num ano bom (é o preço da proteção), positivo quando a camada é acionada.
- **Retenção Líquida**, com a sinistralidade líquida (sobre o prêmio líquido do custo do resseguro) e alerta acima de 80%.
- **Gráfico por UF** — a recuperação do contrato nacional é rateada pelo sinistro de cada estado; o custo, pelo prêmio.

### 2.3. O que o simulador mostra com os parâmetros padrão

| Cenário | Sinistralidade | Recupera | Custa | Benefício | Sinistralidade líquida |
|---|---|---|---|---|---|
| Ano normal | 81,6% | R$ 0 | R$ 290 mi | −R$ 290 mi | 84,1% |
| El Niño severo | 132,3% | R$ 2,90 bi | R$ 290 mi | +R$ 2,61 bi | 105,7% |

Prioridade R$ 8.300 mi (≈ 85% de sinistralidade), capacidade R$ 2.900 mi, taxa de 10%.

---

## 🏗️ 3. Arquitetura

### 3.1. Backend (Python)
- **`backend/susep_scraper.py`** — tenta baixar a base aberta de estatísticas da SUSEP e filtrar o grupo rural; se o portal estiver indisponível, gera uma carteira paramétrica com a participação aproximada de cada UF no prêmio agrícola.
- **`backend/ml_engine.py`** — treina uma `RandomForestRegressor` sobre dados climáticos sintéticos (anomalia do El Niño, precipitação e UF) e exporta `cat_model.pkl`. O alvo é a **sinistralidade**, não o sinistro em reais (ver seção 4).
- **`backend/app.py`** — API em **FastAPI**:
  - `POST /api/calculate` — aplica o contrato à carteira.
  - `POST /api/predict-stress` — projeta a sinistralidade de cada linha sob El Niño severo, multiplica pelo prêmio real e aplica o contrato.
  - `GET /` — serve o painel.

### 3.2. Frontend (JavaScript puro)
- **`frontend/app.js`** — estado, rede e interface separados, com *debounce* nas entradas e **Chart.js** no gráfico por UF.

---

## 🔧 4. Correções de lógica de resseguro

Revisão feita sobre a primeira versão. Cada item foi medido antes e depois.

**1. O estresse climático quase não atingia os estados mais expostos.**
O modelo previa o sinistro em reais usando o prêmio como variável. O treino só via prêmios de R$ 10 mi a R$ 100 mi por mês, mas o RS tem R$ 274 mi — e árvore de decisão não extrapola: a previsão travava em R$ 153 mi, qualquer que fosse o prêmio. No cenário de granizo no Sul, o RS ia de 52% para só 56% de sinistralidade, enquanto SP ia para 198%.
Além disso, os estados fora do Sul recebiam 30 mm de chuva, abaixo da faixa de treino deles (50–300 mm), e caíam no regime de seca aprendido com RS e PR.
→ O modelo passou a prever a **sinistralidade**, multiplicada pelo prêmio real, e o cenário usa entradas dentro da faixa de treino. Agora: **RS e PR ≈ 152%** (granizo), demais estados **≈ 103%** (calor).

**2. O resseguro saía de graça.**
Sem prêmio de resseguro, prioridade zero e capacidade infinita eram sempre a melhor escolha, e o simulador não mostrava o equilíbrio entre prioridade e capacidade.
→ Entrou a **taxa do contrato (rate on line)**, com custo, resultado líquido e benefício. Com prioridade zero e capacidade ilimitada, num ano normal, o contrato agora custa mais do que recupera.

**3. O filtro por UF mudava o contrato.**
Na visão nacional, a recuperação era rateada entre os estados; ao filtrar uma UF, a prioridade e o limite inteiros eram reaplicados só a ela — dois contratos diferentes para a mesma leitura.
→ O contrato é sempre nacional e a UF recebe a sua parcela. A soma das parcelas bate exatamente com o total nacional.

**4. O nome não correspondia ao contrato.**
A prioridade é aplicada ao sinistro anual acumulado, o que é um **XL agregado** — não um XL catastrófico por evento, como os rótulos anteriores sugeriam.
→ Nomes, textos e valores padrão ajustados. Os padrões antigos (prioridade de R$ 20 mi e capacidade de R$ 50 mi numa carteira com R$ 7,9 bi de sinistro anual) consumiam a camada inteira em qualquer cenário.

---

## ⚠️ 5. Premissas e limitações

- A carteira usada é **paramétrica** (fallback do scraper), com proporções aproximadas de mercado — não é a base oficial da SUSEP.
- O modelo climático é treinado em **dados sintéticos**; ele demonstra o método, não substitui um modelo catastrófico calibrado.
- Não há cessão proporcional antes do XL: o prêmio retido é igual ao prêmio ganho.
- Sem reintegrações (reinstatements) e sem cláusula de participação nos lucros.
- No caminho de dados reais da SUSEP, o mapeamento de colunas ainda precisa ser validado contra o dicionário oficial da base.

---

## 🚀 6. Como rodar

### Localmente
```powershell
pip install -r requirements.txt
python backend/ml_engine.py        # (re)treina o modelo de estresse
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Acesse `http://localhost:8000/`.

### Deploy no Render.com
1. Crie um Web Service ligado a este repositório.
2. **Environment:** `Python 3` · **Build Command:** `pip install -r requirements.txt` · **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
