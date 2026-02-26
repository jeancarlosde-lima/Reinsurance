# Simulador de Tratado de Resseguro XL (Excess of Loss)
**Diretoria de Subscrição & Engenharia de Dados**

---

## 1. Proposta Executiva e Visão Geral
Este repositório contém o código-fonte do **Simulador de Exposição e Retenção de Resseguro (Modelo Não-Proporcional XL)**, focado nas carteiras agrícolas do Ramo 11 (Seguros Rurais). 

A proposta central do sistema é fornecer uma **ferramenta analítica de nível institucional (Enterprise)** para subscritores de risco e atuários. O sistema permite testar, em tempo real, o impacto financeiro de diferentes cenários de estruturação de contratos de resseguro, avaliando o balanço entre **Prioridade (Franquia Agregada)** e **Capacidade (Limite Restritivo)**. Além disso, o sistema integra inteligência artificial para simular o comportamento da carteira e a sinistralidade sob estresse climático extremo.

---

## 2. Interface do Usuário: Telas e Funcionalidades

A aplicação possui uma única página de interface rica (Single Page Application - SPA), operando como um **Enterprise Analytics Dashboard**.

### 2.1. Painel de Controle (Sidebar Lateral)
Localizado à esquerda, é o centro de comando do simulador:
- **Prioridade / Franquia (em Milhões R$)**: Campo numérico de entrada onde o atuário define o valor inicial a partir do qual o ressegurador começa a assumir os custos de sinistros.
- **Capacidade / Limite (em Milhões R$)**: Campo numérico de entrada que estipula o teto (limite máximo) de cobertura financeira oferecido pelo tratado de resseguro.
- **Unidade Federativa (Agregação)**: Menu suspenso (dropdown) permitindo filtrar as análises financeiras por estado específico da federação, ou visualizar a exposição global agregada em nível nacional.
- **Toggle de Machine Learning (Catastrophe Modeling)**: Interruptor dinâmico que ativa o modelo de inteligência artificial preditivo. Quando acionado, injeta um cenário catastrófico severo de El Niño, altera o painel visual para o estado de alerta (*Warning Mode*) e recalcula a carteira com base nas inferências e picos de severidade de sinistralidade.

### 2.2. Painel de Visualização (Main Dashboard)
Localizado à direita, exibe fluidamente os resultados dos cálculos atuariais e cenários (*Hot-Reload*):
- **KPI - Sinistro Bruto (Loss Ratio)**: Consolida o montante total de perdas geradas pela carteira, advindos das bases oficiais in-memory ou inflados pelo disparo preditivo da IA.
- **KPI - Retenção Líquida (Seguradora)**: Apresenta o custo retido pela própria seguradora primária (prejuízo final) após o repasse para o ressegurador. 
  - *Smart Alert Box*: A área do KPI se transmuta alertando perigo vermelho (*Danger Red*) automaticamente via CSS se o índice de Sinistralidade Retida ultrapassar a meta limite atuária de 80%.
- **KPI - Recuperação RE (Cessão)**: Exibe a parcela financeira capitalizada da resseguradora em observância aos tetos restritivos de Prioridade e Capacidade.
- **Gráfico de Exposição Financeira (Chart.js)**: Painel gráfico de barras empilhadas que disseca, por estado contábil (UF), o balanceamento de reponsabilidade entre a companhia seguradora primária (fatia reta em vermelho institucional) e a proteção do resseguro XL repassado (fatia top em azul corporativo).

---

## 3. Arquitetura Analítica e Componentes Técnicos

O software opera como um ecossistema *Fullstack* lastreado em infraestrutura Python de backend e JavaScript reativo no frontend.

### 3.1. Arquitetura Backend Integrado e MLOps (Python)
- **`susep_scraper.py`**: Motor robótico de ETL (Webscraping). Realiza download volumétrico, abstração e *parsing* da fonte de dados abertos federais da autarquia SUSEP. Conta com algoritmo paramétrico mitigatório de market-share em caso de indisponibilidade da API governamental.
- **`ml_engine.py`**: Estágio fundacional de Machine Learning (MLOps). Elabora a engenharia de descritores contextuais de meteorologia extrema simulada (Anomalias El Niño/Secas Globais) treinando um algoritmo nativo de regressores florestais randômicos (`sklearn.ensemble.RandomForestRegressor`). Após convergência, materializa e exporta o *artifact model* serializado (`cat_model.pkl`).
- **`app.py`**: Hub REST transacional montado em FastAPI lidando com DataFrames em memória:
  - **Rota Padrão (`/api/calculate`)**: Avalia a matemática de excesso de perda linear cruzando inputs frontends X CSV do Scraper.
  - **Rota Preditiva (`/api/predict-stress`)**: Utiliza o *Pickle* de Machine Learning em modalidade inferência. Promove um choque paramétrico exógeno projetando o Sinistro Bruto com cenários de precipitação extrema ou secas agudas previamente à contabilidade dos tratos XL.
  - *Equação Atuarial Nativa:* $$Recuperação = \min(Capacidade, \max(0, Sinistro Total - Prioridade))$$

### 3.2. Engenharia de Frontend (Vanilla JS / CSS Moderno)
- **`index.html` e `style.css`**: Design system sofisticado edificado em paletas Dark Theme com alto contraste para mitigação de fadiga visual, usando CSS Flexbox/Grid e injeções de SVG interativos.
- **`app.js`**: Controlador de interface implementando Padrão Modular (State/Networking/UI Controller). Faz uso proeminente de um agendador Assíncrono com técnica de Debounce (350ms) absorvendo estresse de repetições sequenciais *on-typing* enviando apenas um único HTTP Payload estruturado. O pacote *Chart.js* é manipulado reativamente por injetores DOM de destruição e reescrita performáticos sem travar a thread.

---

## 4. Guia Definitivo de Implantação e Deploy

### 📋 Pré-Requisitos Sistêmicos
- Instalação Operacional Python 3.9+ 
- Distribuição Pip: `pip install fastapi uvicorn pandas pydantic scikit-learn joblib beautifulsoup4 requests`

### ▶️ Passo 1: Disparo do Backend (Pipeline Atuarial & Datasets)
1. Instancie o acesso ao prompt de comando, focando no subdiretório raiz do motor: `cd backend`.
2. Puxe toda a governança e históricos analíticos governamentais recém formatados pela rotina de raspagem: `python susep_scraper.py`.
3. *(Opcional)* Refaça as métricas de ensaio do simulador paramétrico climatológico acionando a engenharia de treino (irá sobreescrever `cat_model.pkl`): `python ml_engine.py`.
4. Levante a interface Socket Atuarial FastAPI na localnet 8000:
   ```powershell
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

### ▶️ Passo 2: Execução de Console Dashboard (Visual Client)
1. Estabeleça uma segunda janela isolada do terminal mirando diretório alvo: `cd frontend`.
2. Providencie a ativação de um módulo iterativo web HTTP puro (SingleThread mode):
   ```powershell
   python -m http.server 5500
   ```
3. A estação base de Análise Corporativa estará sintonizada, visível e online a partir do URI padrão em seu navegador de preferência: **`http://localhost:5500`**.
