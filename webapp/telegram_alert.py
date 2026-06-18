import requests
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# =====================================
# FIREBASE CONNECTION
# =====================================
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ecobagmonitoring-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# =====================================
# TELEGRAM SETTINGS
# =====================================
TOKEN = "8632708542:AAEzRxnBIxXyuoT8JZtfALxU0sNN9xzM4Yw"
CHAT_ID = "8149623271"

# =====================================
# MEMORY (ANTI SPAM)
# =====================================
last_paper = "OK"
last_canvas = "OK"
last_woven = "OK"

# =====================================
# TELEGRAM SEND FUNCTION
# =====================================
def send_telegram(message):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        print("✅ Telegram Notification Sent")
    else:
        print("❌ Failed to Send Telegram Message")


# =====================================
# TIME FUNCTION
# =====================================
def current_time():
    return datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")


# =====================================
# START SYSTEM
# =====================================
print("======================================")
print("   EcoBag Live Telegram Monitoring")
print("   System Started Successfully")
print("======================================")


# =====================================
# MAIN LOOP
# =====================================
while True:

    try:

        status = db.reference("bin_status").get()

        if status:

            paper = status.get("paper", "OK")
            canvas = status.get("canvas", "OK")
            woven = status.get("woven", "OK")

            # =================================
            # PAPER ALERT
            # =================================
            if paper == "FULL" and last_paper != "FULL":

                msg = f"""⚠️ EcoBag Alert

Paper compartment is FULL.
Please empty immediately.

Time: {current_time()}
"""

                send_telegram(msg)
                print("⚠️ Paper compartment FULL")
                last_paper = "FULL"

            elif paper != "FULL" and last_paper == "FULL":

                print("✅ Paper compartment back to normal")
                last_paper = "OK"


            # =================================
            # CANVAS ALERT
            # =================================
            if canvas == "FULL" and last_canvas != "FULL":

                msg = f"""⚠️ EcoBag Alert

Canvas compartment is FULL.
Please empty immediately.

Time: {current_time()}
"""

                send_telegram(msg)
                print("⚠️ Canvas compartment FULL")
                last_canvas = "FULL"

            elif canvas != "FULL" and last_canvas == "FULL":

                print("✅ Canvas compartment back to normal")
                last_canvas = "OK"


            # =================================
            # WOVEN ALERT
            # =================================
            if woven == "FULL" and last_woven != "FULL":

                msg = f"""⚠️ EcoBag Alert

Woven compartment is FULL.
Please empty immediately.

Time: {current_time()}
"""

                send_telegram(msg)
                print("⚠️ Woven compartment FULL")
                last_woven = "FULL"

            elif woven != "FULL" and last_woven == "FULL":

                print("✅ Woven compartment back to normal")
                last_woven = "OK"

    except:
        print("⚠️ Firebase Connection Error... Retrying")

    time.sleep(5)