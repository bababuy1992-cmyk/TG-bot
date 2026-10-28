import requests
from config import WALLET_ADDRESS, TONCENTER_API_KEY, PRICE_TON_RUB as PRICE_RUB

# How many recent transactions to scan (increased for busy wallets)
TX_SCAN_LIMIT = 100

def get_ton_to_rub_rate() -> float:
    """Fetch live TON/RUB rate from CoinGecko. Falls back to 700 if API is down."""
    try:
        url = (
            'https://api.coingecko.com/api/v3/simple/price'
            '?ids=the-open-network&vs_currencies=rub'
        )
        res = requests.get(url, timeout=8)
        res.raise_for_status()
        return float(res.json()['the-open-network']['rub'])
    except Exception as e:
        print(f"[ton_payment] Rate fetch error: {e}. Using fallback 700.")
        return 700.0

def get_price_in_ton(price_rub: float = PRICE_RUB) -> float:
    rate = get_ton_to_rub_rate()
    return round(price_rub / rate, 4)   # 4 decimal places for accuracy

def check_transaction(comment: str, expected_amount_ton: float) -> bool:
    """
    Scans the last TX_SCAN_LIMIT transactions on the wallet.
    Returns True when a matching payment (correct memo + sufficient amount) is found.
    Allows ±2% rounding tolerance.
    """
    try:
        url = (
            f'https://toncenter.com/api/v2/getTransactions'
            f'?address={WALLET_ADDRESS}'
            f'&limit={TX_SCAN_LIMIT}'
            f'&api_key={TONCENTER_API_KEY}'
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data.get('ok'):
            print(f"[ton_payment] Toncenter not OK: {data}")
            return False

        tolerance = 0.98   # accept payments that are within 2% of the target
        min_amount = expected_amount_ton * tolerance

        for tx in data.get('result', []):
            in_msg = tx.get('in_msg')
            if not in_msg:
                continue

            # Only consider incoming messages to our wallet
            if in_msg.get('destination') != WALLET_ADDRESS:
                continue

            value_nano = int(in_msg.get('value', 0))
            value_ton  = value_nano / 1e9
            msg_text   = in_msg.get('message', '').strip()

            if msg_text == comment.strip() and value_ton >= min_amount:
                return True

        return False

    except Exception as e:
        print(f"[ton_payment] check_transaction error: {e}")
        return False
