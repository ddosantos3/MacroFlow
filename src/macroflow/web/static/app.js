const state = {
  dashboard: null,
  currentTab: "menu-principal",
  currentTimeframe: "4H",
  selectedAsset: null,
  indicatorPanelOpen: false,
  visibleIndicators: {
    ema_fast: true,
    ema_slow: true,
    vwap: true,
    pmd: false,
    poc: false,
  },
  newsCountry: "ALL",
  newsImportance: "ALL",
  jarvisHistory: [],
};

let chartSequence = 0;
const requestedChartLoads = new Set();

const DEFAULT_TIMEFRAME_OPTIONS = [
  { value: "1D", label: "1 Dia" },
  { value: "4H", label: "4 Horas" },
  { value: "1H", label: "1 Hora" },
  { value: "30M", label: "30 Minutos" },
  { value: "15M", label: "15 Minutos" },
  { value: "5M", label: "5 Minutos" },
  { value: "1M", label: "1 Minuto" },
];

const INDICATOR_OVERLAYS = [
  { key: "ema_fast", label: "Média curta", source: "indicators", field: "ema_fast", color: "#5df2b4" },
  { key: "ema_slow", label: "Média lenta", source: "indicators", field: "ema_slow", color: "#ff6b7d" },
  { key: "vwap", label: "Preço médio", source: "quant_indicators", field: "vwap", color: "#79dbff" },
  { key: "pmd", label: "Meio do candle", source: "indicators", field: "pmd", color: "#f6c66f" },
  { key: "poc", label: "Volume-chave", source: "quant_indicators", field: "poc", color: "#bb8dff" },
];

const setText = (id, value) => {
  const element = document.getElementById(id);
  if (!element) return null;
  element.textContent = value;
  return element;
};

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
};

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${formatNumber(value, 2)}%`;
};

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const formatCompactNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value));
};

const assetEmoji = (asset) => ({
  USDBRL: "DL",
  BRA50: "IN",
  SPX: "SP",
  NDX: "ND",
  USA500: "US",
  USAIND: "DJ",
}[asset] || String(asset || "MF").slice(0, 2).toUpperCase());

const metricIcon = (label = "") => {
  const source = label.toLowerCase();
  if (source.includes("regime") || source.includes("macro")) return "🧭";
  if (source.includes("score")) return "🎯";
  if (source.includes("dxy") || source.includes("dolar")) return "💵";
  if (source.includes("yield") || source.includes("treasury") || source.includes("juros")) return "🏦";
  if (source.includes("not") || source.includes("news") || source.includes("calend")) return "🌍";
  if (source.includes("volume")) return "🌊";
  if (source.includes("sinal") || source.includes("trade")) return "⚡";
  return "✦";
};

const normalizeText = (value = "") => String(value || "").toLowerCase();

const toneFromText = (...values) => {
  const joined = normalizeText(values.filter(Boolean).join(" "));
  if (!joined) return "neutral";
  if (joined.includes("buy") || joined.includes("compra") || joined.includes("operavel") || joined.includes("online") || joined.includes("alta")) return "bullish";
  if (joined.includes("sell") || joined.includes("venda") || joined.includes("bloqueado") || joined.includes("error") || joined.includes("offline") || joined.includes("queda")) return "bearish";
  if (joined.includes("warning") || joined.includes("chaotic") || joined.includes("nao operar") || joined.includes("aten") || joined.includes("monitorar")) return "warning";
  if (joined.includes("jarvis") || joined.includes("ia")) return "violet";
  return "neutral";
};

const toneClass = (tone) => {
  if (tone === "bullish") return "bullish";
  if (tone === "bearish") return "bearish";
  if (tone === "warning") return "warning";
  if (tone === "info") return "info";
  if (tone === "violet") return "violet";
  return "";
};

const displaySignal = (value) => {
  const signal = String(value || "").toUpperCase();
  if (["BUY", "COMPRA", "SINAL_BUY", "ENTER_LONG", "ARMED_LONG"].includes(signal)) return "Compra";
  if (["SELL", "VENDA", "SINAL_SELL", "ENTER_SHORT", "ARMED_SHORT"].includes(signal)) return "Venda";
  if (signal.includes("BLOQUE") || signal.includes("BLOCK")) return "Bloqueado";
  if (signal.includes("NO_TRADE")) return "Sem entrada";
  return "Aguardar";
};

const displayStatus = (value) => {
  const status = String(value || "").toUpperCase();
  if (status.includes("SINAL_BUY") || status.includes("ENTER_LONG")) return "Compra liberada";
  if (status.includes("SINAL_SELL") || status.includes("ENTER_SHORT")) return "Venda liberada";
  if (status.includes("BLOQUE") || status.includes("BLOCK")) return "Bloqueado";
  if (status.includes("SEM_DADOS")) return "Sem dados suficientes";
  if (status.includes("SEM_SINAL") || status.includes("HOLD")) return "Aguardar";
  if (status.includes("ACOMPANHAMENTO")) return "Acompanhar";
  if (status.includes("CONFIRMACAO")) return "Esperar confirmação";
  return status ? status.replaceAll("_", " ").toLowerCase() : "Aguardar";
};

const displayRegime = (value) => {
  const regime = String(value || "").toLowerCase();
  if (regime === "trend_clean") return "Tendência clara";
  if (regime === "chaotic") return "Mercado agitado";
  if (regime === "range") return "Lateral";
  if (regime === "transition") return "Transição";
  if (regime === "sem_dados") return "Sem dados";
  if (regime === "strong_long_bias") return "Compra forte";
  if (regime === "weak_long_bias") return "Compra moderada";
  if (regime === "strong_short_bias") return "Venda forte";
  if (regime === "weak_short_bias") return "Venda moderada";
  if (regime === "neutral") return "Neutro";
  return value || "-";
};

const displayDirection = (value) => {
  const direction = String(value || "").toUpperCase();
  if (["COMPRA", "BUY", "LONG"].includes(direction)) return "Compra";
  if (["VENDA", "SELL", "SHORT"].includes(direction)) return "Venda";
  return "Neutro";
};

const displayBlockReason = (value) => ({
  ORDERFLOW_UNAVAILABLE: "Falta leitura real de agressão",
  INVALID_TIMEFRAME: "Tempo gráfico incompatível",
  MISSING_PROXY: "Falta dado de mercado obrigatório",
  STALE_DATA: "Dado desatualizado",
  BAD_PRICE_LOCATION: "Preço fora da região ideal",
  FLOW_NOT_CONFIRMED: "Fluxo não confirmou o movimento",
  BAD_RISK_REWARD: "Risco e alvo não compensam",
  MISSING_EXPECTANCY: "Falta histórico real do setup",
  LOW_PARTICIPATION: "Pouca participação no movimento",
  OUTSIDE_TRADING_WINDOW: "Fora do horário operacional",
  MACRO_CONFLICT: "Mercado externo em conflito",
  MICRO_CONFLICT: "Gráfico ainda não confirmou",
}[String(value || "").toUpperCase()] || String(value || "-").replaceAll("_", " ").toLowerCase());

const buildHelperPill = (label, tone = "neutral") => `
  <span class="helper-pill ${toneClass(tone)}">${escapeHtml(label)}</span>
`;

const renderBulls = (importance) => "●".repeat(Math.max(Number(importance) || 0, 0)) || "·";

const setActiveTab = (tabId) => {
  state.currentTab = tabId;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
    button.setAttribute("aria-current", button.dataset.tab === tabId ? "page" : "false");
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tabId);
  });
};

const getDecisionMap = () => {
  const entries = (state.dashboard?.asset_decisions || []).map((decision) => [decision.asset, decision]);
  return new Map(entries);
};

const getIntradayDecisionMap = () => {
  const entries = (state.dashboard?.intraday_decisions || []).map((decision) => [decision.asset, decision]);
  return new Map(entries);
};

const getAssets = () => state.dashboard?.market_assets || [];

const getSelectedAsset = () => {
  const assets = getAssets();
  if (!assets.length) return null;
  return assets.find((asset) => asset.asset === state.selectedAsset) || assets[0];
};

const getTimeframeOptions = () => {
  const options = state.dashboard?.summary?.timeframe_options;
  if (Array.isArray(options) && options.length) return options;
  return DEFAULT_TIMEFRAME_OPTIONS;
};

const timeframeLabel = (value) => {
  const option = getTimeframeOptions().find((item) => item.value === value);
  return option?.label || value || "-";
};

const getChartPayload = (asset, timeframe = state.currentTimeframe) => asset?.charts?.[timeframe] || null;

const buildOverlaySeries = (chartPayload, candles) => {
  if (!chartPayload || !candles?.length) return [];
  return INDICATOR_OVERLAYS
    .filter((indicator) => state.visibleIndicators[indicator.key])
    .map((indicator) => {
      const points = chartPayload[indicator.source] || [];
      const values = points
        .slice(-candles.length)
        .map((point) => Number(point[indicator.field]))
        .map((value) => (Number.isFinite(value) ? value : null));
      return { ...indicator, values };
    })
    .filter((indicator) => indicator.values.some((value) => Number.isFinite(value)));
};

const selectAsset = (assetCode, tab = "visao-ativo") => {
  state.selectedAsset = assetCode;
  renderAssetSelector();
  renderSelectedAssetOverview();
  renderChartAssets();
  if (tab) setActiveTab(tab);
  loadSelectedChartIfNeeded();
};

const loadSelectedChartIfNeeded = async () => {
  const asset = getSelectedAsset();
  if (!asset?.asset || !state.currentTimeframe) return;
  asset.charts = asset.charts || {};
  const chartPayload = asset.charts[state.currentTimeframe];
  if (chartPayload && Array.isArray(chartPayload.candles) && chartPayload.candles.length) return;

  const requestKey = `${asset.asset}:${state.currentTimeframe}`;
  if (requestedChartLoads.has(requestKey)) return;
  requestedChartLoads.add(requestKey);

  asset.charts[state.currentTimeframe] = {
    label: timeframeLabel(state.currentTimeframe),
    available: false,
    loading: true,
    candles: [],
    indicators: [],
    quant_indicators: [],
    message: "Carregando dados reais deste tempo gráfico...",
  };
  renderSelectedAssetOverview();

  try {
    const params = new URLSearchParams({ timeframe: state.currentTimeframe });
    const response = await fetch(`/api/assets/${encodeURIComponent(asset.asset)}/chart?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao carregar tempo gráfico.");
    asset.charts[state.currentTimeframe] = payload.chart;
  } catch (error) {
    asset.charts[state.currentTimeframe] = {
      label: timeframeLabel(state.currentTimeframe),
      available: false,
      candles: [],
      indicators: [],
      quant_indicators: [],
      message: error.message || "Sem dados reais para este tempo gráfico agora.",
    };
  } finally {
    renderSelectedAssetOverview();
    renderChartAssets();
  }
};

const setTimeframe = (timeframe) => {
  state.currentTimeframe = timeframe;
  renderTimeframeSwitches();
  renderSelectedAssetOverview();
  renderChartAssets();
  loadSelectedChartIfNeeded();
};

const renderTimeframeSwitches = () => {
  document.querySelectorAll("[data-timeframe-group]").forEach((host) => {
    host.innerHTML = `
      <label class="timeframe-label" for="timeframe-select-${escapeHtml(host.dataset.timeframeGroup || "main")}">Tempo gráfico</label>
      <select class="timeframe-select" id="timeframe-select-${escapeHtml(host.dataset.timeframeGroup || "main")}" data-timeframe-select>
        ${getTimeframeOptions().map((timeframe) => `
          <option value="${escapeHtml(timeframe.value)}" ${state.currentTimeframe === timeframe.value ? "selected" : ""}>
            ${escapeHtml(timeframe.label || timeframe.value)}
          </option>
        `).join("")}
      </select>
    `;
  });
  document.querySelectorAll("[data-timeframe-select]").forEach((select) => {
    select.addEventListener("change", () => setTimeframe(select.value));
  });
};

const drawLineChart = (container, series, options = {}) => {
  if (!container) return;
  const validSeries = series.filter((line) => Array.isArray(line.values) && line.values.some(Number.isFinite));
  if (!validSeries.length) {
    container.classList.add("empty");
    container.innerHTML = "<p class='muted'>Sem dados suficientes para desenhar este grafico.</p>";
    return;
  }
  container.classList.remove("empty");

  const chartId = `chart-${++chartSequence}`;
  const width = 760;
  const height = 220;
  const padding = 16;
  const allValues = validSeries.flatMap((line) => line.values).filter(Number.isFinite);
  const min = options.min ?? Math.min(...allValues);
  const max = options.max ?? Math.max(...allValues);
  const totalPoints = Math.max(...validSeries.map((line) => line.values.length));
  const scaleX = (index) => padding + (index / Math.max(totalPoints - 1, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };
  const makePath = (values) => values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${scaleX(index)} ${scaleY(value)}`)
    .join(" ");

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const y = padding + ((height - padding * 2) / 4) * index;
    return `<line class="chart-grid-line" x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}"></line>`;
  }).join("");

  const thresholdPaths = (options.thresholds || []).map((threshold) => {
    const y = scaleY(threshold.value);
    return `<line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" stroke="${threshold.color}" stroke-dasharray="4 4" opacity="0.35"></line>`;
  }).join("");

  const firstSeries = validSeries[0];
  const areaPath = `${makePath(firstSeries.values)} L ${scaleX(totalPoints - 1)} ${height - padding} L ${scaleX(0)} ${height - padding} Z`;
  const gradients = validSeries.map((line, index) => `
    <linearGradient id="${chartId}-line-${index}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="${line.color}" stop-opacity="0.28"></stop>
      <stop offset="45%" stop-color="${line.color}" stop-opacity="0.94"></stop>
      <stop offset="100%" stop-color="${line.color}" stop-opacity="0.72"></stop>
    </linearGradient>
  `).join("");

  const linePaths = validSeries.map((line, index) => {
    const lastIndex = line.values
      .map((value, valueIndex) => ({ value, valueIndex }))
      .filter((item) => Number.isFinite(item.value))
      .pop();
    return `
      <path class="chart-line" pathLength="1" d="${makePath(line.values)}" stroke="url(#${chartId}-line-${index})" stroke-width="${line.strokeWidth || 2.2}" opacity="${line.opacity || 1}"></path>
      ${lastIndex ? `<circle class="chart-dot" cx="${scaleX(lastIndex.valueIndex)}" cy="${scaleY(lastIndex.value)}" r="3.2" fill="${line.color}" style="color:${line.color}"></circle>` : ""}
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        ${gradients}
        <linearGradient id="${chartId}-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${firstSeries.color}" stop-opacity="0.24"></stop>
          <stop offset="100%" stop-color="${firstSeries.color}" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      ${gridLines}
      ${thresholdPaths}
      <path class="chart-area" d="${areaPath}" fill="url(#${chartId}-area)"></path>
      ${linePaths}
    </svg>
  `;
};

const drawCandlestickChart = (container, candles, options = {}) => {
  if (!container) return;
  if (!candles || !candles.length) {
    container.classList.add("empty");
    container.innerHTML = `<p class='muted'>${escapeHtml(options.message || "Sem candles suficientes para este ativo.")}</p>`;
    return;
  }
  container.classList.remove("empty");

  const chartId = `candles-${++chartSequence}`;
  const width = 760;
  const height = 252;
  const padding = 18;
  const highs = candles.map((candle) => candle.high).filter(Number.isFinite);
  const lows = candles.map((candle) => candle.low).filter(Number.isFinite);
  const overlaySeries = Array.isArray(options.overlays) ? options.overlays : [];
  const overlayValues = overlaySeries
    .flatMap((series) => series.values || [])
    .filter(Number.isFinite);
  const volumes = candles.map((candle) => Number(candle.volume) || 0);
  const min = Math.min(...lows, ...overlayValues);
  const max = Math.max(...highs, ...overlayValues);
  const scaleX = (index) => padding + (index / Math.max(candles.length, 1)) * (width - padding * 2);
  const scaleY = (value) => {
    if (max === min) return height / 2;
    return height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  };
  const candleWidth = Math.max(4, (width - padding * 2) / Math.max(candles.length, 1) * 0.52);
  const volumeHeight = 34;
  const maxVolume = Math.max(...volumes, 1);

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const y = padding + ((height - padding * 2 - volumeHeight) / 4) * index;
    return `<line class="chart-grid-line" x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}"></line>`;
  }).join("");

  const volumeBars = candles.map((candle, index) => {
    const x = scaleX(index);
    const barHeight = ((Number(candle.volume) || 0) / maxVolume) * volumeHeight;
    return `<rect class="chart-volume-bar" x="${x - candleWidth / 2}" y="${height - padding - barHeight}" width="${candleWidth}" height="${barHeight}" rx="2"></rect>`;
  }).join("");

  const shapes = candles.map((candle, index) => {
    const x = scaleX(index);
    const openY = scaleY(candle.open);
    const closeY = scaleY(candle.close);
    const highY = scaleY(candle.high);
    const lowY = scaleY(candle.low);
    const rising = candle.close >= candle.open;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
    const colorClass = rising ? "chart-candle-up" : "chart-candle-down";
    const wickClass = rising ? "chart-wick-up" : "chart-wick-down";
    return `
      <line class="${wickClass}" x1="${x}" y1="${highY}" x2="${x}" y2="${lowY}" stroke-width="1.25" opacity="0.84"></line>
      <rect class="${colorClass}" x="${x - candleWidth / 2}" y="${bodyTop}" width="${candleWidth}" height="${bodyHeight}" rx="3" opacity="0.9"></rect>
    `;
  }).join("");

  const overlayPaths = overlaySeries.map((series, seriesIndex) => {
    const values = (series.values || []).slice(-candles.length);
    const path = values
      .map((value, index) => {
        if (!Number.isFinite(value)) return null;
        return `${index === 0 || !Number.isFinite(values[index - 1]) ? "M" : "L"} ${scaleX(index)} ${scaleY(value)}`;
      })
      .filter(Boolean)
      .join(" ");
    if (!path) return "";
    return `
      <path class="chart-overlay-line" d="${path}" stroke="${series.color || "#79dbff"}" stroke-width="${series.strokeWidth || 1.7}" opacity="${series.opacity || 0.88}"></path>
      <text class="chart-overlay-label" x="${padding + 8}" y="${padding + 14 + seriesIndex * 15}" fill="${series.color || "#79dbff"}">${escapeHtml(series.label)}</text>
    `;
  }).join("");

  const lastClose = candles.at(-1)?.close;
  const lastY = Number.isFinite(lastClose) ? scaleY(lastClose) : null;

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <radialGradient id="${chartId}-glow" cx="50%" cy="0%" r="80%">
          <stop offset="0%" stop-color="rgba(93, 242, 180, 0.22)"></stop>
          <stop offset="100%" stop-color="rgba(93, 242, 180, 0)"></stop>
        </radialGradient>
      </defs>
      <rect x="${padding}" y="${padding}" width="${width - padding * 2}" height="${height - padding * 2}" fill="url(#${chartId}-glow)" opacity="0.24"></rect>
      ${gridLines}
      ${volumeBars}
      ${shapes}
      ${overlayPaths}
      ${lastY ? `<line class="chart-price-line" x1="${padding}" y1="${lastY}" x2="${width - padding}" y2="${lastY}"></line>` : ""}
      ${lastY ? `<text class="chart-price-label" x="${width - padding - 62}" y="${Math.max(lastY - 6, 14)}">${formatNumber(lastClose, 4)}</text>` : ""}
    </svg>
  `;
};

const renderSourceHealth = (sources = []) => {
  const host = document.getElementById("source-health-list");
  if (!host) return;
  if (!sources.length) {
    host.innerHTML = "<div class='source-item' data-status='warning'><p class='muted'>Sem dados de integridade carregados ainda.</p></div>";
    return;
  }
  host.innerHTML = sources.map((source) => {
    const rawStatus = source.status || source.health || (source.ok === true ? "online" : source.ok === false ? "warning" : "warning");
    const status = String(rawStatus).toLowerCase();
    const detail = source.message || source.detail || source.note || "Sem detalhe adicional.";
    return `
      <article class="source-item" data-status="${escapeHtml(status)}">
        <div class="source-item-top">
          <p class="metric-label">${escapeHtml(source.source || source.label || "feed")}</p>
          <span class="source-status">
            <span class="source-status-dot"></span>
            ${status === "online" || status === "ok" ? "Disponível" : "Atenção"}
          </span>
        </div>
        <strong>${escapeHtml(source.updated_at || source.checked_at || source.status || "monitorado")}</strong>
        <p class="muted">${escapeHtml(detail)}</p>
      </article>
    `;
  }).join("");
};

const renderIntradayDecisions = (decisions = []) => {
  const host = document.getElementById("intraday-v2-grid");
  if (!host) return;
  if (!decisions.length) {
    host.innerHTML = "<div class='source-item' data-status='warning'><p class='muted'>Sem ciclo v2 registrado ainda.</p></div>";
    return;
  }
  host.innerHTML = decisions.map((decision) => {
    const reasons = (decision.block_reasons || []).map(displayBlockReason).join(", ") || displayBlockReason(decision.reason);
    const statusTone = toneFromText(decision.entry_status, reasons);
    return `
      <article class="source-item" data-status="${escapeHtml(statusTone)}">
        <div class="source-item-top">
          <p class="metric-label">${escapeHtml(decision.asset || "ativo")}</p>
          <span class="source-status">
            <span class="source-status-dot"></span>
            ${escapeHtml(decision.entry_status || "NO_TRADE")}
          </span>
        </div>
        <strong>${escapeHtml(displayDirection(decision.allowed_side))} | ${escapeHtml(displayRegime(decision.asset_context || "neutro"))}</strong>
        <p class="muted">${escapeHtml(reasons)}</p>
        <div class="signal-cluster">
          <span class="helper-pill info">Localização ${formatNumber(decision.zone, 2)}</span>
          <span class="helper-pill info">Volume relativo ${formatNumber(decision.rvol, 2)}</span>
          <span class="helper-pill warning">Pressão ${formatNumber(decision.imbalance, 2)}</span>
          <span class="helper-pill ${toneClass(statusTone)}">Risco/retorno ${formatNumber(decision.risk_reward, 2)}</span>
        </div>
      </article>
    `;
  }).join("");
};

const renderAssetSelector = () => {
  const select = document.getElementById("asset-select");
  const shortcuts = document.getElementById("asset-shortcuts");
  const assets = getAssets();
  if (!select || !shortcuts) return;

  if (!assets.length) {
    select.innerHTML = "<option value=''>Aguardando coleta</option>";
    shortcuts.innerHTML = "";
    return;
  }

  if (!state.selectedAsset || !assets.some((asset) => asset.asset === state.selectedAsset)) {
    const preferred = assets.find((asset) => ["USDBRL", "BRA50"].includes(asset.asset)) || assets[0];
    state.selectedAsset = preferred.asset;
  }

  select.innerHTML = assets.map((asset) => `
    <option value="${escapeHtml(asset.asset)}" ${state.selectedAsset === asset.asset ? "selected" : ""}>
      ${escapeHtml(asset.label || asset.asset)}
    </option>
  `).join("");
  select.onchange = (event) => selectAsset(event.target.value, "visao-ativo");

  shortcuts.innerHTML = assets.map((asset) => {
    const active = state.selectedAsset === asset.asset;
    const tone = toneFromText(asset.quant_report?.signal, asset.quant_report?.status);
    return `
      <button class="asset-shortcut ${active ? "active" : ""} ${toneClass(tone)}" type="button" data-asset-shortcut="${escapeHtml(asset.asset)}" aria-pressed="${active ? "true" : "false"}">
        <span>${assetEmoji(asset.asset)}</span>
        <strong>${escapeHtml(asset.asset)}</strong>
      </button>
    `;
  }).join("");
  shortcuts.querySelectorAll("[data-asset-shortcut]").forEach((button) => {
    button.addEventListener("click", () => selectAsset(button.dataset.assetShortcut, "visao-ativo"));
  });
};

const renderChartIndicatorControls = () => {
  const host = document.getElementById("chart-indicator-controls");
  if (!host) return;
  host.innerHTML = INDICATOR_OVERLAYS.map((indicator) => `
    <label class="indicator-check">
      <input type="checkbox" value="${escapeHtml(indicator.key)}" ${state.visibleIndicators[indicator.key] ? "checked" : ""}>
      <span>${escapeHtml(indicator.label)}</span>
    </label>
  `).join("");
  host.querySelectorAll("input[type='checkbox']").forEach((input) => {
    input.addEventListener("change", () => {
      state.visibleIndicators[input.value] = input.checked;
      renderSelectedAssetOverview();
    });
  });
};

const renderSelectedAssetIndicators = (asset, chartPayload, quantReport, decision, tone) => {
  const panel = document.getElementById("selected-asset-indicators");
  const body = document.getElementById("indicator-panel-body");
  const toggle = document.getElementById("indicator-panel-toggle");
  const toggleLabel = document.getElementById("indicator-panel-toggle-label");
  const summaryHost = document.getElementById("selected-indicator-summary");
  const detailsHost = document.getElementById("selected-indicator-details");
  if (!panel || !body || !toggle || !toggleLabel || !summaryHost || !detailsHost) return;

  toggle.setAttribute("aria-expanded", state.indicatorPanelOpen ? "true" : "false");
  toggleLabel.textContent = state.indicatorPanelOpen ? "Ocultar" : "Expandir";
  body.hidden = !state.indicatorPanelOpen;
  panel.classList.toggle("open", state.indicatorPanelOpen);

  if (!asset) {
    summaryHost.innerHTML = "";
    detailsHost.innerHTML = "";
    return;
  }

  const indicators = chartPayload?.indicators || [];
  const quantIndicators = chartPayload?.quant_indicators || [];
  const lastIndicator = indicators.at(-1) || {};
  const lastQuant = quantIndicators.at(-1) || {};
  const timeframe = timeframeLabel(state.currentTimeframe);

  summaryHost.innerHTML = [
    { label: "Preço médio", value: formatNumber(lastQuant.vwap ?? quantReport.vwap, 4), detail: "Referência do preço negociado", tone: "info" },
    { label: "Média curta", value: formatNumber(lastIndicator.ema_fast, 4), detail: "Mostra o ritmo mais recente", tone },
    { label: "Média lenta", value: formatNumber(lastIndicator.ema_slow, 4), detail: "Ajuda a filtrar a direção", tone },
    { label: "Força", value: formatNumber(lastIndicator.rsi, 1), detail: "Leitura de fôlego do movimento", tone: toneFromText(Number(lastIndicator.rsi) > 55 ? "alta" : Number(lastIndicator.rsi) < 45 ? "queda" : "neutro") },
  ].map((item) => `
    <div class="decision-box ${toneClass(item.tone)}">
      <p class="metric-label">${escapeHtml(item.label)}</p>
      <strong>${escapeHtml(item.value)}</strong>
      <p class="muted">${escapeHtml(item.detail)}</p>
    </div>
  `).join("");

  detailsHost.innerHTML = [
    { label: "Volume-chave", value: formatNumber(lastQuant.poc ?? quantReport.poc, 4), detail: "Região de maior participação" },
    { label: "Amplitude", value: formatNumber(lastQuant.atr ?? quantReport.atr, 4), detail: "Espaço médio de movimento" },
    { label: "Tendência", value: formatNumber(lastQuant.adx ?? quantReport.adx, 2), detail: "Quanto maior, mais limpa tende a ser a direção" },
    { label: "Tempo gráfico", value: timeframe, detail: chartPayload?.available === false ? "Sem dado real carregado" : "Dados reais carregados" },
    ...(asset.indicator_notes || []).slice(0, 3).map((note) => ({
      label: "Observação",
      value: "Leitura",
      detail: note,
    })),
  ].map((item) => `
    <div class="decision-box indicator-note-card">
      <p class="metric-label">${escapeHtml(item.label)}</p>
      <strong>${escapeHtml(item.value)}</strong>
      <p class="muted">${escapeHtml(item.detail)}</p>
    </div>
  `).join("");

  const priceSeries = [
    { color: "#f6c66f", values: indicators.map((item) => Number(item.close)) },
    { color: "#5df2b4", values: indicators.map((item) => Number(item.ema_fast)) },
    { color: "#ff6b7d", values: indicators.map((item) => Number(item.ema_slow)) },
  ];
  const quantSeries = [
    { color: "#79dbff", values: quantIndicators.map((item) => Number(item.vwap)), strokeWidth: 2.3 },
    { color: "#bb8dff", values: quantIndicators.map((item) => Number(item.poc)), strokeWidth: 1.9 },
    { color: "#f6c66f", values: quantIndicators.map((item) => Number(item.atr)), strokeWidth: 1.5 },
  ];
  const rsiSeries = [
    { color: "#bb8dff", values: indicators.map((item) => Number(item.rsi)), strokeWidth: 2.2 },
  ];

  drawLineChart(panel.querySelector(".indicator-price-chart"), priceSeries);
  drawLineChart(panel.querySelector(".indicator-quant-chart"), quantSeries);
  drawLineChart(panel.querySelector(".indicator-rsi-chart"), rsiSeries, {
    min: 0,
    max: 100,
    thresholds: [
      { value: 30, color: "#f27e8c" },
      { value: 50, color: "#dbc46d" },
      { value: 70, color: "#f27e8c" },
    ],
  });
};

const renderSelectedAssetOverview = () => {
  const asset = getSelectedAsset();
  const chartHost = document.getElementById("selected-asset-chart");
  const metricsHost = document.getElementById("selected-asset-metrics");
  const readingHost = document.getElementById("selected-asset-reading");
  if (!chartHost || !metricsHost || !readingHost) return;

  if (!asset) {
    setText("selected-asset-title", "Escolha um ativo");
    setText("selected-asset-subtitle", "Atualize o mercado para carregar os ativos disponíveis.");
    setText("selected-asset-bias", "Aguardando dados");
    setText("selected-asset-reason", "Nenhuma leitura disponível.");
    setText("selected-chart-title", "Preço e movimento");
    metricsHost.innerHTML = "";
    readingHost.innerHTML = "";
    renderChartIndicatorControls();
    renderSelectedAssetIndicators(null, null, {}, {}, "neutral");
    drawCandlestickChart(chartHost, []);
    return;
  }

  const decision = getDecisionMap().get(asset.asset) || {};
  const intraday = getIntradayDecisionMap().get(asset.asset) || {};
  const quantReport = asset.quant_report || {};
  const tone = toneFromText(quantReport.signal, quantReport.status, decision.execution_status, intraday.entry_status);
  const signal = displaySignal(quantReport.signal || decision.technical_direction || intraday.entry_status);
  const status = displayStatus(quantReport.status || decision.execution_status || intraday.entry_status);
  const chartPayload = getChartPayload(asset) || { label: timeframeLabel(state.currentTimeframe), candles: [] };
  const signalBadge = document.getElementById("selected-asset-signal");
  const reason = decision.stage_reason || quantReport.explanation || "Leitura aguardando confirmação dos dados.";

  setText("selected-asset-title", asset.label || asset.asset);
  setText("selected-asset-subtitle", `${asset.asset} | ${asset.ticker || "ativo monitorado"} | gráfico em ${timeframeLabel(state.currentTimeframe)}`);
  setText("selected-asset-bias", `${signal} agora`);
  setText("selected-asset-reason", reason);
  setText("selected-chart-title", `${timeframeLabel(state.currentTimeframe)} com indicadores selecionáveis`);
  if (signalBadge) {
    signalBadge.textContent = status;
    signalBadge.className = `tag ${toneClass(tone)}`.trim();
  }

  renderChartIndicatorControls();
  drawCandlestickChart(chartHost, chartPayload.candles || [], {
    message: chartPayload.message || "Sem dados reais para este tempo gráfico agora.",
    overlays: buildOverlaySeries(chartPayload, chartPayload.candles || []),
  });

  const actionHost = document.getElementById("selected-asset-action-list");
  if (actionHost) {
    actionHost.innerHTML = [
      { label: "Viés", value: signal, detail: status, tone },
      { label: "Preço atual", value: formatNumber(asset.latest?.price, 4), detail: `Variação ${formatPercent(asset.latest?.change_pct_4h)}`, tone: toneFromText(asset.latest?.change_pct_4h > 0 ? "alta" : "queda") },
      { label: "Mercado", value: displayRegime(quantReport.regime), detail: quantReport.volatilidade || "volatilidade sem leitura", tone: toneFromText(quantReport.regime) },
    ].map((item) => `
      <div class="decision-action ${toneClass(item.tone)}">
        <span>${escapeHtml(item.label)}</span>
        <strong>${escapeHtml(item.value)}</strong>
        <small>${escapeHtml(item.detail)}</small>
      </div>
    `).join("");
  }

  metricsHost.innerHTML = [
    { label: "Preço", value: formatNumber(asset.latest?.price, 4), detail: formatPercent(asset.latest?.change_pct_4h), tone },
    { label: "Direção provável", value: signal, detail: status, tone },
    { label: "Força do movimento", value: formatNumber(quantReport.score, 0), detail: displayRegime(quantReport.regime), tone: toneFromText(quantReport.regime, quantReport.score >= 70 ? "alta" : "") },
    { label: "Participação", value: quantReport.volume || "-", detail: `Volume ${formatCompactNumber(asset.latest?.volume_4h)}`, tone: toneFromText(quantReport.volume) },
    { label: "Risco x alvo", value: formatNumber(quantReport.risk_reward, 2), detail: quantReport.risk_reward ? "relação estimada" : "sem entrada liberada", tone: quantReport.risk_reward >= 2 ? "bullish" : "warning" },
  ].map((item) => `
    <article class="focus-metric ${toneClass(item.tone)}">
      <p>${escapeHtml(item.label)}</p>
      <strong>${escapeHtml(item.value)}</strong>
      <span>${escapeHtml(item.detail)}</span>
    </article>
  `).join("");

  readingHost.innerHTML = [
    {
      title: "O que isso significa",
      text: `${asset.label || asset.asset} está em modo ${displayRegime(quantReport.regime).toLowerCase()}. A orientação principal agora é ${signal.toLowerCase()}, com status ${status.toLowerCase()}.`,
    },
    {
      title: "Níveis de atenção",
      text: `Entrada ${formatNumber(quantReport.entrada, 4)}, proteção ${formatNumber(quantReport.stop, 4)} e alvo ${formatNumber(quantReport.alvo, 4)}. Quando não há entrada, esses campos ficam em espera.`,
    },
    {
      title: "Confirmações usadas",
      text: `Preço médio ${formatNumber(quantReport.vwap, 4)}, ponto de volume ${formatNumber(quantReport.poc, 4)}, força ${formatNumber(quantReport.adx, 2)} e amplitude ${formatNumber(quantReport.atr, 4)}.`,
    },
  ].map((item) => `
    <article class="reading-card panel">
      <p class="eyebrow">${escapeHtml(item.title)}</p>
      <p>${escapeHtml(item.text)}</p>
    </article>
  `).join("");

  renderSelectedAssetIndicators(asset, chartPayload, quantReport, decision, tone);
};

const renderCommandCenter = (dashboard) => {
  const macro = dashboard.macro_context || {};
  const news = dashboard.news_center || {};
  const actionableTrades = (dashboard.quant_reports || []).filter((report) => ["BUY", "SELL"].includes(report.signal)).length;

  setText("hero-operation-headline", macro.nao_operar ? "Mercado em observação" : "Mercado com leitura ativa");
  setText("hero-operation-reason", macro.motivo_nao_operar || "O ambiente permite acompanhar oportunidades com disciplina.");
  setText("hero-regime-value", String(macro.regime || "-").replaceAll("_", " "));
  setText("hero-score-value", formatNumber(macro.score, 0));
  setText("hero-bias-value", news.risk_bias || "neutro");
  setText("hero-setup-value", String(actionableTrades));

  const highlightHost = document.getElementById("hero-highlights");
  highlightHost.innerHTML = [
    {
      label: "Dólar global",
      value: `${formatNumber(macro.dxy_fred, 2)} / ${formatNumber(macro.dxy_rsi14, 1)}`,
      detail: "Ajuda a medir pressão no câmbio e apetite por proteção.",
    },
    {
      label: "Juros EUA",
      value: `${formatNumber(macro.us10y_fred, 2)} / ${formatNumber(macro.us10y_delta_5d, 2)}`,
      detail: "Mostra se o mercado está mais sensível a risco e liquidez.",
    },
    {
      label: "Eventos do dia",
      value: `${news.high_impact_count || 0} eventos / ${news.risk_bias || "neutro"}`,
      detail: "Notícias relevantes podem mudar o ritmo do mercado.",
    },
  ].map((item) => `
    <article class="hero-highlight">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <p>${escapeHtml(item.detail)}</p>
    </article>
  `).join("");
};

const renderOverview = (overview) => {
  setText("overview-title", overview.title || "Menu Principal");
  setText("overview-subtitle", overview.subtitle || "");
  const news = state.dashboard?.news_center || {};
  const macro = state.dashboard?.macro_context || {};
  const headline = (overview.macroflow_does || [])[0]
    || "Lê dólar global, juros, bolsa americana e calendário antes de apontar um viés.";
  const process = (overview.macroflow_does || [])[1]
    || "Mostra quando o mercado favorece compra, venda ou espera.";
  const operation = (overview.market_notes || [])[0]
    || "Quando a leitura não está clara, o sistema bloqueia a entrada e informa o motivo.";
  const newsSummary = news.summary
    || "Noticias e eventos economicos entram como camada complementar de vies e monitoramento.";

  const briefHost = document.getElementById("macroflow-brief");
  if (!briefHost) return;
  briefHost.innerHTML = `
    <div class="principal-brief-block">
      <span class="principal-brief-label">Leitura rápida</span>
      <p><strong>${escapeHtml(headline)}</strong></p>
      <p>${escapeHtml(process)}</p>
    </div>
    <div class="principal-brief-divider"></div>
    <div class="principal-brief-block">
      <span class="principal-brief-label">Direção do dia</span>
      <p><strong>Humor ${escapeHtml(String(macro.regime || "-").replaceAll("_", " "))}</strong> com confiança ${formatNumber(macro.score, 0)}. ${escapeHtml(operation)}</p>
    </div>
    <div class="principal-brief-divider"></div>
    <div class="principal-brief-block">
      <span class="principal-brief-label">Eventos importantes</span>
      <p><strong>${news.high_impact_count || 0} eventos de atenção</strong> com viés <strong>${escapeHtml(news.risk_bias || "neutro")}</strong>.</p>
      <p>${escapeHtml(newsSummary)}</p>
    </div>
  `;
};

const renderChartAssets = () => {
  const host = document.getElementById("chart-assets-grid");
  if (!host) return;
  const decisionMap = getDecisionMap();
  host.innerHTML = "";

  (state.dashboard?.market_assets || []).forEach((asset) => {
    const timeframe = state.currentTimeframe;
    const chartPayload = asset.charts?.[timeframe] || {
      candles: [],
      message: "Abra a Visão do Ativo para carregar este tempo gráfico.",
    };
    const decision = decisionMap.get(asset.asset);
    const quantReport = asset.quant_report || {};
    const tone = toneFromText(quantReport.signal, decision?.execution_status, decision?.technical_direction);
    const card = document.createElement("article");
    card.className = "asset-card panel";
    card.classList.toggle("selected", asset.asset === state.selectedAsset);
    card.dataset.tone = tone;
    card.innerHTML = `
      <div class="asset-top">
        <div class="asset-title">
          <span class="asset-icon">${assetEmoji(asset.asset)}</span>
          <div>
            <p class="eyebrow">${escapeHtml(asset.asset)}</p>
            <h3>${escapeHtml(asset.label)}</h3>
            <p class="muted">${escapeHtml(asset.description || "Ativo acompanhado pelo MacroFlow.")}</p>
          </div>
        </div>
        <div class="signal-cluster">
          <span class="tag ${toneClass(tone)}">${escapeHtml(displaySignal(quantReport.signal || decision?.technical_direction))}</span>
          <button class="secondary-button" type="button" data-focus-asset="${escapeHtml(asset.asset)}">Ver ativo</button>
        </div>
      </div>
      <div class="latest-metrics">
        <div class="metric-box" data-tone="${tone}">
          <p class="metric-label">Preço agora</p>
          <strong>${formatNumber(asset.latest?.price, 4)}</strong>
          <p class="muted">Var. ${formatPercent(asset.latest?.change_pct_4h)}</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Participação</p>
          <strong>${formatCompactNumber(asset.latest?.volume_4h)}</strong>
          <p class="muted">${escapeHtml(quantReport.volume || "sem leitura")}</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Força</p>
          <strong>${formatNumber(quantReport.score, 0)}</strong>
          <p class="muted">${escapeHtml(displayRegime(quantReport.regime))}</p>
        </div>
        <div class="metric-box">
          <p class="metric-label">Status</p>
          <strong>${escapeHtml(displayStatus(quantReport.status || decision?.execution_status))}</strong>
          <p class="muted">${escapeHtml(timeframeLabel(timeframe))} • ${escapeHtml(asset.ticker)}</p>
        </div>
      </div>
      <div class="chart-box"></div>
      <div class="signal-cluster">
        <span class="helper-pill ${toneClass(tone)}">${escapeHtml(displayDirection(decision?.technical_direction))}</span>
        <span class="helper-pill info">Preço médio ${formatNumber(quantReport.vwap, 4)}</span>
        <span class="helper-pill warning">Volume-chave ${formatNumber(quantReport.poc, 4)}</span>
        <span class="helper-pill ${quantReport.volume === "acima da média" ? "bullish" : ""}">${escapeHtml(quantReport.volume || "volume sem leitura")}</span>
      </div>
      <p class="muted">${escapeHtml(decision?.stage_reason || quantReport.explanation || asset.description)}</p>
    `;
    drawCandlestickChart(card.querySelector(".chart-box"), chartPayload.candles || [], {
      message: chartPayload.message || "Abra a Visão do Ativo para carregar este tempo gráfico.",
    });
    card.querySelector("[data-focus-asset]")?.addEventListener("click", () => selectAsset(asset.asset, "visao-ativo"));
    host.appendChild(card);
  });
};

const renderNews = (newsCenter) => {
  setText("news-title", newsCenter.title || "Noticias do Mercado Financeiro");
  setText("news-summary", newsCenter.summary || "");
  const newsStatus = setText("news-status", newsCenter.status || "planejamento");
  if (newsStatus) {
    newsStatus.className = `tag subtle ${toneClass(toneFromText(newsCenter.status))}`.trim();
  }
  const newsRiskBias = setText("news-risk-bias", `Vies ${newsCenter.risk_bias || "neutro"}`);
  if (newsRiskBias) {
    newsRiskBias.className = `tag ${toneClass(toneFromText(newsCenter.risk_bias))}`.trim();
  }
  setText("news-source-note", `${newsCenter.source || "Trading Economics"} | ${newsCenter.window?.start || "-"} a ${newsCenter.window?.end || "-"}`);

  const countryFilter = document.getElementById("news-country-filter");
  const importanceFilter = document.getElementById("news-importance-filter");
  const host = document.getElementById("economic-calendar-grid");
  if (!countryFilter || !importanceFilter || !host) return;
  const sourceCountries = newsCenter.countries?.length ? newsCenter.countries : (newsCenter.configured_countries || []);
  const countries = ["ALL", ...sourceCountries];
  if (!countries.includes(state.newsCountry)) state.newsCountry = "ALL";
  countryFilter.innerHTML = countries.map((country) => `
    <option value="${escapeHtml(country)}" ${state.newsCountry === country ? "selected" : ""}>
      ${country === "ALL" ? "Todos os países" : escapeHtml(country)}
    </option>
  `).join("");
  importanceFilter.value = state.newsImportance;

  countryFilter.onchange = () => {
    state.newsCountry = countryFilter.value;
    renderNews(state.dashboard?.news_center || {});
  };
  importanceFilter.onchange = (event) => {
    state.newsImportance = event.target.value;
    renderNews(state.dashboard?.news_center || {});
  };

  const events = (newsCenter.events || []).filter((event) => {
    const countryMatch = state.newsCountry === "ALL" || event.country === state.newsCountry;
    const importanceMatch = state.newsImportance === "ALL" || String(event.importance) === state.newsImportance;
    return countryMatch && importanceMatch;
  });
  if (!events.length) {
    host.innerHTML = "<article class='panel info-card'><p class='muted'>Sem eventos para os filtros selecionados.</p></article>";
    return;
  }
  host.innerHTML = events.map((event) => `
    <article class="calendar-event panel" data-importance="${escapeHtml(event.importance || 0)}">
      <div class="calendar-event-top">
        <div>
          <p class="eyebrow">${escapeHtml(event.country)} | ${escapeHtml(event.category)}</p>
          <h3>${escapeHtml(event.event)}</h3>
          <p class="muted">${escapeHtml(event.date || "-")}</p>
        </div>
        <div class="signal-cluster">
          <span class="tag warning">${renderBulls(event.importance)} ${escapeHtml(event.importance_label || `${event.importance} touros`)}</span>
          <span class="tag ${toneClass(toneFromText(event.market_bias))}">${escapeHtml(event.market_bias || "monitorar")}</span>
        </div>
      </div>
      <div class="calendar-values">
        <div><p class="metric-label">Realizado</p><strong>${escapeHtml(event.actual || "-")}</strong></div>
        <div><p class="metric-label">Esperado</p><strong>${escapeHtml(event.forecast || event.te_forecast || "-")}</strong></div>
        <div><p class="metric-label">Anterior</p><strong>${escapeHtml(event.previous || "-")}</strong></div>
        <div><p class="metric-label">Impacto</p><strong>${escapeHtml(event.surprise || "-")} / ${escapeHtml(event.market_bias || "monitorar")}</strong></div>
      </div>
      <div class="calendar-impact">
        <p class="muted">${escapeHtml(event.projection || "Monitorar impacto com DXY, US10Y e SPX.")}</p>
        <span class="helper-pill ${toneClass(toneFromText(event.theme || event.category))}">${escapeHtml(event.theme || event.category || "macro")}</span>
      </div>
    </article>
  `).join("");
};

const renderSettings = (settingsPanel) => {
  const form = document.getElementById("settings-form");
  if (!form) return;
  setText("settings-note", settingsPanel.runtime_note || "");
  setText("refresh-button", settingsPanel.operational_button_label || "Atualizar mercado");
  form.replaceChildren();

  (settingsPanel.groups || []).forEach((group) => {
    const section = document.createElement("section");
    section.className = "setting-group panel";
    section.dataset.groupId = String(group.id || "");

    const header = document.createElement("div");
    header.className = "setting-group-header";

    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = group.title || "";

    const description = document.createElement("p");
    description.textContent = group.description || "";

    header.append(eyebrow, description);

    const fields = document.createElement("div");
    fields.className = "setting-group-fields";

    (group.fields || []).forEach((field) => {
      const wrapper = document.createElement("div");
      wrapper.className = "setting-field";

      const label = document.createElement("label");
      label.textContent = field.label || "";

      let control;
      if (field.type === "select") {
        control = document.createElement("select");
        (field.options || []).forEach((option) => {
          const optionElement = document.createElement("option");
          optionElement.value = String(option);
          optionElement.textContent = String(option);
          optionElement.selected = String(field.value) === String(option);
          control.appendChild(optionElement);
        });
      } else {
        control = document.createElement("input");
        control.type = field.type || "text";
        control.value = field.value ?? "";
        control.placeholder = field.configured ? "Chave configurada" : (field.placeholder || "");
        if (field.step !== undefined) {
          control.step = String(field.step);
        }
      }

      control.dataset.env = String(field.env || "");
      control.dataset.secret = field.secret ? "1" : "0";
      control.dataset.group = String(group.id || "");

      const help = document.createElement("small");
      help.textContent = field.help || "";

      wrapper.append(label, control, help);
      fields.appendChild(wrapper);
    });

    const actions = document.createElement("div");
    actions.className = "settings-actions";

    const button = document.createElement("button");
    button.className = "primary-button settings-save-button";
    button.type = "button";
    button.dataset.saveGroup = String(group.id || "");
    button.textContent = group.save_label || settingsPanel.save_label || "Salvar configuracoes";

    const feedback = document.createElement("span");
    feedback.className = "muted settings-feedback";
    feedback.dataset.feedbackGroup = String(group.id || "");

    actions.append(button, feedback);
    section.append(header, fields, actions);
    form.appendChild(section);
  });
};

const renderDashboard = (dashboard) => {
  state.dashboard = dashboard;
  state.currentTimeframe = dashboard.summary?.default_chart_timeframe || state.currentTimeframe || "4H";
  if (!getTimeframeOptions().some((timeframe) => timeframe.value === state.currentTimeframe)) {
    state.currentTimeframe = "4H";
  }
  if (!state.selectedAsset && (dashboard.market_assets || []).length) {
    const preferred = dashboard.market_assets.find((asset) => ["USDBRL", "BRA50"].includes(asset.asset)) || dashboard.market_assets[0];
    state.selectedAsset = preferred.asset;
  }

  renderCommandCenter(dashboard);
  renderTimeframeSwitches();
  renderAssetSelector();
  renderSelectedAssetOverview();
  renderOverview(dashboard.market_overview || {});
  renderSourceHealth(dashboard.source_health || []);
  renderIntradayDecisions(dashboard.intraday_decisions || []);
  renderChartAssets();
  renderNews(dashboard.news_center || {});
  renderSettings(dashboard.settings_panel || {});
  loadSelectedChartIfNeeded();
};

const loadDashboard = async () => {
  const response = await fetch("/api/dashboard");
  if (!response.ok) throw new Error("Falha ao carregar o dashboard.");
  const dashboard = await response.json();
  renderDashboard(dashboard);
};

const refreshDashboard = async () => {
  const button = document.getElementById("refresh-button");
  button.disabled = true;
  button.textContent = "Atualizando...";
  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao atualizar");
    renderDashboard(payload.state);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = state.dashboard?.settings_panel?.operational_button_label || "Atualizar mercado";
  }
};

const saveSettings = async (groupId) => {
  let button = document.querySelector(`[data-save-group="${groupId}"]`);
  let feedback = document.querySelector(`[data-feedback-group="${groupId}"]`);
  const values = {};

  document.querySelectorAll(`#settings-form [data-group="${groupId}"][data-env]`).forEach((input) => {
    const env = input.dataset.env;
    const secret = input.dataset.secret === "1";
    const value = String(input.value ?? "").trim();
    if (secret && !value) return;
    values[env] = value;
  });

  if (!button || !feedback) return;
  button.disabled = true;
  feedback.textContent = "Salvando...";
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao salvar configurações");

    state.dashboard = state.dashboard || {};
    state.dashboard.settings_panel = payload.settings;
    renderSettings(payload.settings);
    button = document.querySelector(`[data-save-group="${groupId}"]`);
    feedback = document.querySelector(`[data-feedback-group="${groupId}"]`);
    const chartField = payload.settings.groups
      .flatMap((group) => group.fields)
      .find((field) => field.env === "MACROFLOW_CHART_DEFAULT_TIMEFRAME");
    if (chartField?.value) {
      state.currentTimeframe = chartField.value;
      renderTimeframeSwitches();
      renderSelectedAssetOverview();
      renderChartAssets();
      loadSelectedChartIfNeeded();
    }
    if (feedback) {
      feedback.textContent = "Alterações salvas. Clique em Iniciar Macroflow para aplicar na próxima coleta.";
    }
  } catch (error) {
    if (feedback) {
      feedback.textContent = error.message;
    }
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
};

const addJarvisMessage = (role, content) => {
  const host = document.getElementById("jarvis-messages");
  if (!host) return;
  const message = document.createElement("div");
  message.className = `jarvis-message ${role}`;
  message.innerHTML = `<p>${escapeHtml(content).replaceAll("\n", "<br>")}</p>`;
  host.appendChild(message);
  host.scrollTop = host.scrollHeight;
};

const toggleJarvis = (open) => {
  document.getElementById("jarvis-panel")?.classList.toggle("open", open);
  document.getElementById("jarvis-toggle")?.classList.toggle("hidden", open);
  if (open && !state.jarvisHistory.length) {
    addJarvisMessage(
      "assistant",
      "Jarvis online. Me pergunte sobre o ativo selecionado, o viés do dia ou notícias importantes.",
    );
  }
  if (open) document.getElementById("jarvis-input")?.focus();
};

const submitJarvisMessage = async (event) => {
  event.preventDefault();
  const input = document.getElementById("jarvis-input");
  const message = String(input.value || "").trim();
  if (!message) return;
  input.value = "";
  addJarvisMessage("user", message);
  state.jarvisHistory.push({ role: "user", content: message });

  const thinking = "Analisando snapshot do MacroFlow...";
  addJarvisMessage("assistant pending", thinking);
  try {
    const response = await fetch("/api/jarvis/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: state.jarvisHistory.slice(-8) }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Falha ao consultar o Jarvis.");
    document.querySelector("#jarvis-messages .pending:last-child")?.remove();
    addJarvisMessage("assistant", payload.reply || "Sem resposta do Jarvis.");
    state.jarvisHistory.push({ role: "assistant", content: payload.reply || "" });
  } catch (error) {
    document.querySelector("#jarvis-messages .pending:last-child")?.remove();
    addJarvisMessage("assistant", error.message);
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
  document.getElementById("refresh-button")?.addEventListener("click", refreshDashboard);
  document.getElementById("indicator-panel-toggle")?.addEventListener("click", () => {
    state.indicatorPanelOpen = !state.indicatorPanelOpen;
    renderSelectedAssetOverview();
  });
  document.getElementById("settings-form")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-save-group]");
    if (!button) return;
    saveSettings(button.dataset.saveGroup || "");
  });
  document.getElementById("jarvis-toggle")?.addEventListener("click", () => toggleJarvis(true));
  document.getElementById("jarvis-close")?.addEventListener("click", () => toggleJarvis(false));
  document.getElementById("jarvis-form")?.addEventListener("submit", submitJarvisMessage);
  document.querySelectorAll("[data-jarvis-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleJarvis(true);
      const input = document.getElementById("jarvis-input");
      if (!input) return;
      input.value = button.dataset.jarvisPrompt || "";
      input.focus();
    });
  });
  setActiveTab(state.currentTab);
  try {
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});
