# MacroFlow

Atualizacao atual: o MacroFlow agora inclui motor quant deterministico com `VWAP`, `POC`, `ATR`, `Bollinger`, `OBV`, `ADX`, score 0-100, classificacao de regime, risco por volatilidade, relatorio estruturado, alerta automatico por e-mail, calendario economico e chat Jarvis. A camada LLM, quando habilitada, apenas explica os dados e nao decide entrada.

MacroFlow agora é uma plataforma local de inteligência macro + execução disciplinada para trading, com três pilares:

- coleta e persistência de dados críticos (`DXY`, `US10Y`, `SPX`, `IBOV`, `USD/BRL` e proxies associados);
- motor determinístico de decisão baseado no documento `ANALISE-PREDITIVA-PRESCRITIVA.docx`;
- dashboard web local com identidade visual consistente com a referência fornecida.

O projeto foi refatorado para separar ingestão, indicadores, estratégia, persistência e apresentação. O Excel continua existindo como artefato de compatibilidade, mas o contrato principal do sistema passa a ser o estado local em JSON consumido pelo dashboard.

## Dashboard modular

A aba de indicadores agora tambem mostra leitura quant por ativo: score, regime, sinal deterministico, VWAP, POC, ADX, ATR, volume, volatilidade e explicacao operacional.

O dashboard tambem ganhou o `Jarvis - Trader Quantitativo`, acessado pelo botao flutuante no canto inferior direito. Ele usa o `prompt.txt`, o ultimo `dashboard_state.json`, os relatorios quant, decisoes operacionais e eventos do calendario economico como contexto de conversa.

O frontend local foi reorganizado em abas funcionais:

- `Menu Principal`: panorama geral do mercado e explicação do que o MacroFlow faz;
- `Análise Gráfica`: candles de todos os ativos monitorados;
- `Indicadores Técnicos`: linhas de PMD, MME9, MME21 e RSI por ativo;
- `Notícias do Mercado Financeiro`: calendario economico estruturado com filtro por pais e criticidade de 1, 2 ou 3 touros;
- `Configurações`: edição dos parâmetros principais diretamente pela interface, com gravação no `.env`.

O botão `Iniciar Macroflow` agora fica logo abaixo de `Configurações` no menu lateral e recompõe os dados do dashboard sob demanda.
Os assets estáticos do dashboard (`app.js` e `styles.css`) agora são servidos com versão na URL para evitar cache antigo do navegador após mudanças de interface.

## O que mudou

- a coleta macro e de mercado saiu do script monolítico e foi organizada em módulos;
- a decisão deixou de usar apenas níveis fixos `0/25/50/75/100` e passou a respeitar a lógica de `PMD`, `MME9`, `MME21`, pullback, confirmação, stop inicial, trailing stop e sizing por risco;
- a camada macro (`DXY`, `US10Y`, `SPX`) continua preservada como filtro e trava institucional;
- o sistema ganhou uma interface web local premium para leitura operacional;
- a persistência agora grava:
  - `data/runtime/dashboard_state.json`
  - `data/runtime/snapshots.jsonl`
  - `data/runtime/MacroFlow_Dados.xlsx`

## Arquitetura atual

```text
src/
├─ macroflow/
│  ├─ api.py
│  ├─ config.py
│  ├─ domain.py
│  ├─ indicators.py
│  ├─ pipeline.py
│  ├─ providers.py
│  ├─ storage.py
│  ├─ strategy.py
│  └─ web/
│     ├─ static/
│     └─ templates/
├─ agente_macroflow.py
├─ macroflow_coletor.py
├─ run_macroflow.py
└─ settings.py
tests/
└─ ...
```

Camadas:

Novos modulos da camada quant e alertas:

- `quant.py`: indicadores avancados, score, regime, regras de entrada/saida e risco por ATR;
- `llm.py`: explicacao textual opcional com fallback local, sem decidir trade;
- `emailer.py`: envio SMTP com gatilho por novo sinal ou relatorio diario;
- `economic_calendar.py`: calendario economico com pais, criticidade, surpresa, projecao e vies macro;
- `jarvis.py`: chat Jarvis com prompt local, contexto do dashboard e fallback analitico local;
- `settings_store.py`: exposicao dos parametros editaveis no dashboard.

- `providers.py`: integrações com `FRED` e `Yahoo Finance`
- `indicators.py`: normalização, RSI, resample 4H, PMD, MME9/MME21 e níveis fixos
- `strategy.py`: score macro, bloqueio institucional, leitura do setup e sizing
- `storage.py`: gravação em Excel + JSON
- `api.py`: entrega local para o dashboard
- `web/`: design system, layout e rendering do produto

## Estratégia operacional implementada

O sistema segue a lógica do documento de análise preditiva/prescritiva:

### Camada macro

- `DXY`, `US10Y` e `SPX` geram `regime`, `score` e `NÃO OPERAR`
- se `FRED` ou `SPX` falharem, o sistema trava a operação
- divergência entre `DXY` e `US10Y` ou volume fraco também pode bloquear

### Camada técnica

- timeframe operacional: diário
- métrica base: `PMD = (máxima + mínima) / 2`
- médias:
  - `MME9` sobre o `PMD`
  - `MME21` sobre o `PMD`
- compra:
  - `MME9` cruza e permanece acima da `MME21`
  - o preço toca a `MME21`
  - ocorre candle positivo no mesmo dia ou no seguinte
- venda:
  - `MME9` cruza e permanece abaixo da `MME21`
  - o preço toca a `MME21`
  - ocorre candle negativo no mesmo dia ou no seguinte
- stop inicial:
  - abaixo da mínima do candle de toque no long
  - acima da máxima do candle de toque no short
- saída:
  - trailing stop pela `MME21`
- sizing:
  - risco máximo de `1%` do capital configurado

## Camada quant e alertas

A camada quant calcula `VWAP` intraday e rolling, `POC/VAH/VAL`, `ATR`, Bandas de Bollinger, squeeze, `OBV`, media de volume, detector de volume spike, `EMA 8/21/80/200` e `ADX`.

O regime e classificado como `trend_clean`, `chaotic`, `range` ou `transition`. O score final vai de 0 a 100 e combina tendencia, volume, volatilidade, macro score, posicao contra VWAP e posicao contra POC.

As entradas seguem regra deterministica: compra exige preco acima do VWAP e POC, `EMA21 > EMA80`, `ADX > 25` e volume spike; venda aplica a leitura inversa. Trades sao bloqueados em regime `chaotic`, quando o macro esta bloqueado ou quando a direcao macro conflita com o sinal operacional.

Risco quant: `position_size = capital * risk_percent / ATR`, stop em `2 * ATR`, alvo em `3 * ATR` e teto efetivo de risco de 2% por operacao.

O e-mail usa `smtplib` e fica desabilitado por padrao. Para ativar, configure `EMAIL_ENABLED=true`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_TO` e `EMAIL_SEND_MODE`. O estado anti-spam fica em `data/runtime/email_alert_state.json`.

O LLM e opcional (`MACROFLOW_LLM_ENABLED=true`) e so gera explicacao textual. O sinal, entrada, stop, alvo e sizing continuam 100% deterministicos.

## Calendario economico e Jarvis

A aba `Noticias do Mercado Financeiro` agora carrega eventos de calendario economico via Fair Economy / Forex Factory por padrao, incluindo pais, categoria, evento, actual, forecast, previous, criticidade em 1, 2 ou 3 touros, surpresa numerica quando disponivel, projecao textual e vies macro estimado. Trading Economics permanece como provider configuravel para quem tiver credencial propria.

O filtro visual permite selecionar pais e criticidade diretamente na tela. A coleta padrao usa `United States,Brazil,Euro Area,China`, janela de 1 dia para tras e 7 dias para frente.

O `Jarvis - Trader Quantitativo` fica no canto inferior direito do dashboard. Ele usa `prompt.txt` e o ultimo estado coletado do MacroFlow. Se `MACROFLOW_LLM_ENABLED=false`, responde em modo local com uma leitura resumida; se estiver habilitado com `OPENAI_API_KEY`, usa o LLM com `store=false` e os mesmos guardrails deterministas.

## Identidade visual

O dashboard foi construído com um design system inspirado diretamente na imagem `referência_visual.png`:

- superfícies escuras com brilho suave e gradientes discretos;
- acento primário verde institucional;
- acento secundário dourado para leitura de curva e destaque;
- cards densos, gráficos claros e foco em leitura rápida;
- navegação lateral, hero, KPIs, trilha de auditoria e planos operacionais por ativo.

## Requisitos

- Python 3.11+
- `FRED_API_KEY` válida

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário.

Variáveis principais:

- `FRED_API_KEY`
- `MACROFLOW_CAPITAL_TOTAL_BRL`
- `MACROFLOW_RUNTIME_DIR`
- `MACROFLOW_EXCEL_PATH`
- `MACROFLOW_CHART_DEFAULT_TIMEFRAME`
- `MACROFLOW_PORT`
- `MACROFLOW_VWAP_ROLLING_WINDOW`
- `MACROFLOW_POC_BINS`
- `MACROFLOW_ATR_PERIOD`
- `MACROFLOW_VOLUME_SPIKE_FACTOR`
- `MACROFLOW_ADX_PERIOD`
- `MACROFLOW_QUANT_RISK_PERCENT`
- `EMAIL_ENABLED`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `EMAIL_TO`
- `MACROFLOW_LLM_ENABLED`
- `OPENAI_API_KEY`
- `MACROFLOW_CALENDAR_ENABLED`
- `TRADING_ECONOMICS_API_KEY`
- `MACROFLOW_CALENDAR_COUNTRIES`
- `MACROFLOW_CALENDAR_IMPORTANCE_MIN`
- `MACROFLOW_JARVIS_PROMPT_PATH`

## Execução

Pipeline completo:

```powershell
python -m src.run_macroflow
```

Coleta somente:

```powershell
python -m src.run_macroflow collect
```

Relatório determinístico do último estado:

```powershell
python -m src.run_macroflow agent
```

Dashboard local:

```powershell
python -m src.run_macroflow serve --port 8000
```

Depois abra:

```text
http://127.0.0.1:8000
```

## Testes

```powershell
pytest
```

## Persistência

Arquivos gerados por padrão:

- `data/runtime/dashboard_state.json`
- `data/runtime/snapshots.jsonl`
- `data/runtime/MacroFlow_Dados.xlsx`

## Limitações importantes

- hoje `USDBRL` e `IBOV` ainda são proxies públicos para `WDO/WIN`; não substituem feed real da B3;
- `DXY` e `US10Y` continuam em base diária via `FRED`, então a camada macro deve ser lida como filtro institucional, não como feed intraday;
- sem `FRED_API_KEY`, o sistema vai bloquear por desenho;
- o dashboard está pronto para uso local, mas a validação em mercado real depende da sua chave, do seu capital configurado e do feed final escolhido.

## Documentação complementar

- [Arquitetura](docs/architecture.md)

## Critério de pronto desta refatoração

- coleta modularizada;
- motor técnico coerente com o documento;
- camada macro preservada;
- dashboard local com design system consistente;
- README alinhado ao código real;
- testes cobrindo bloqueio macro, setup técnico e API base.
