import asyncio
from aiocryptopay import AioCryptoPay, Networks
import config

# Initialize crypto pay client. We use Mainnet by default.
crypto = AioCryptoPay(token=config.CRYPTOPAY_TOKEN, network=Networks.MAIN_NET)

async def create_rub_invoice(amount_rub: float, payload: str = "") -> dict:
    """
    Creates a CryptoBot invoice in fiat equivalent (RUB).
    Payload can be used to store internal reference.
    """
    try:
        # creating invoice in fiat (RUB). Users can pay in any supported crypto.
        invoice = await crypto.create_invoice(
            amount=amount_rub,
            fiat='RUB',
            currency_type='fiat',
            description="Покупка аккаунта",
            hidden_message="Спасибо за покупку!",
            payload=payload
        )
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url": invoice.bot_invoice_url
        }
    except Exception as e:
        print(f"Error creating CryptoBot invoice: {e}")
        return None

async def check_invoice_status(invoice_id: int) -> bool:
    """
    Checks if the invoice is paid.
    """
    try:
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        if invoices and invoices[0].status == 'paid':
            return True
        return False
    except Exception as e:
        print(f"Error checking CryptoBot invoice API: {e}")
        return False

# Ensure to close the session gracefully when stopping the bot
async def close():
    await crypto.close()
