import requests
from config import WALLET_ADDRESS, TONCENTER_API_KEY, PRICE_TON_RUB as PRICE_RUB

def get_ton_to_rub_rate():
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub'
        res = requests.get(url, timeout=5)
        data = res.json()
        return data['the-open-network']['rub']
    except Exception as e:
        print("Error fetching rate:", e)
        return 700 # Fallback rate if AP is down

def get_price_in_ton(price_rub: float = PRICE_RUB):
    rate = get_ton_to_rub_rate()
    amount_in_ton = price_rub / rate
    return round(amount_in_ton, 3)

def check_transaction(comment, expected_amount_ton):
    try:
        url = f'https://toncenter.com/api/v2/getTransactions?address={WALLET_ADDRESS}&limit=20&api_key={TONCENTER_API_KEY}'
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if not data.get('ok'):
            print("Toncenter response not OK:", data)
            return False
        
        for tx in data.get('result', []):
            in_msg = tx.get('in_msg')
            if not in_msg:
                continue
            
            # Toncenter v2 getTransactions: destination is checked
            # Actually for the wallet itself it will receive the tx
            if in_msg.get('destination') != WALLET_ADDRESS:
                continue
                
            value = int(in_msg.get('value', 0))
            value_ton = value / 1e9
            msg_message = in_msg.get('message', '')
            
            if msg_message.strip() == comment.strip() and value_ton >= (expected_amount_ton * 0.98): # allowing a tiny diff due to rounding
                return True
        return False
    except Exception as e:
        print("Error checking tx:", e)
        return False
