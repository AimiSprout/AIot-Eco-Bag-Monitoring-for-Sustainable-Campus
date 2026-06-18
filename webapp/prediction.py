import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

# Firebase Setup
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred,{
    'databaseURL':
    'https://ecobagmonitoring-default-rtdb.asia-southeast1.firebasedatabase.app'
})

history_ref = db.reference("history")
history = history_ref.get()

daily_count = {}

for key,item in history.items():

    ts = item.get("timestamp")

    if not ts:
        continue

    date_only = ts.split(" ")[0]

    daily_count[date_only] = \
        daily_count.get(date_only,0) + 1

dates = sorted(daily_count.keys())

X=[]
y=[]

for i,date in enumerate(dates):

    X.append([i+1])
    y.append(daily_count[date])

if len(X) < 3:

    print("Not enough data")
    exit()

model = LinearRegression()
model.fit(X,y)

next_day = len(X)+1

prediction = model.predict([[next_day]])

prediction_value = max(
    0,
    round(float(prediction[0]))
)

print("Prediction:",prediction_value)

db.reference("prediction").set({

    "nextDayPrediction":
    prediction_value,

    "generatedAt":
    datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

})