from __future__ import annotations

import logging
import json
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree

import requests

from .config import AppSettings


logger = logging.getLogger("macroflow.economic_calendar")


CURRENCY_TO_COUNTRY = {
    "USD": "United States",
    "BRL": "Brazil",
    "EUR": "Euro Area",
    "CNY": "China",
    "JPY": "Japan",
    "GBP": "United Kingdom",
    "CAD": "Canada",
    "AUD": "Australia",
    "NZD": "New Zealand",
    "CHF": "Switzerland",
    "ALL": "Global",
}

COUNTRY_TO_CURRENCY = {country.lower(): currency for currency, country in CURRENCY_TO_COUNTRY.items()}
IMPACT_TO_IMPORTANCE = {"low": 1, "medium": 2, "high": 3}


def _split_countries(raw: str) -> list[str]:
    countries = [item.strip() for item in raw.split(",") if item.strip()]
    return countries or ["All"]


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    multiplier = 1.0
    if text[-1:].upper() == "K":
        multiplier = 1_000.0
        text = text[:-1]
    elif text[-1:].upper() == "M":
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text[-1:].upper() == "B":
        multiplier = 1_000_000_000.0
        text = text[:-1]
    cleaned = re.sub(r"[^0-9,.\-]", "", text)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _event_theme(category: str, event: str) -> str:
    text = f"{category} {event}".lower()
    if any(term in text for term in ["inflation", "cpi", "ppi", "price", "deflator"]):
        return "inflation"
    if any(term in text for term in ["interest rate", "fed", "central bank", "fomc", "copom", "monetary"]):
        return "rates"
    if any(term in text for term in ["unemployment", "jobless", "payroll", "employment", "wage"]):
        return "labor"
    if any(term in text for term in ["gdp", "retail", "pmi", "industrial", "manufacturing", "services"]):
        return "growth"
    if any(term in text for term in ["trade", "current account", "budget"]):
        return "external_balance"
    return "general"


def _projection_for_event(item: dict[str, Any]) -> dict[str, str | float | None]:
    actual = _parse_number(item.get("Actual"))
    forecast = _parse_number(item.get("Forecast")) or _parse_number(item.get("TEForecast"))
    previous = _parse_number(item.get("Previous"))
    reference = forecast if forecast is not None else previous
    theme = _event_theme(str(item.get("Category", "")), str(item.get("Event", "")))

    if actual is None or reference is None:
        return {
            "theme": theme,
            "surprise": None,
            "market_bias": "monitorar",
            "projection": "Evento aguardado ou sem consenso numerico; usar como alerta de volatilidade, nao como direcao isolada.",
        }

    surprise = actual - reference
    if abs(surprise) < 1e-12:
        return {
            "theme": theme,
            "surprise": 0.0,
            "market_bias": "neutro",
            "projection": "Resultado em linha com a referencia; impacto direcional tende a ser limitado.",
        }

    positive_surprise = surprise > 0
    if theme in {"inflation", "rates"}:
        market_bias = "risk_off" if positive_surprise else "risk_on"
        projection = (
            "Surpresa altista em inflacao/juros tende a pressionar juros, fortalecer USD e reduzir apetite a risco."
            if positive_surprise
            else "Surpresa baixista em inflacao/juros tende a aliviar juros e favorecer apetite a risco."
        )
    elif theme == "labor" and "unemployment" in str(item.get("Event", "")).lower():
        market_bias = "risk_off" if positive_surprise else "risk_on"
        projection = (
            "Desemprego acima da referencia sugere enfraquecimento de atividade e pede cautela em risco."
            if positive_surprise
            else "Desemprego abaixo da referencia sugere mercado de trabalho firme; pode favorecer risco, mas tambem pressionar juros."
        )
    elif theme in {"labor", "growth"}:
        market_bias = "risk_on" if positive_surprise else "risk_off"
        projection = (
            "Surpresa positiva de atividade/emprego tende a favorecer crescimento e ativos de risco; monitorar efeito em juros."
            if positive_surprise
            else "Surpresa negativa de atividade/emprego tende a reduzir apetite a risco e reforcar postura defensiva."
        )
    else:
        market_bias = "risk_on" if positive_surprise else "risk_off"
        projection = "Surpresa relevante contra a referencia; validar impacto com DXY, US10Y e SPX antes de agir."

    return {
        "theme": theme,
        "surprise": surprise,
        "market_bias": market_bias,
        "projection": projection,
    }


def _normalize_event(item: dict[str, Any]) -> dict[str, Any]:
    importance = int(item.get("Importance") or 0)
    projection = _projection_for_event(item)
    source_url = item.get("SourceURL") or ""
    relative_url = item.get("URL") or ""
    return {
        "id": str(item.get("CalendarId") or ""),
        "date": item.get("Date") or "",
        "country": item.get("Country") or "N/A",
        "category": item.get("Category") or "N/A",
        "event": item.get("Event") or "Evento economico",
        "reference": item.get("Reference") or "",
        "actual": item.get("Actual") or "",
        "previous": item.get("Previous") or "",
        "forecast": item.get("Forecast") or "",
        "te_forecast": item.get("TEForecast") or "",
        "importance": importance,
        "importance_label": f"{importance} touro" if importance == 1 else f"{importance} touros",
        "source": item.get("Source") or "Trading Economics",
        "source_url": source_url,
        "url": f"https://tradingeconomics.com{relative_url}" if relative_url.startswith("/") else relative_url,
        "theme": projection["theme"],
        "surprise": projection["surprise"],
        "market_bias": projection["market_bias"],
        "projection": projection["projection"],
    }


def fetch_economic_calendar(settings: AppSettings, today: date | None = None) -> dict[str, Any]:
    if not settings.calendar.enabled:
        return {
            "ok": False,
            "status": "desabilitado",
            "events": [],
            "countries": [],
            "importance_levels": [1, 2, 3],
            "message": "Calendario economico desabilitado nas configuracoes.",
        }
    if settings.calendar.provider in {"forexfactory", "faireconomy"}:
        return _fetch_forexfactory_calendar(settings, today=today)
    if settings.calendar.provider != "tradingeconomics":
        return {
            "ok": False,
            "status": "provider_nao_suportado",
            "events": [],
            "countries": [],
            "importance_levels": [1, 2, 3],
            "message": f"Provider de calendario nao suportado: {settings.calendar.provider}.",
        }

    today = today or datetime.now().date()
    start = today - timedelta(days=max(settings.calendar.days_back, 0))
    end = today + timedelta(days=max(settings.calendar.days_ahead, 0))
    countries = _split_countries(settings.calendar.countries)
    country_path = quote(",".join(countries), safe=",")
    url = f"https://api.tradingeconomics.com/calendar/country/{country_path}/{start:%Y-%m-%d}/{end:%Y-%m-%d}"
    try:
        response = requests.get(
            url,
            params={"c": settings.calendar.api_key, "f": "json"},
            timeout=settings.calendar.timeout_seconds,
        )
        response.raise_for_status()
        raw_events = response.json()
        if not isinstance(raw_events, list):
            raise ValueError("Resposta inesperada do calendario economico.")
    except Exception as exc:
        logger.warning("Falha ao carregar calendario economico: %s", exc)
        return {
            "ok": False,
            "status": "indisponivel",
            "events": [],
            "countries": countries,
            "importance_levels": [1, 2, 3],
            "message": "Calendario economico indisponivel; tente novamente no proximo refresh.",
            "source": "Trading Economics",
            "source_url": "https://docs.tradingeconomics.com/economic_calendar/snapshot/",
        }

    min_importance = max(1, min(3, settings.calendar.importance_min))
    events = [
        _normalize_event(item)
        for item in raw_events
        if int(item.get("Importance") or 0) >= min_importance
    ]
    events = sorted(events, key=lambda item: item.get("date") or "")[: settings.calendar.max_events]
    available_countries = sorted({str(item["country"]) for item in events if item.get("country")})
    high_impact = len([item for item in events if item.get("importance") == 3])
    risk_bias = _aggregate_market_bias(events)
    return {
        "ok": True,
        "status": "online",
        "source": "Trading Economics",
        "source_url": "https://docs.tradingeconomics.com/economic_calendar/snapshot/",
        "window": {"start": f"{start:%Y-%m-%d}", "end": f"{end:%Y-%m-%d}"},
        "events": events,
        "countries": available_countries,
        "configured_countries": countries,
        "importance_levels": [1, 2, 3],
        "high_impact_count": high_impact,
        "risk_bias": risk_bias,
        "message": f"{len(events)} eventos economicos carregados para a janela {start:%Y-%m-%d} a {end:%Y-%m-%d}.",
    }


def _selected_currency_codes(countries: list[str]) -> set[str]:
    codes = set()
    for country in countries:
        normalized = country.strip()
        if not normalized:
            continue
        upper = normalized.upper()
        if upper in CURRENCY_TO_COUNTRY:
            codes.add(upper)
            continue
        mapped = COUNTRY_TO_CURRENCY.get(normalized.lower())
        if mapped:
            codes.add(mapped)
    return codes


def _fetch_forexfactory_calendar(settings: AppSettings, today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now().date()
    start = today - timedelta(days=max(settings.calendar.days_back, 0))
    end = today + timedelta(days=max(settings.calendar.days_ahead, 0))
    countries = _split_countries(settings.calendar.countries)
    selected_codes = _selected_currency_codes(countries)
    try:
        response = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "MacroFlow/1.0 (+local dashboard)"},
            timeout=settings.calendar.timeout_seconds,
        )
        response.raise_for_status()
        raw_events = response.json()
        if not isinstance(raw_events, list):
            raise ValueError("Resposta inesperada do calendario Fair Economy.")
    except Exception as exc:
        logger.info("Feed JSON Fair Economy indisponivel; tentando XML: %s", exc)
        try:
            raw_events = _fetch_forexfactory_xml_events(settings)
        except Exception as xml_exc:
            logger.warning("Falha ao carregar fallback XML Fair Economy: %s", xml_exc)
            raw_events = None
        if raw_events is None:
            cached = _load_calendar_cache(settings)
            if cached:
                cached["status"] = "cache"
                cached["message"] = "Fonte de calendario indisponivel/rate-limited; usando ultimo cache local valido."
                return cached
            return {
                "ok": False,
                "status": "indisponivel",
                "events": [],
                "countries": countries,
                "importance_levels": [1, 2, 3],
                "message": "Calendario economico indisponivel; tente novamente no proximo refresh.",
                "source": "Fair Economy / Forex Factory",
                "source_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            }

    if raw_events is None:
        cached = _load_calendar_cache(settings)
        if cached:
            cached["status"] = "cache"
            cached["message"] = "Fonte de calendario indisponivel/rate-limited; usando ultimo cache local valido."
            return cached
        raw_events = []

    min_importance = max(1, min(3, settings.calendar.importance_min))
    events = []
    for item in raw_events:
        event = _normalize_forexfactory_event(item)
        event_date = _event_date(event.get("date"))
        if event["importance"] < min_importance:
            continue
        if selected_codes and event.get("currency") not in selected_codes and event.get("currency") != "ALL":
            continue
        if event_date and not (start <= event_date <= end):
            continue
        events.append(event)

    events = sorted(events, key=lambda item: item.get("date") or "")[: settings.calendar.max_events]
    available_countries = sorted({str(item["country"]) for item in events if item.get("country")})
    payload = {
        "ok": True,
        "status": "online",
        "source": "Fair Economy / Forex Factory",
        "source_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "window": {"start": f"{start:%Y-%m-%d}", "end": f"{end:%Y-%m-%d}"},
        "events": events,
        "countries": available_countries,
        "configured_countries": countries,
        "importance_levels": [1, 2, 3],
        "high_impact_count": len([item for item in events if item.get("importance") == 3]),
        "risk_bias": _aggregate_market_bias(events),
        "message": f"{len(events)} eventos economicos carregados para a janela {start:%Y-%m-%d} a {end:%Y-%m-%d}.",
    }
    _save_calendar_cache(settings, payload)
    return payload


def _calendar_cache_path(settings: AppSettings):
    return settings.storage.runtime_dir / "economic_calendar_cache.json"


def _fetch_forexfactory_xml_events(settings: AppSettings) -> list[dict[str, Any]]:
    response = requests.get(
        "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
        headers={"User-Agent": "MacroFlow/1.0 (+local dashboard)"},
        timeout=settings.calendar.timeout_seconds,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    events = []
    for event in root.findall("event"):
        events.append(
            {
                "title": _xml_text(event, "title"),
                "country": _xml_text(event, "country"),
                "date": _xml_text(event, "date"),
                "impact": _xml_text(event, "impact"),
                "forecast": _xml_text(event, "forecast"),
                "previous": _xml_text(event, "previous"),
                "actual": _xml_text(event, "actual"),
            }
        )
    return events


def _xml_text(event, tag: str) -> str:
    node = event.find(tag)
    return "" if node is None or node.text is None else node.text.strip()


def _load_calendar_cache(settings: AppSettings) -> dict[str, Any] | None:
    path = _calendar_cache_path(settings)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Cache de calendario invalido em %s; ignorando.", path)
        return None


def _save_calendar_cache(settings: AppSettings, payload: dict[str, Any]) -> None:
    path = _calendar_cache_path(settings)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Falha ao salvar cache do calendario economico: %s", exc)


def _event_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_forexfactory_event(item: dict[str, Any]) -> dict[str, Any]:
    impact = str(item.get("impact") or "").lower()
    importance = IMPACT_TO_IMPORTANCE.get(impact, 0)
    currency = str(item.get("country") or "").upper()
    country = CURRENCY_TO_COUNTRY.get(currency, currency or "N/A")
    te_like_item = {
        "Actual": item.get("actual") or "",
        "Forecast": item.get("forecast") or "",
        "Previous": item.get("previous") or "",
        "Category": "Economic Calendar",
        "Event": item.get("title") or "",
    }
    projection = _projection_for_event(te_like_item)
    return {
        "id": f"{currency}:{item.get('date')}:{item.get('title')}",
        "date": item.get("date") or "",
        "country": country,
        "currency": currency,
        "category": "Economic Calendar",
        "event": item.get("title") or "Evento economico",
        "reference": "",
        "actual": item.get("actual") or "",
        "previous": item.get("previous") or "",
        "forecast": item.get("forecast") or "",
        "te_forecast": "",
        "importance": importance,
        "importance_label": f"{importance} touro" if importance == 1 else f"{importance} touros",
        "source": "Fair Economy / Forex Factory",
        "source_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "url": "",
        "theme": projection["theme"],
        "surprise": projection["surprise"],
        "market_bias": projection["market_bias"],
        "projection": projection["projection"],
    }


def _aggregate_market_bias(events: list[dict[str, Any]]) -> str:
    weights = {"risk_on": 0, "risk_off": 0}
    for event in events:
        bias = event.get("market_bias")
        if bias in weights:
            weights[bias] += int(event.get("importance") or 1)
    if weights["risk_on"] > weights["risk_off"]:
        return "risk_on"
    if weights["risk_off"] > weights["risk_on"]:
        return "risk_off"
    return "neutro"
