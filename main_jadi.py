import RPi.GPIO as GPIO
import tensorflow as tf
import numpy as np
from picamera2 import Picamera2
from RPLCD.i2c import CharLCD
import firebase_admin
from firebase_admin import credentials, db
from adafruit_servokit import ServoKit
import requests
import time
import datetime
import os

# =====================
# TELEGRAM SETTINGS
# =====================
TOKEN   = "8632708542:AAEzRxnBIxXyuoT8JZtfALxU0sNN9xzM4Yw"
CHAT_ID = "8149623271"

def send_telegram(message):
    try:
        url  = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=5)
        print("✅ Telegram sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def current_time():
    return datetime.datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

# =====================
# GPIO SETUP
# =====================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

IR_BAG    = 17
IR_WOVEN  = 27
IR_PAPER  = 22
IR_CANVAS = 23

for pin in [IR_BAG, IR_WOVEN, IR_PAPER, IR_CANVAS]:
    GPIO.setup(pin, GPIO.IN)

# =====================
# PCA9685 SERVO SETUP
# =====================
kit = ServoKit(channels=16)

S2 = 1
S3 = 0

kit.servo[S2].set_pulse_width_range(500, 2500)
kit.servo[S3].set_pulse_width_range(500, 2500)

S2_LEFT   = 0
S2_CENTER = 90
S2_RIGHT  = 180

S3_LEFT   = 0
S3_CENTER = 90
S3_RIGHT  = 180

MOVE_DELAY    = 1.0
BAG_PASS_TIME = 2.0

def reset_servos():
    kit.servo[S2].angle = S2_CENTER
    kit.servo[S3].angle = S3_CENTER
    time.sleep(MOVE_DELAY)

def sort_bag(bag_type):
    bag_type = bag_type.lower().strip()

    if bag_type == 'paper':
        print("[SORT] Paper → C1")
        kit.servo[S2].angle = S2_RIGHT
        time.sleep(MOVE_DELAY)
        time.sleep(BAG_PASS_TIME)

    elif bag_type == 'canvas':
        print("[SORT] Canvas → C2")
        kit.servo[S2].angle = S2_LEFT
        time.sleep(MOVE_DELAY)
        kit.servo[S3].angle = S3_RIGHT
        time.sleep(MOVE_DELAY)
        time.sleep(BAG_PASS_TIME)

    elif bag_type == 'woven':
        print("[SORT] Woven → C3")
        kit.servo[S2].angle = S2_LEFT
        time.sleep(MOVE_DELAY)
        kit.servo[S3].angle = S3_LEFT
        time.sleep(MOVE_DELAY)
        time.sleep(BAG_PASS_TIME)

    else:
        print(f"[WARN] Unknown: '{bag_type}' — skip")
        return

    reset_servos()
    print("[SORT] Done!\n")

# =====================
# FIREBASE SETUP
# =====================
cred = credentials.Certificate('/home/pi/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ecobagmonitoring-default-rtdb.asia-southeast1.firebasedatabase.app'
})
print("✅ Firebase connected!")

# =====================
# LCD SETUP
# =====================
lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,
    cols=16,
    rows=2
)

def lcd_display(line1, line2=""):
    lcd.clear()
    lcd.write_string(line1[:16])
    if line2:
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2[:16])

# =====================
# ML MODEL SETUP
# =====================
print("Loading ML model...")
interpreter = tf.lite.Interpreter(
    model_path='/home/pi/eco_bag_model5.tflite'
)
interpreter.allocate_tensors()

input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

with open('/home/pi/labels5.txt', 'r') as f:
    labels = [line.strip() for line in f.readlines()]

print("Labels:", labels)

# =====================
# CAMERA SETUP
# =====================
print("Starting camera...")
picam = Picamera2()
config = picam.create_still_configuration(
    main={"size": (224, 224)}
)
picam.configure(config)
picam.start()
time.sleep(2)

# =====================
# BAG COUNTER
# =====================
bag_count = {label: 0 for label in labels}

bin_was_full   = {label: False for label in labels}
bin_full_count = {label: 0 for label in labels}
bin_cooldown   = {label: 0 for label in labels}
DEBOUNCE_LIMIT   = 3
COOLDOWN_SECONDS = 10

# =====================
# CLASSIFY FUNCTION
# (3 captures + majority vote)
# =====================
def classify_bag():
    predictions    = []
    confidences    = []
    TOTAL_CAPTURES = 3

    for i in range(TOTAL_CAPTURES):
        frame = picam.capture_array()
        img   = frame[:,:,:3].astype(np.float32) / 255.0
        img   = np.expand_dims(img, axis=0)

        interpreter.set_tensor(input_details[0]['index'], img)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])

        predicted_class = labels[int(np.argmax(output))]
        confidence      = float(np.max(output) * 100)

        predictions.append(predicted_class)
        confidences.append(confidence)

        print(f"  Capture {i+1}: {predicted_class} ({confidence:.1f}%)")
        time.sleep(0.3)

    # Majority vote
    final_class = max(set(predictions), key=predictions.count)
    avg_conf    = sum(confidences) / len(confidences)

    print(f"  Majority  : {final_class.upper()}")
    print(f"  Avg Conf  : {avg_conf:.1f}%")

    return final_class, avg_conf

# =====================
# FIREBASE FUNCTIONS
# =====================
def update_firebase(bag_type, bag_count):
   try:

       # ---------------------
       # GLOBAL ADMIN COUNTER
       # ---------------------
       total = sum(bag_count.values())

       db.reference('bag_count').set({
           **bag_count,
           'total': total
       })

       db.reference('machine_status').set({
           'message': f'Last: {bag_type.upper()} | Total: {total}'
       })

       # ---------------------
       # ACTIVE USER
       # ---------------------
       active_user = db.reference("active_user").get()

       # ---------------------
       # HISTORY LOG
       # ---------------------
       timestamp = datetime.datetime.now().strftime(
           "%Y-%m-%d %H:%M:%S"
       )

       db.reference('history').push({
           'bag_type': bag_type,
           'timestamp': timestamp,
           "matrix": active_user["matrix"] if active_user else "unknown",
           "day": datetime.datetime.now().strftime("%A")
       })

       # ---------------------
       # ACTIVE USER SESSION
       # ---------------------
       active_user = db.reference('active_user').get()

       if active_user:

           matrix = active_user.get('matrix')

           if matrix:

               user_ref = db.reference(
                   f'users/{matrix}/session'
               )

               session = user_ref.get()

               if session is None:
                   session = {
                       'paper': 0,
                       'canvas': 0,
                       'woven': 0,
                       'total': 0
                   }

               if bag_type not in session:
                   session[bag_type] = 0

               session[bag_type] += 1
               session['total']   += 1

               user_ref.set(session)

               # ---------------------
               # UPDATE LCD SESSION TOTAL
               # ---------------------
               session_total = session['total']
               lcd_display(
                   f"{bag_type.upper()}",
                   f"Bags:{session_total}"
               )

               print(f"✅ Session updated for {matrix}")

       print(f"✅ Firebase updated! Total: {total}")
       os.system("python3 /home/pi/prediction.py")

   except Exception as e:
       print(f"❌ Firebase error: {e}")


# =====================
# BIN FULL CHECK
# =====================
def check_bin_full():
    ir_pins = {
        'canvas' : IR_PAPER,
        'woven': IR_CANVAS,
        'paper' : IR_WOVEN
    }
    current_time_val = time.time()

    for bag_type, pin in ir_pins.items():
        if current_time_val < bin_cooldown[bag_type]:
            continue

        sensor_value = GPIO.input(pin)

        if sensor_value == 0:
            bin_full_count[bag_type] += 1
            if bin_full_count[bag_type] >= DEBOUNCE_LIMIT:
                if not bin_was_full[bag_type]:
                    db.reference('bin_status').update({
                        bag_type: 'FULL'
                    })
                    bin_was_full[bag_type] = True
                    bin_cooldown[bag_type] = current_time_val + COOLDOWN_SECONDS
                    print(f"⚠️ {bag_type.upper()} bin FULL!")

                    lcd_display(
                        f"{bag_type.upper()} Bin FULL!",
                        "Check Admin!"
                    )

                    send_telegram(
                        f"⚠️ EcoBag Alert\n\n"
                        f"{bag_type.upper()} compartment is FULL.\n"
                        f"Please empty immediately.\n\n"
                        f"Time: {current_time()}"
                    )
        else:
            bin_full_count[bag_type] = 0
            # FIX: Jangan auto clear — tunggu admin tekan Clear button
            # Buang bahagian bin_was_full = False dari sini


# =====================
# MAIN LOOP
# =====================
print("\n✅ System Ready!")
lcd_display("Eco-Bag System", "Ready!")

reset_servos()

db.reference('bin_status').set({label: 'OK' for label in labels})
existing = db.reference('bag_count').get()
if existing:
    bag_count.update({
        k: v for k, v in existing.items()
        if k in bag_count
    })
else:
    db.reference('bag_count').set({
        **{label: 0 for label in labels},
        'total': 0
    })

try:

    while True:

        sorting_status = db.reference(
            "sorting_status"
        ).get()

        if sorting_status != True:

            lcd_display(
                "Waiting User",
                "Login First"
            )
            check_bin_full()
            time.sleep(0.1)
            continue

        check_bin_full()

        if GPIO.input(IR_BAG) == 0:

            print("\n🎒 Bag detected!")

            lcd_display(
                "Bag Detected!",
                "Classifying..."
            )

            time.sleep(0.5)

            predicted_class, avg_conf = classify_bag()

            print(
                f"\nBag Type : {predicted_class.upper()}"
            )

            print(
                f"Confidence: {avg_conf:.2f}%"
            )

            if avg_conf >= 70.0:

                bag_count[predicted_class] += 1

                total = sum(
                    bag_count.values()
                )

                lcd_display(
                    f"Type:{predicted_class.upper()}",
                    "Classifying"
                )

                sort_bag(predicted_class)

                update_firebase(
                    predicted_class,
                    bag_count
                )

                check_bin_full()

                print(
                    f"Bag counts: {bag_count}"
                )

            else:

                print(
                    f"Low confidence: {avg_conf:.1f}% - skip"
                )

                lcd_display(
                    "Low Confidence",
                    "Try Again..."
                )

                time.sleep(2)

            lcd_display(
                "Eco-Bag System",
                "Ready!"
            )

        time.sleep(0.1)

except KeyboardInterrupt:

    print("\n\nSystem stopped!")

    print(
        f"Final counts: {bag_count}"
    )

    lcd_display(
        "System Off",
        "Goodbye!"
    )

    time.sleep(2)

    lcd.clear()

    kit.servo[S2].angle = None
    kit.servo[S3].angle = None

    GPIO.cleanup()

    picam.stop()

    print("Done!")