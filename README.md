# MacroFlow (Coletor + Agente)
# MacroFlow

MacroFlow é uma solução em Python para automação de fluxos e coleta de dados, projetada para permitir a criação, execução e monitoramento de macros e rotinas automatizadas de forma robusta e extensível.

Principais objetivos:
- Automação de tarefas repetitivas em ambientes Windows.
- Coleta e pré-processamento de dados a partir de fontes diversas.
- Execução de macros configuráveis com logs e tratamento de erros.

Funcionalidades
- Definição e execução de macros automatizadas.
- Coletor com capacidade de agendamento e persistência mínima.
- Arquitetura modular para facilitar integração e extensão.

Instalação
1. Crie e ative um ambiente virtual Python (recomendado):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale dependências:

```powershell
pip install -r requirements.txt
```

Uso básico
- Execute o coletor/main runner:

```powershell
python src/run_macroflow.py
```

Configuração
- Ajuste as opções em `src/settings.py` conforme seu ambiente (caminhos, credenciais, agendamento).

Estrutura do projeto
- `src/` : código-fonte principal (agentes, coletor, runner, configurações).
- `requirements.txt` : dependências do projeto.

Contribuição
- Abra issues para bugs ou sugestões.
- Para contribuições: crie um fork, adicione uma branch com alterações e abra um pull request descrevendo as mudanças.

Licença
- Indique aqui a licença do projeto (ex: MIT). Se preferir, informe qual licença aplicar.

Contato
- Para dúvidas ou suporte profissional, abra uma issue ou envie um e-mail para o responsável do projeto.

---
Este README foi preparado para o repositório MacroFlow — se quiser, eu posso também inicializar o repositório Git local e executar o push para o seu repositório no GitHub (preciso da URL do repositório e do método de autenticação: HTTPS/PAT ou SSH).

## O que ele faz (visão objetiva)

- Puxa **DXY (proxy institucional)** e **US10Y** do **FRED**
- Puxa **SPX, NDX, DJI, IBOV, USD/BRL** do **Yahoo Finance** (via yfinance)
- Reamostra tudo para **4H**
- Calcula:
  - Preço, Variação, %Variação, Volume (4H)
  - RSI(14)
  - Níveis fixos **0/25/50/75/100** por passo (configurável)
  - Regime macro (`RISK_ON`, `RISK_OFF`, `NEUTRO`) e **score**
  - Flag institucional **NÃO_OPERAR** + motivo
- Salva no Excel:
  - Aba `SNAPSHOTS`: 1 linha por execução
  - Abas `OHLC_<ATIVO>`: candles 4H
- O agente lê o snapshot e **gera o plano operacional** para mini dólar e mini índice
- **Se FRED ou SPX falhar**, o sistema **trava em NÃO OPERAR** (motivo explícito)

> Importante: WIN/WDO futuros B3 em tempo real normalmente exigem fonte paga/bridge. O pipeline já está pronto para plugar depois.

---

## Estrutura do projeto

```
macroflow_coletor_excel/
├─ src/
│  ├─ __init__.py
│  ├─ settings.py
│  ├─ macroflow_coletor.py
│  ├─ agente_macroflow.py
│  └─ run_macroflow.py
├─ .env.example
├─ requirements.txt
└─ README.md
```

---

## Pré-requisitos

- Python 3.10+
- Conta no FRED para gerar `FRED_API_KEY`

---

## Como criar ambiente virtual (Windows)

### 1) Criar
```bash
python -m venv .venv
```

### 2) Ativar
```bash
.venv\Scripts\activate
```

> Se der erro de permissão no PowerShell:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3) Instalar dependências
```bash
pip install -r requirements.txt
```

---

## Configurar FRED_API_KEY

1) Copie `.env.example` para `.env`
2) Edite `.env` e coloque sua chave:

```env
FRED_API_KEY=SEU_TOKEN_AQUI
```

Opcional (se quiser usar LLM no agente):
```env
OPENAI_API_KEY=SEU_TOKEN_AQUI
OPENAI_MODEL=gpt-4o-mini
```

---

## Executar

```bash
python -m src.macroflow_coletor
python -m src.run_macroflow
```

Opcional (alterar caminho do Excel):
```bash
python -m src.macroflow_coletor --excel "C:\temp\MacroFlow_Dados.xlsx"
```

Executar apenas o agente (gera recomendação a partir do último snapshot):
```bash
python -m src.agente_macroflow
```

---

## Onde o Excel é salvo

Padrão:
`C:\Users\<SeuUsuario>\Documents\MacroFlow_Dados.xlsx`

---

## Logs de saúde (console)

Durante a coleta, o sistema imprime um resumo em português:

- Status das fontes (FRED e SPX/Yahoo)
- Avisos por ativo sem dados
- Confirmação de escrita no Excel
- Resultado final com **Regime**, **Score** e **Não operar**

Exemplo:
```
🧭 Iniciando coleta MacroFlow...
✅ FRED OK (DXY/US10Y).
✅ SPX OK (Yahoo).
⚠️ Yahoo sem dados para NDX (^NDX).
✅ Excel atualizado: C:\Users\...\Documents\MacroFlow_Dados.xlsx
ℹ️ Regime: RISK_OFF | Score: 80 | Não operar: False (Liberado para operar...)
⚠️ Coleta concluída com falhas: Yahoo:NDX.
```

Se **tudo deu certo**, a última linha será:
```
✅ Coleta concluída com sucesso. Todas as fontes responderam.
```

---

## Automatizar (Agendador de Tarefas)

Agende a execução a cada 15 minutos:

- Programa:
  - `C:\caminho\do\projeto\.venv\Scripts\python.exe`
- Argumentos:
  - `-m src.macroflow_coletor`
- Iniciar em:
  - pasta do projeto

---

## Ajustes rápidos

No arquivo `src/settings.py`, você pode ajustar:
- `score_minimo_operar`
- Lista de ativos `ATIVOS_YAHOO`
- `prefixo_mini_dolar` e `prefixo_mini_indice` (agente)
- `passo_nivel_padrao` e `casas_nivel_padrao` (níveis fixos padrão)
- Mapa `PASSOS_NIVEIS_FIXOS` (overrides por ativo)
- `lookback_swing_barras_4h` (só se você voltar para níveis por swing)