import asyncio
from aiocryptopay import AioCryptoPay, Networks
import config

crypto = AioCryptoPay(token=config.CRYPTOPAY_TOKEN, network=Networks.MAIN_NET)

async def create_rub_invoice(amount_rub: float, account_id: int) -> dict | None:
    """
    Creates a CryptoBot invoice.
    Payload encodes account_id so we can look it up on callback (fix: was missing).
    """
    try:
        invoice = await crypto.create_invoice(
            amount=amount_rub,
            fiat='RUB',
            currency_type='fiat',
            description="Покупка аккаунта",
            hidden_message="Спасибо за покупку! Ваш архив отправлен.",
            payload=str(account_id)   # ← FIX: store account_id in payload
        )
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url":    invoice.bot_invoice_url,
            "account_id": account_id,
        }
    except Exception as e:
        print(f"[crypto_payment] create_invoice error: {e}")
        return None

async def check_invoice_status(invoice_id: int) -> tuple[bool, int | None]:
    """
    Returns (is_paid, account_id).
    account_id is extracted from the invoice payload (fix: was not returned before).
    """
    try:
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        if invoices and invoices[0].status == 'paid':
            acc_id = int(invoices[0].payload) if invoices[0].payload else None
            return True, acc_id
        return False, None
    except Exception as e:
        print(f"[crypto_payment] check_invoice_status error: {e}")
        return False, None

async def close():
    await crypto.close()
