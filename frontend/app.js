/**
 * @file app.js
 * @description Advanced Institutional Reinsurance Dashboard Controller
 * Arquitetura: Module Pattern (State, Network, UI, ChartFactory)
 */

// --- 1. UTILITIES & CONFIGURATIONS ---
const CONFIG = {
    API_URL_NORMAL: '/api/calculate',
    API_URL_STRESS: '/api/predict-stress',
    DEBOUNCE_DELAY: 350,
    COLORS: {
        RETENCAO: '#dc2626',      // Institutional Red (Danger)
        RECUPERACAO: '#2563eb',   // Corporate Blue
        AXIS_LINES: '#3f3f46',
        TEXT_MUTED: '#a1a1aa',
        TOOLTIP_BG: 'rgba(24, 24, 27, 0.95)'
    }
};

const Formatters = {
    currency: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }),
    percent: new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }),
    compact: (val) => 'R$ ' + (val / 1000000).toFixed(0) + 'M',
    // KPIs em bilhões/milhões: com centavos, R$ 7.945.808.599,66 estourava o cartão
    big: (val) => {
        const abs = Math.abs(val);
        const fmt = (n, casas) => n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
        if (abs >= 1e9) return `R$ ${fmt(val / 1e9, 2)} bi`;
        if (abs >= 1e6) return `R$ ${fmt(val / 1e6, 1)} mi`;
        return `R$ ${fmt(val, 0)}`;
    }
};

const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
};

// --- 2. STATE MANAGEMENT ---
class DashboardState {
    constructor() {
        this.data = null;
        this.listeners = [];
    }

    set(newData) {
        this.data = newData;
        this.notify();
    }

    subscribe(callback) {
        this.listeners.push(callback);
    }

    notify() {
        this.listeners.forEach(fn => fn(this.data));
    }
}

const Store = new DashboardState();

// --- 3. NETWORK LAYER ---
class ApiService {
    static async fetchExposure(payload, isStressMode = false) {
        try {
            const ENDPOINT = isStressMode ? CONFIG.API_URL_STRESS : CONFIG.API_URL_NORMAL;
            const response = await fetch(ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
            return await response.json();

        } catch (error) {
            console.error('[Network Error]', error);
            throw error;
        }
    }
}

// --- 4. DATA VISUALIZATION (CHART.JS MASTER) ---
class ChartManager {
    constructor(canvasId) {
        this.ctx = document.getElementById(canvasId).getContext('2d');
        this.chartInstance = null;
    }

    render(graphData) {
        if (this.chartInstance) {
            this.chartInstance.destroy(); // Destruição limpa exigida
        }

        const labels = graphData.map(item => item.uf);
        const dataRetencao = graphData.map(item => item.retencao);
        const dataRecuperacao = graphData.map(item => item.recuperacao);

        this.chartInstance = new Chart(this.ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Retenção (Seguradora)',
                        data: dataRetencao,
                        backgroundColor: CONFIG.COLORS.RETENCAO,
                        borderRadius: { bottomLeft: 4, bottomRight: 4 },
                        barPercentage: 0.6,
                        stack: 'exposure'
                    },
                    {
                        label: 'Recuperação (Resseguradora)',
                        data: dataRecuperacao,
                        backgroundColor: CONFIG.COLORS.RECUPERACAO,
                        borderRadius: { topLeft: 4, topRight: 4 },
                        barPercentage: 0.6,
                        stack: 'exposure'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 600, easing: 'easeOutQuart' },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: {
                            color: CONFIG.COLORS.TEXT_MUTED,
                            usePointStyle: true,
                            boxWidth: 8,
                            font: { family: 'Inter', size: 12, weight: 500 }
                        }
                    },
                    tooltip: {
                        backgroundColor: CONFIG.COLORS.TOOLTIP_BG,
                        titleFont: { family: 'Inter', size: 14, weight: 600 },
                        bodyFont: { family: 'Inter', size: 13 },
                        padding: 12,
                        cornerRadius: 8,
                        borderColor: CONFIG.COLORS.AXIS_LINES,
                        borderWidth: 1,
                        callbacks: {
                            label: function (context) {
                                const val = context.parsed.y;
                                const total = context.chart._metasets[0].total + context.chart._metasets[1].total; // Simplified assumption
                                return `${context.dataset.label}: ${Formatters.currency.format(val)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false, drawBorder: false }, // Remoção de gridlines
                        ticks: { color: CONFIG.COLORS.TEXT_MUTED, font: { family: 'Inter', weight: 500 } }
                    },
                    y: {
                        stacked: true,
                        grid: {
                            color: CONFIG.COLORS.AXIS_LINES,
                            drawBorder: false,
                            borderDash: [4, 4]
                        },
                        ticks: {
                            color: CONFIG.COLORS.TEXT_MUTED,
                            font: { family: 'Inter' },
                            callback: Formatters.compact
                        }
                    }
                }
            }
        });
    }
}

// --- 5. UI CONTROLLER ---
class UIController {
    constructor() {
        this.inputs = {
            priority: document.getElementById('prioridade'),
            capacity: document.getElementById('capacidade'),
            rate: document.getElementById('taxa'),
            uf: document.getElementById('uf'),
            mlToggle: document.getElementById('ml-stress-toggle')
        };

        this.kpis = {
            sinBruto: document.getElementById('kpi-sinistro-bruto'),
            sinBrutaBadge: document.getElementById('kpi-sinistralidade-bruta'),
            recuperacao: document.getElementById('kpi-recuperacao'),
            custo: document.getElementById('kpi-custo'),
            beneficioBadge: document.getElementById('kpi-beneficio'),
            retencao: document.getElementById('kpi-retencao'),
            retencaoAlertBox: document.getElementById('card-retencao'),
            retencaoBadge: document.getElementById('kpi-sinistralidade-retida')
        };

        this.hints = {
            priority: document.getElementById('hint-prioridade'),
            capacity: document.getElementById('hint-capacidade'),
            rate: document.getElementById('hint-taxa'),
            scope: document.getElementById('scope-note')
        };

        this.chartManager = new ChartManager('exposure-chart');

        // Bindings
        this.bindEvents();
        Store.subscribe(this.render.bind(this));
    }

    bindEvents() {
        const handleInput = debounce(async () => {
            const isStressMode = this.inputs.mlToggle.checked;

            // UI Feedback: Ativando Tema de Catástrofe Global
            if (isStressMode) {
                document.body.classList.add('stress-mode');
            } else {
                document.body.classList.remove('stress-mode');
            }

            const payload = {
                prioridade: parseFloat(this.inputs.priority.value) || 0,
                capacidade: parseFloat(this.inputs.capacity.value) || 0,
                taxa_rol: parseFloat(this.inputs.rate.value) || 0,
                uf: this.inputs.uf.value
            };

            try {
                const data = await ApiService.fetchExposure(payload, isStressMode);
                if (data.error) throw new Error(data.error);
                Store.set(data);
            } catch (e) {
                console.warn("Simulação falhou:", e);
            }

        }, CONFIG.DEBOUNCE_DELAY);

        // Eventos nativos e dinâmicos
        this.inputs.priority.addEventListener('input', handleInput);
        this.inputs.capacity.addEventListener('input', handleInput);
        this.inputs.rate.addEventListener('input', handleInput);
        this.inputs.uf.addEventListener('change', handleInput);
        this.inputs.mlToggle.addEventListener('change', handleInput);

        // Initial Fetch
        handleInput();
    }

    render(data) {
        if (!data) return;

        // Textos KPIs Monetários
        this.kpis.sinBruto.innerText = Formatters.big(data.Sinistro_Bruto);
        this.kpis.sinBrutaBadge.innerText = `${Formatters.percent.format(data.Sinistralidade_Bruta / 100)} Sinistralidade`;
        this.kpis.recuperacao.innerText = Formatters.big(data.Recuperacao_RE);
        this.kpis.custo.innerText = Formatters.big(data.Premio_Resseguro);
        this.kpis.retencao.innerText = Formatters.big(data.Retencao_Liquida);

        // Benefício = recuperação − custo. Negativo num ano bom é o normal:
        // é o preço da proteção para o ano ruim.
        const beneficio = data.Beneficio_Resseguro;
        const sinal = beneficio >= 0 ? '+' : '−';
        this.kpis.beneficioBadge.innerText = `Benefício ${sinal}${Formatters.compact(Math.abs(beneficio))}`;
        this.kpis.beneficioBadge.classList.toggle('badge-positive', beneficio > 0);
        this.kpis.beneficioBadge.classList.toggle('badge-negative', beneficio < 0);

        // Equivalências em pontos de sinistralidade, sobre o prêmio NACIONAL
        // (o contrato é nacional, então é a base certa para ler a camada)
        const contrato = data.contrato || data;
        const premioNacional = contrato.Premio_Total;
        if (premioNacional > 0) {
            const p = (parseFloat(this.inputs.priority.value) || 0) * 1e6;
            const c = (parseFloat(this.inputs.capacity.value) || 0) * 1e6;
            const pts = (v) => (100 * v / premioNacional).toFixed(1).replace('.', ',');
            this.hints.priority.innerText = `Dispara acima de ${pts(p)}% de sinistralidade da carteira`;
            this.hints.capacity.innerText = `Cobre até ${pts(c)} pontos de sinistralidade acima da prioridade`;
            this.hints.rate.innerText = `Custo do contrato: ${Formatters.compact(contrato.Premio_Resseguro)} (${pts(contrato.Premio_Resseguro)} pontos)`;
        }

        this.hints.scope.innerText = data.escopo && data.escopo !== 'Todas'
            ? `Mostrando a parcela de ${data.escopo} no contrato nacional`
            : '';

        // Lógica de Alerta de Sinistralidade líquida (80%)
        const sinRetidaPct = data.Sinistralidade_Retida / 100;
        this.kpis.retencaoBadge.innerText = `${Formatters.percent.format(sinRetidaPct)} Sinistralidade líquida`;

        if (sinRetidaPct > 0.80) {
            this.kpis.retencaoAlertBox.classList.add('alert-critical');
        } else {
            this.kpis.retencaoAlertBox.classList.remove('alert-critical');
        }

        // Renderiza Gráfico Hot-Reload
        this.chartManager.render(data.grafico || []);
    }
}

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
    window.DashboardApp = new UIController();
});
