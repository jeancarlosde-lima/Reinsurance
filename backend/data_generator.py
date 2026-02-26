import pandas as pd
import numpy as np
import os

def gerar_dados():
    np.random.seed(42)
    ufs = ['SP', 'PR', 'RS', 'MG', 'GO', 'MT', 'MS']
    anos_meses = ['2023-01', '2023-02', '2023-03', '2023-04', '2023-05', '2023-06']
    
    dados = []
    
    # Gerar dados para o Ramo 11 (Seguro Rural) e alguns outros ramos para teste de filtro
    for uf in ufs:
        for am in anos_meses:
            # Ramo 11
            premio_ganho = np.random.uniform(10_000_000, 50_000_000)
            premio_retido = premio_ganho * 0.8  # Seguradora retém 80% do prêmio
            
            # Simulando sinistros severos no sul (RS, PR) em alguns meses
            if uf in ['RS', 'PR'] and am in ['2023-03', '2023-04']:
                sinistro_bruto = np.random.uniform(40_000_000, 100_000_000) # Evento catastrófico
            else:
                sinistro_bruto = np.random.uniform(5_000_000, 30_000_000)
                
            dados.append([uf, am, 11, premio_ganho, premio_retido, sinistro_bruto])
            
            # Ramo 18 (outro ramo, pra testar filtro)
            dados.append([uf, am, 18, np.random.uniform(5_000_000, 10_000_000), np.random.uniform(4_000_000, 8_000_000), np.random.uniform(1_000_000, 5_000_000)])

    # Adicionar alguns nulos para testar o tratamento de dados (Diretriz 2)
    dados.append(['SP', '2023-07', 11, np.nan, 10_000_000, np.nan])

    df = pd.DataFrame(dados, columns=['UF', 'Ano_Mes', 'Ramo', 'Premio_Ganho', 'Premio_Retido', 'Sinistro_Bruto'])
    
    # Salvar na mesma pasta
    caminho_csv = os.path.join(os.path.dirname(__file__), 'dados_resseguro.csv')
    df.to_csv(caminho_csv, index=False)
    print(f"Dados gerados com sucesso em {caminho_csv}")

if __name__ == '__main__':
    gerar_dados()
