import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

import database
import ton_payment
import crypto_payment
import config

# Initialize components
bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()

# Make sure accounts directory exists
os.makedirs("accounts", exist_ok=True)
database.init_db()

# --- FSM States ---
class AddAccountState(StatesGroup):
    waiting_for_country = State()
    waiting_for_aging = State()
    waiting_for_archive = State()

# --- ADMIN HANDLERS ---
@dp.message(Command("add"), F.from_user.id == config.ADMIN_ID)
async def admin_add_account(message: types.Message, state: FSMContext):
    await message.answer("Режим добавления аккаунта.\nУкажите страну аккаунта:")
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
    doc = message.document
    file_name = f"{uuid.uuid4()}_{doc.file_name}"
    file_path = os.path.join("accounts", file_name)
    
    # Download file using bot.download()
    await bot.download(doc, destination=file_path)
    
    data = await state.get_data()
    database.add_account(data['country'], data['aging'], file_path)
    
    await message.answer("✅ Аккаунт успешно добавлен!")
    await state.clear()

@dp.message(Command("delete"), F.from_user.id == config.ADMIN_ID)
async def admin_list_delete(message: types.Message):
    accounts = database.get_available_accounts()
    if not accounts:
        await message.answer("Нет доступных аккаунтов для удаления.")
        return
        
    for acc in accounts:
        acc_id, country, aging = acc
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить этот аккаунт", callback_data=f"admin_del_{acc_id}")]
        ])
        await message.answer(f"ID: {acc_id} | 🌍 {country} | ⏳ {aging}", reply_markup=markup)

@dp.callback_query(F.data.startswith("admin_del_"), F.from_user.id == config.ADMIN_ID)
async def admin_do_delete(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[2])
    account = database.get_account(acc_id)
    if not account:
        await callback.answer("Аккаунт уже удалён или не найден.")
        return
    
    file_path = account[3]
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Removed archive: {file_path}")
        except Exception as e:
            print(f"Failed removing file: {e}")
            
    database.delete_account(acc_id)
    await callback.message.edit_text(f"✅ Аккаунт {acc_id} успешно удалён.")
    await callback.answer()


# --- USER HANDLERS ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить аккаунт", callback_data="buy_account")],
        [InlineKeyboardButton(text="ℹ️ Важное", callback_data="important_info")]
    ])
    await message.answer("👋 Добро пожаловать в магазин аккаунтов!", reply_markup=markup)

@dp.callback_query(F.data == "important_info")
async def process_important_info(callback: types.CallbackQuery):
    await callback.message.answer("все аккаунты в формате Tdata")
    await callback.answer()

@dp.callback_query(F.data == "buy_account")
async def process_buy_account(callback: types.CallbackQuery):
    accounts = database.get_available_accounts()
    if not accounts:
        await callback.message.answer("😔 К сожалению, аккаунты сейчас недоступны.")
        await callback.answer()
        return

    # Let's just pick the first available or show a list.
    # The prompt implies a smooth flow, let's just pick the first available.
    acc = accounts[0]
    acc_id, country, aging = acc
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Подтвердить и оплатить ({config.PRICE_TON_RUB} руб.)", callback_data=f"checkout_{acc_id}")]
    ])
    
    await callback.message.answer(
        f"📋 Выбранный аккаунт:\n"
        f"🌍 Страна: {country}\n"
        f"⏳ Отлёжка: {aging}\n\n"
        f"💰 Цена: {config.PRICE_TON_RUB} руб.",
        reply_markup=markup
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("checkout_"))
async def process_checkout(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    account = database.get_account(acc_id)
    
    if not account:
        await callback.message.answer("❌ Этот аккаунт больше недоступен.")
        await callback.answer()
        return
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data=f"pay_cb_{acc_id}")],
        [InlineKeyboardButton(text="🛡️ Trust Wallet (вручную)", callback_data=f"pay_tw_{acc_id}")],
        [InlineKeyboardButton(text="💎 Tonkeeper", callback_data=f"pay_tk_{acc_id}")]
    ])
    
    await callback.message.answer(
        "💳 Выберите способ оплаты:",
        reply_markup=markup
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_payment_method(callback: types.CallbackQuery):
    _, method_prefix, acc_id_str = callback.data.split("_")
    acc_id = int(acc_id_str)
    
    account = database.get_account(acc_id)
    if not account:
        await callback.message.answer("This account is no longer available.")
        await callback.answer()
        return
        
    if method_prefix == 'cb':
        # CryptoBot
        invoice_data = await crypto_payment.create_rub_invoice(config.PRICE_CRYPTOBOT, payload=f"acc_{acc_id}")
        if not invoice_data:
            await callback.message.answer("❌ Ошибка при создании счёта CryptoBot. Попробуйте позже.")
            await callback.answer()
            return
            
        inv_id = str(invoice_data['invoice_id'])
        pay_url = invoice_data['pay_url']
        
        database.create_invoice(callback.from_user.id, acc_id, 0, inv_id, 'cryptobot')
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Оплатить через CryptoBot", url=pay_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"checkpay_{inv_id}")]
        ])
        
        await callback.message.answer(
            f"💳 **Счёт CryptoBot создан!**\n\nСумма: {config.PRICE_CRYPTOBOT} руб.\n_(включает комиссию сервиса 1.5%)_\nНажмите кнопку ниже для оплаты.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        await callback.answer()
        return

    # TON Methods (Tonkeeper or Trust Wallet)
    amount_ton = ton_payment.get_price_in_ton(config.PRICE_TON_RUB)
    comment = f"pay_{callback.from_user.id}_{uuid.uuid4().hex[:8]}"
    database.create_invoice(callback.from_user.id, acc_id, amount_ton, comment, 'ton')
    
    if method_prefix == 'tw':
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"checkpay_{comment}")]
        ])
        await callback.message.answer(
            f"💳 **Счёт Trust Wallet создан!**\n\n"
            f"Сумма: `{amount_ton}` TON (~{config.PRICE_TON_RUB} руб.)\n"
            f"Адрес:\n`{config.WALLET_ADDRESS}`\n\n"
            f"📝 Комментарий/Memo:\n`{comment}`\n\n"
            f"⚠️ **ВАЖНО:** Вы ОБЯЗАНЫ указать точный комментарий при отправке! Нажмите на адрес и комментарий выше, чтобы скопировать их.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    elif method_prefix == 'tk':
        tonkeeper_link = f"https://app.tonkeeper.com/transfer/{config.WALLET_ADDRESS}?amount={int(amount_ton * 1e9)}&text={comment}"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Открыть в Tonkeeper", url=tonkeeper_link)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"checkpay_{comment}")]
        ])
        await callback.message.answer(
            f"💳 **Счёт Tonkeeper создан!**\n\n"
            f"Сумма: `{amount_ton}` TON (~{config.PRICE_TON_RUB} руб.)\n"
            f"Адрес: `{config.WALLET_ADDRESS}`\n"
            f"📝 Комментарий/Memo: `{comment}`\n\n"
            f"Нажмите кнопку для оплаты через Tonkeeper.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("checkpay_"))
async def check_payment(callback: types.CallbackQuery):
    comment = callback.data.split("_", 1)[1]
    invoice = database.get_invoice(comment)
    
    if not invoice:
        await callback.answer("❌ Счёт не найден.")
        return
        
    # Unpack safely to handle DB schema changes
    inv_id = invoice[0]
    user_id = invoice[1]
    acc_id = invoice[2]
    amount_ton = invoice[3]
    inv_comment = invoice[4]
    status = invoice[5]
    method = invoice[6] if len(invoice) > 6 else 'ton'
    
    if status == 'paid':
        await callback.answer("✅ Этот счёт уже оплачен.")
        return
        
    # Check blockchain / API depending on method
    is_paid = False
    if method == 'cryptobot':
        is_paid = await crypto_payment.check_invoice_status(int(comment))
    else:
        is_paid = ton_payment.check_transaction(comment, amount_ton)
    
    if is_paid:
        # Fulfill order
        account = database.get_account(acc_id)
        if not account:
            await callback.message.answer("❌ Ошибка: аккаунт уже продан или удалён.")
            await callback.answer("Ошибка")
            return
            
        file_path = account[3]
        
        # Send file
        if os.path.exists(file_path):
            doc = FSInputFile(file_path)
            await callback.message.answer_document(doc, caption="🎉 Спасибо за покупку! Вот ваш архив с аккаунтом.")
            
            # Delete file
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")
                
            # Update DB
            database.mark_account_sold(acc_id)
            database.mark_invoice_paid(comment)
            await callback.answer("✅ Оплата прошла успешно!")
        else:
            await callback.message.answer("❌ Критическая ошибка: файл архива не найден на сервере.")
            await callback.answer("Ошибка")
    else:
        await callback.message.answer("⏳ Оплата ещё не найдена или сумма недостаточна. Убедитесь, что транзакция отправлена и подтверждена сетью.")
        await callback.answer("Оплата не найдена")

async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
