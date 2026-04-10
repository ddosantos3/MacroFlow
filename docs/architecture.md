# Arquitetura MacroFlow

## Objetivo

Atualizacao: a arquitetura agora inclui uma camada quant deterministica (`quant.py`) e uma camada de alertas (`emailer.py` + `llm.py`). O LLM e apenas explicativo; entrada, saida, score, regime e risco seguem regras de codigo.

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

### 4. Persistência

`src/macroflow/storage.py` salva:

- `dashboard_state.json`
- `snapshots.jsonl`
- `MacroFlow_Dados.xlsx`

O Excel existe para compatibilidade e auditoria humana. O dashboard consome o JSON local.

### 5. Entrega

- `src/macroflow/api.py`: API local e endpoint de refresh
- `src/macroflow/web/templates`: estrutura HTML
- `src/macroflow/web/static`: design system, layout e comportamento do dashboard

## Decisões importantes

- macro continua sendo filtro e trava, não gatilho de execução;
- técnico passa a ser diário, como no documento de referência;
- proxies continuam até a entrada de um feed real de `WDO/WIN`;
- LLM não participa da decisão de trade.

## Riscos ainda presentes

- `FRED` diário versus proxies intraday ainda exige interpretação correta do timeframe;
- proxies públicos não equivalem ao instrumento futuro real;
- sem replay histórico mais amplo, a confiança ainda está em fase de endurecimento.
