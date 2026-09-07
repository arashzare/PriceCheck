import requests
from typing import Dict

# Fallback rates if API call fails
FALLBACK_RATES: Dict[str, float] = {
    "USD": 1.36,
    "EUR": 1.48,
    "GBP": 1.76,
    "CAD": 1.00,
    "CNY": 0.19,
    "HKD": 0.17
}

_CACHED_RATES = None

def get_cad_exchange_rates() -> Dict[str, float]:
    global _CACHED_RATES
    if _CACHED_RATES is not None:
        return _CACHED_RATES
    
    try:
        # Free open exchange rate API (no API key needed)
        resp = requests.get("https://open.er-api.com/v6/latest/CAD", timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rates_from_cad = data.get("rates", {})
            # We want conversion TO CAD (i.e. 1 USD = X CAD)
            converted = {}
            for curr, rate in rates_from_cad.items():
                if rate > 0:
                    converted[curr] = 1.0 / rate
            converted["CAD"] = 1.00
            _CACHED_RATES = converted
            return _CACHED_RATES
    except Exception as e:
        print(f"[Currency] Warning: Could not fetch live FX rates ({e}), using fallback rates.")
    
    _CACHED_RATES = FALLBACK_RATES
    return _CACHED_RATES

def convert_to_cad(amount: float, from_currency: str) -> float:
    from_currency = from_currency.upper().strip()
    if from_currency in ["CAD", "C$", "CDN$", "CA$"]:
        return amount
    
    rates = get_cad_exchange_rates()
    multiplier = rates.get(from_currency, FALLBACK_RATES.get(from_currency, 1.36))
    return amount * multiplier
