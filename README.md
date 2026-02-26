<div align="center">
  
# 📊 Simulador de Tratado de Resseguro XL (Excess of Loss)

**Diretoria de Subscrição & Engenharia de Dados**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![scikit-learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)

</div>

---

## 🎯 1. Proposta Executiva e Visão Geral
Este repositório contém o código-fonte do **Simulador de Exposição e Retenção de Resseguro (Modelo Não-Proporcional XL)**, focado nas carteiras agrícolas do Ramo 11 (Seguros Rurais). 

A proposta central do sistema é fornecer uma **ferramenta analítica de nível institucional (Enterprise)** para subscritores de risco e atuários. O sistema permite testar, em tempo real, o impacto financeiro de diferentes cenários de estruturação de contratos de resseguro, avaliando o balanço entre **Prioridade (Franquia Agregada)** e **Capacidade (Limite Restritivo)**. Além disso, o sistema integra inteligência artificial para simular o comportamento da carteira e a sinistralidade sob estresse climático extremo.

---

## 💻 2. Interface do Usuário: Telas e Funcionalidades

A aplicação possui uma única página de interface rica (Single Page Application - SPA), operando como um **Enterprise Analytics Dashboard**.

### ⚙️ 2.1. Painel de Controle (Sidebar Lateral)
Localizado à esquerda, é o centro de comando do simulador:
- **Prioridade / Franquia (em Milhões R$)**: Campo numérico de entrada onde o atuário define o valor inicial a partir do qual o ressegurador começa a assumir os custos de sinistros.
- **Capacidade / Limite (em Milhões R$)**: Campo numérico de entrada que estipula o teto (limite máximo) de cobertura financeira oferecido pelo tratado de resseguro.
- **Unidade Federativa (Agregação)**: Menu suspenso (dropdown) permitindo filtrar as análises financeiras por estado específico da federação, ou visualizar a exposição global agregada em nível nacional.
- **Toggle de Machine Learning (Catastrophe Modeling)**: Interruptor dinâmico que ativa o modelo de inteligência artificial preditivo. Quando acionado, injeta um cenário catastrófico severo de El Niño, altera o painel visual para o estado de alerta (*Warning Mode*) e recalcula a carteira com base nas inferências e picos de severidade de sinistralidade.

### 📈 2.2. Painel de Visualização (Main Dashboard)
Localizado à direita, exibe fluidamente os resultados dos cálculos atuariais e cenários (*Hot-Reload*):
- **KPI - Sinistro Bruto (Loss Ratio)**: Consolida o montante total de perdas geradas pela carteira, advindos das bases oficiais in-memory ou inflados pelo disparo preditivo da IA.
- **KPI - Retenção Líquida (Seguradora)**: Apresenta o custo retido pela própria seguradora primária (prejuízo final) após o repasse para o ressegurador. 
  - *Smart Alert Box*: A área do KPI se transmuta alertando perigo vermelho (*Danger Red*) automaticamente via CSS se o índice de Sinistralidade Retida ultrapassar a meta limite atuária de 80%.
- **KPI - Recuperação RE (Cessão)**: Exibe a parcela financeira capitalizada da resseguradora em observância aos tetos restritivos de Prioridade e Capacidade.
- **Gráfico de Exposição Financeira (Chart.js)**: Painel gráfico de barras empilhadas que disseca, por estado contábil (UF), o balanceamento de reponsabilidade entre a companhia seguradora primária (fatia reta em vermelho institucional) e a proteção do resseguro XL repassado (fatia top em azul corporativo).

---

## 🏗️ 3. Arquitetura Analítica e Componentes Técnicos

O software opera como um ecossistema *Fullstack* lastreado em infraestrutura Python de backend e JavaScript reativo no frontend, agora servido em modo consolidado.

### 🐍 3.1. Arquitetura Backend Integrado e MLOps (Python)
- **`/backend/susep_scraper.py`**: Motor robótico de ETL (Webscraping). Realiza download volumétrico, abstração e *parsing* da fonte de dados abertos federais da autarquia SUSEP. 
- **`/backend/ml_engine.py`**: Estágio fundacional de Machine Learning (MLOps). Elabora a engenharia de descritores contextuais de meteorologia extrema simulada treinando um algoritmo nativo de regressores florestais randômicos (`RandomForestRegressor`). Após convergência, exporta o *artifact model* serializado (`cat_model.pkl`).
- **`/backend/app.py`**: Hub REST transacional montado em **FastAPI** lidando com DataFrames em memória:
  - **Rota Padrão (`/api/calculate`)**: Avalia a matemática de excesso de perda linear cruzando inputs frontends X CSV do Scraper.
  - **Rota Preditiva (`/api/predict-stress`)**: Utiliza o modelo preditivo para inflar o Sinistro Bruto com cenários climáticos severos.
  - **Rota de Estáticos (`/`)**: Carrega e serve nativamente a interface do Dashboard via `StaticFiles`.
  - *Equação Atuarial Nativa:* $$Recuperação = \min(Capacidade, \max(0, Sinistro Total - Prioridade))$$

### 🎨 3.2. Engenharia de Frontend (Vanilla JS / CSS Moderno)
- **`/frontend/index.html` e `style.css`**: Design system sofisticado edificado em paletas Dark Theme com alto contraste para mitigação de fadiga visual, usando CSS Flexbox/Grid e injeções de SVG interativos.
- **`/frontend/app.js`**: Controlador de interface implementando Padrão Modular (State/Networking/UI Controller) com um agendador de *Debounce* otimizado enviando *Single HTTP Payloads*. Utiliza dinamicamente a biblioteca **Chart.js** no canvas visual.

---

## 🚀 4. Guia de Implantação e Render Deploy

O projeto foi consolidado para simplificar implantações em nuvem (ex: Render, Heroku, Railway) com `requirements.txt` estrututado na raiz do repositório.

### ☁️ Como Fazer o Deploy no Render.com

1. Crie um novo Web Service ligado ao seu repositório no GitHub.
2. Defina os seguintes parâmetros na interface gráfica do Render:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
3. A aplicação executará o FastAPI servindo o JSON do Backend juntamente com todo o HTML/JS/CSS da pasta Frontend sob a mesma porta.

### 💻 Como Rodar Localmente

1. Navegue pelo terminal até a pasta raiz `resseguro-xl-analytics`.
2. Instale as dependências executando:
   ```powershell
   pip install -r requirements.txt
   ```
3. Suba o servidor com o uvicorn nativo ativando o backend e o frontend vinculados simultaneamente:
   ```powershell
   uvicorn backend.app:app --host 0.0.0.0 --port 8000
   ```
4. Acesse seu dashboard local via `http://localhost:8000/`.
