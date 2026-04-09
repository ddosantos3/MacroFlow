# Arquitetura MacroFlow

## Objetivo

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
