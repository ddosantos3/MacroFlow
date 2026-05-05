# Arquitetura MacroFlow

## Objetivo

Atualizacao: a arquitetura agora inclui uma camada quant deterministica (`quant.py`), motor decisorio intraday v2 (`intraday_decision.py`), alertas (`emailer.py` + `llm.py`), calendario economico (`economic_calendar.py`) e chat Jarvis (`jarvis.py`). O LLM e apenas explicativo; entrada, saida, score, regime e risco seguem regras de codigo.

Manter o filtro macro original do projeto, substituir o motor operacional por uma leitura determinística baseada em `PMD/MME9/MME21` e entregar isso com uma camada visual confiável para decisão local.

## Camadas

### 1. Ingestão

- `FRED`: `DXY` e `US10Y`
- `Yahoo Finance`: `SPX`, `DJI`, `NDX`, `IBOV`, `USD/BRL`
- retries e normalização básica ficam em `src/macroflow/providers.py`

### 2. Indicadores

- `RSI`
- reamostragem `4H`
- `PMD`
- `MME9`
- `MME21`
- detecção de toque na média lenta
- cálculo de níveis fixos auxiliares

Tudo isso fica em `src/macroflow/indicators.py`.

### 3. Motor de decisão

`src/macroflow/strategy.py` opera em duas trilhas:

- trilha macro:
  - regime
  - score
  - trava institucional
  - direcional macro por ativo
- trilha técnica:
  - tendência via `MME9 x MME21`
  - pullback até `MME21`
  - confirmação por candle
  - stop inicial
  - trailing stop
  - sizing pelo risco máximo de `1%`

A decisão final só fica pronta quando macro e técnico convergem.

### 3b. Motor quant e alertas

`src/macroflow/quant.py` calcula `VWAP`, `POC`, `ATR`, Bollinger, squeeze, `OBV`, media/spike de volume, `EMA 8/21/80/200` e `ADX`.

O score quant normalizado de 0 a 100 combina tendencia, volume, volatilidade, macro score, posicao contra VWAP e posicao contra POC. A classificacao de regime usa `trend_clean`, `chaotic`, `range` e `transition`.

As regras de entrada/saida sao deterministicamente avaliadas no codigo. O LLM nao participa dessa decisao.

`src/macroflow/emailer.py` envia relatorio por SMTP quando existe novo sinal ou quando o envio diario ainda nao ocorreu. `src/macroflow/llm.py` gera explicacao opcional e tem fallback local.

### 3c. Motor decisorio intraday v2

`src/macroflow/intraday_decision.py` e o nucleo de producao para decisao intraday. Ele nao depende de score solto nem de fallback artificial. A decisao passa por gates:

- integridade de candles 60m/5m, proxies obrigatorios e fluxo/agressao real;
- janela operacional configuravel e bloqueio de noticia de alto impacto quando informado;
- correlacao especifica por ativo: indice e dolar usam pesos opostos para `SPX`, `DXY`, `US10Y` e `USD/BRL`;
- estrutura e zona: compra so em `Zona <= 0.25`, venda so em `Zona >= 0.75`;
- VWAP, EMA9, EMA21, candle de 60m e RSI alinhados ao lado permitido;
- RVOL ou volume financeiro acima da referencia real;
- imbalance de agressao confirmando o lado;
- candle de 5m confirmado;
- stop estrutural, alvo objetivo, `RR >= 2.0`, expectativa positiva e sizing por risco.

Sem qualquer input critico, o status final e `NO_TRADE` ou `BLOCKED`, com motivo rastreavel (`ORDERFLOW_UNAVAILABLE`, `MISSING_PROXY`, `STALE_DATA`, `BAD_PRICE_LOCATION`, `FLOW_NOT_CONFIRMED`, `BAD_RISK_REWARD`, `MISSING_EXPECTANCY`, entre outros).

### 3d. Calendario economico e Jarvis

`src/macroflow/economic_calendar.py` coleta eventos do calendario economico via Fair Economy / Forex Factory por padrao, com Trading Economics opcional via credencial propria. A camada normaliza pais, categoria, evento, actual, forecast, previous, criticidade e uma projecao de impacto. Esses eventos entram em `news_center` dentro do `dashboard_state.json`.

`src/macroflow/jarvis.py` le o `prompt.txt`, monta um contexto enxuto com macro, decisoes, relatórios quant e calendario, e responde via endpoint `/api/jarvis/chat`. Quando o LLM esta desabilitado ou indisponivel, o Jarvis responde em modo local sem inventar dados.

### 4. Persistência

`src/macroflow/storage.py` salva:

- `dashboard_state.json`
- `snapshots.jsonl`
- `decision_audit.jsonl`
- `MacroFlow_Dados.xlsx`

O Excel existe para compatibilidade e auditoria humana. O dashboard consome o JSON local. A trilha `decision_audit.jsonl` separa ciclos de decisao v2 da camada analitica historica.

### 5. Entrega

- `src/macroflow/api.py`: API local e endpoint de refresh
- `src/macroflow/web/templates`: estrutura HTML
- `src/macroflow/web/static`: design system, layout e comportamento do dashboard

## Decisões importantes

- macro continua sendo filtro e trava, não gatilho de execução;
- técnico passa a ser diário, como no documento de referência;
- v2 intraday so pode liberar entrada com feed real completo; proxies publicos atuais mantem `NO_TRADE`;
- proxies continuam até a entrada de um feed real de `WDO/WIN`;
- LLM não participa da decisão de trade.

## Riscos ainda presentes

- `FRED` diário versus proxies intraday ainda exige interpretação correta do timeframe;
- proxies públicos não equivalem ao instrumento futuro real;
- sem replay histórico mais amplo, a confiança ainda está em fase de endurecimento.
