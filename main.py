import asyncio
import os
import uuid

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

import database
import ton_payment
import crypto_payment
import config

bot = Bot(token=config.TELEGRAM_TOKEN)
dp  = Dispatcher()

os.makedirs("accounts", exist_ok=True)
database.init_db()

# ---------------------------------------------------------------------------
# FSM
# ---------------------------------------------------------------------------
class AddAccountState(StatesGroup):
    waiting_for_country = State()
    waiting_for_aging   = State()
    waiting_for_archive = State()

# ---------------------------------------------------------------------------
# Helper: safely deliver file and fulfill order
# ---------------------------------------------------------------------------
async def fulfill_order(message_or_callback, acc_id: int, comment: str):
    """
    Deliver the archive to the buyer.
    Only marks account as sold AFTER successful file delivery (fix: was reversed).
    Releases reservation if delivery fails.
    """
    # Try to reserve (atomic, prevents double-sell)
    if not database.reserve_account(acc_id):
        # Someone else already grabbed it
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer("❌ Аккаунт уже продан другому покупателю.")
        return False

    account = database.get_account(acc_id)
    if not account:
        database.release_account(acc_id)
        return False

    file_path = account[3]

    if not os.path.exists(file_path):
        database.release_account(acc_id)
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer("❌ Критическая ошибка: архив не найден на сервере.")
        return False

    try:
        doc = FSInputFile(file_path)
        if hasattr(message_or_callback, 'answer_document'):
            await message_or_callback.answer_document(
                doc, caption="🎉 Спасибо за покупку! Ваш архив:"
            )
        else:
            await message_or_callback.message.answer_document(
                doc, caption="🎉 Спасибо за покупку! Ваш архив:"
            )
        # Delivery OK → mark as sold, delete file
        database.mark_account_sold(acc_id)
        database.mark_invoice_paid(comment)
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[main] Could not remove archive {file_path}: {e}")
        return True

    except Exception as e:
        print(f"[main] Delivery failed: {e}")
        database.release_account(acc_id)   # return to available if send failed
        return False

# ---------------------------------------------------------------------------
# ADMIN HANDLERS
# ---------------------------------------------------------------------------
@dp.message(Command("add"), F.from_user.id == config.ADMIN_ID)
async def admin_add_account(message: types.Message, state: FSMContext):
    await message.answer("Режим добавления.\nУкажите страну аккаунта:")
    await state.set_state(AddAccountState.waiting_for_country)

@dp.message(AddAccountState.waiting_for_country, F.from_user.id == config.ADMIN_ID)
async def admin_get_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("Укажите период отлёжки:")
    await state.set_state(AddAccountState.waiting_for_aging)

@dp.message(AddAccountState.waiting_for_aging, F.from_user.id == config.ADMIN_ID)
async def admin_get_aging(message: types.Message, state: FSMContext):
    await state.update_data(aging=message.text)
    await message.answer("Отправьте zip/rar архив с аккаунтом:")
    await state.set_state(AddAccountState.waiting_for_archive)

@dp.message(AddAccountState.waiting_for_archive, F.document, F.from_user.id == config.ADMIN_ID)
async def admin_get_archive(message: types.Message, state: FSMContext):
    doc       = message.document
    file_name = f"{uuid.uuid4()}_{doc.file_name}"
    file_path = os.path.join("accounts", file_name)
    await bot.download(doc, destination=file_path)
    data = await state.get_data()
    database.add_account(data['country'], data['aging'], file_path)
    await message.answer("✅ Аккаунт успешно добавлен!")
    await state.clear()

@dp.message(Command("delete"), F.from_user.id == config.ADMIN_ID)
async def admin_list_delete(message: types.Message):
    accounts = database.get_available_accounts()
    if not accounts:
        await message.answer("Нет доступных аккаунтов.")
        return
    for acc_id, country, aging in accounts:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_del_{acc_id}")
        ]])
        await message.answer(f"ID: {acc_id} | 🌍 {country} | ⏳ {aging}", reply_markup=markup)

@dp.callback_query(F.data.startswith("admin_del_"), F.from_user.id == config.ADMIN_ID)
async def admin_do_delete(callback: types.CallbackQuery):
    acc_id  = int(callback.data.split("_")[2])
    account = database.get_account(acc_id)
    if not account:
        await callback.answer("Аккаунт уже удалён.")
        return
    file_path = account[3]
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[admin] File remove error: {e}")
    database.delete_account(acc_id)
    await callback.message.edit_text(f"✅ Аккаунт {acc_id} удалён.")
    await callback.answer()

# ---------------------------------------------------------------------------
# USER HANDLERS
# ---------------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить аккаунт", callback_data="buy_account")],
        [InlineKeyboardButton(text="ℹ️ Важное",          callback_data="important_info")],
    ])
    await message.answer("👋 Добро пожаловать в магазин аккаунтов!", reply_markup=markup)

@dp.callback_query(F.data == "important_info")
async def process_important_info(callback: types.CallbackQuery):
    await callback.message.answer("Все аккаунты поставляются в формате **Tdata**.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "buy_account")
async def process_buy_account(callback: types.CallbackQuery):
    accounts = database.get_available_accounts()
    if not accounts:
        await callback.message.answer("😔 Аккаунты сейчас недоступны. Заходите позже.")
        await callback.answer()
        return

    acc_id, country, aging = accounts[0]
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"✅ Подтвердить ({config.PRICE_TON_RUB} руб.)",
            callback_data=f"checkout_{acc_id}"
        )
    ]])
    await callback.message.answer(
        f"📋 Аккаунт:\n🌍 Страна: {country}\n⏳ Отлёжка: {aging}\n\n"
        f"💰 Цена: {config.PRICE_TON_RUB} руб.",
        reply_markup=markup
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("checkout_"))
async def process_checkout(callback: types.CallbackQuery):
    acc_id  = int(callback.data.split("_")[1])
    account = database.get_account(acc_id)
    if not account:
        await callback.message.answer("❌ Этот аккаунт уже недоступен.")
        await callback.answer()
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 CryptoBot",              callback_data=f"pay_cb_{acc_id}")],
        [InlineKeyboardButton(text="🛡️ Trust Wallet (вручную)", callback_data=f"pay_tw_{acc_id}")],
        [InlineKeyboardButton(text="💎 Tonkeeper",               callback_data=f"pay_tk_{acc_id}")],
    ])
    await callback.message.answer("💳 Выберите способ оплаты:", reply_markup=markup)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_payment_method(callback: types.CallbackQuery):
    parts         = callback.data.split("_")   # pay  cb  123
    method_prefix = parts[1]
    acc_id        = int(parts[2])

    account = database.get_account(acc_id)
    if not account:
        await callback.message.answer("❌ Аккаунт больше недоступен.")
        await callback.answer()
        return

    # ---- CryptoBot ----
    if method_prefix == 'cb':
        invoice_data = await crypto_payment.create_rub_invoice(config.PRICE_CRYPTOBOT, acc_id)
        if not invoice_data:
            await callback.message.answer("❌ Ошибка CryptoBot. Попробуйте позже.")
            await callback.answer()
            return

        inv_id  = str(invoice_data['invoice_id'])
        pay_url = invoice_data['pay_url']
        database.create_invoice(callback.from_user.id, acc_id, 0, inv_id, 'cryptobot')

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Оплатить через CryptoBot", url=pay_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату",          callback_data=f"checkpay_{inv_id}")],
        ])
        await callback.message.answer(
            f"💳 *Счёт CryptoBot создан!*\n\nСумма: {config.PRICE_CRYPTOBOT} руб.\n"
            f"_(включает комиссию 1.5%)_",
            parse_mode="Markdown",
            reply_markup=markup
        )
        await callback.answer()
        return

    # ---- TON methods (Tonkeeper / Trust Wallet) ----
    amount_ton = ton_payment.get_price_in_ton(config.PRICE_TON_RUB)
    comment    = f"pay_{callback.from_user.id}_{uuid.uuid4().hex[:8]}"
    database.create_invoice(callback.from_user.id, acc_id, amount_ton, comment, 'ton')

    if method_prefix == 'tw':
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"checkpay_{comment}")
        ]])
        await callback.message.answer(
            f"💳 *Trust Wallet*\n\n"
            f"Сумма: `{amount_ton}` TON (~{config.PRICE_TON_RUB} руб.)\n"
            f"Адрес:\n`{config.WALLET_ADDRESS}`\n\n"
            f"📝 Комментарий/Memo:\n`{comment}`\n\n"
            f"⚠️ *ОБЯЗАТЕЛЬНО укажите точный комментарий!*",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif method_prefix == 'tk':
        tonkeeper_link = (
            f"https://app.tonkeeper.com/transfer/{config.WALLET_ADDRESS}"
            f"?amount={int(amount_ton * 1e9)}&text={comment}"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Открыть Tonkeeper", url=tonkeeper_link)],
            [InlineKeyboardButton(text="🔄 Проверить оплату",  callback_data=f"checkpay_{comment}")],
        ])
        await callback.message.answer(
            f"💳 *Tonkeeper*\n\n"
            f"Сумма: `{amount_ton}` TON (~{config.PRICE_TON_RUB} руб.)\n"
            f"Адрес: `{config.WALLET_ADDRESS}`\n"
            f"📝 Memo: `{comment}`",
            parse_mode="Markdown",
            reply_markup=markup
        )

    await callback.answer()

# ---------------------------------------------------------------------------
# PAYMENT CHECK
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("checkpay_"))
async def check_payment(callback: types.CallbackQuery):
    comment = callback.data.split("_", 1)[1]
    invoice = database.get_invoice(comment)

    if not invoice:
        await callback.answer("❌ Счёт не найден.", show_alert=True)
        return

    inv_id, user_id, acc_id, amount_ton, inv_comment, status, method = (
        invoice[0], invoice[1], invoice[2], invoice[3],
        invoice[4], invoice[5], invoice[6] if len(invoice) > 6 else 'ton'
    )

    if status == 'paid':
        await callback.answer("✅ Этот счёт уже оплачен.", show_alert=True)
        return

    # Check payment
    is_paid = False
    if method == 'cryptobot':
        is_paid, _ = await crypto_payment.check_invoice_status(int(comment))
    else:
        is_paid = ton_payment.check_transaction(comment, amount_ton)

    if is_paid:
        ok = await fulfill_order(callback, acc_id, comment)
        if ok:
            await callback.answer("✅ Оплата прошла! Архив отправлен.", show_alert=True)
        else:
            await callback.answer("❌ Ошибка доставки. Обратитесь к администратору.", show_alert=True)
    else:
        await callback.message.answer(
            "⏳ Оплата ещё не найдена.\n"
            "Убедитесь, что транзакция отправлена и подтверждена сетью, затем нажмите «Проверить» снова."
        )
        await callback.answer("Оплата не найдена")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def main():
    print("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await crypto_payment.close()

if __name__ == '__main__':
    asyncio.run(main())
