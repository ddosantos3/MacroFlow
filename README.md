# MacroFlow

MacroFlow agora é uma plataforma local de inteligência macro + execução disciplinada para trading, com três pilares:

- coleta e persistência de dados críticos (`DXY`, `US10Y`, `SPX`, `IBOV`, `USD/BRL` e proxies associados);
- motor determinístico de decisão baseado no documento `ANALISE-PREDITIVA-PRESCRITIVA.docx`;
- dashboard web local com identidade visual consistente com a referência fornecida.

O projeto foi refatorado para separar ingestão, indicadores, estratégia, persistência e apresentação. O Excel continua existindo como artefato de compatibilidade, mas o contrato principal do sistema passa a ser o estado local em JSON consumido pelo dashboard.

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
- `MACROFLOW_PORT`

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
