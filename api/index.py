from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient, ReturnDocument
import datetime
import os

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
app.secret_key = "super_secret_key"  # Change this in production

# Connect to MongoDB
client = MongoClient("mongodb+srv://tjsreeharish:Tjsreeharish@cluster0.yrg9a.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
email_db = client["email_database"]
booking_db = client["booking_database"]

# Updated slot timings as requested
slots = [
    ("7:30", "7:30 AM – 9:00 AM"),
    ("8:30", "8:30 AM – 10:00 AM"),
    ("9:30", "9:30 AM – 11:00 AM"),
    ("10:30", "10:30 AM – 12:00 PM"),
    ("12:30", "12:30 PM – 2:00 PM"),
    ("1:30", "1:30 PM – 3:00 PM"),
    ("2:30", "2:30 PM – 4:00 PM")
]
dates = ["26 April", "27 April"]

# Initialize slot counts if not already
def initialize_slot_counts():
    for date in dates:
        for slot_code, _ in slots:
            booking_db.slot_counts.update_one(
                {"date": date, "slot": slot_code},
                {"$setOnInsert": {"count": 0}},
                upsert=True
            )

initialize_slot_counts()

# Login route
@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_email = request.form.get("email", "").strip().lower()
        allowed = email_db.allowed_emails.find_one({"email": user_email})

        if allowed:
            session["email"] = user_email
            return redirect(url_for("slot_booking"))
        else:
            flash("Invalid Credentials, please register to Lakshya")
            return redirect(url_for("login"))

    return render_template("login.html")

# Slot Booking route
@app.route('/book', methods=["GET", "POST"])
def slot_booking():
    if "email" not in session:
        return redirect(url_for("login"))

    selected_date = request.args.get("date") or dates[0]
    email = session["email"]
    existing_booking = booking_db.bookings.find_one({"email": email})

    # Build slot data for display
    slot_data = []
    for slot_code, slot_label in slots:
        count_doc = booking_db.slot_counts.find_one({"date": selected_date, "slot": slot_code})
        count = count_doc["count"] if count_doc else 0
        remaining = 30 - count
        slot_data.append({
            "slot": slot_code,
            "label": slot_label,
            "remaining": remaining,
            "status": "Available" if remaining > 0 else "Full"
        })

    # Handle booking
    if request.method == "POST":
        slot = request.form.get("slot")

        if existing_booking:
            flash("Your slot has already been booked. Only one booking per person is allowed.")
        else:
            result = booking_db.slot_counts.find_one_and_update(
                {"date": selected_date, "slot": slot, "count": {"$lt": 30}},
                {"$inc": {"count": 1}},
                return_document=ReturnDocument.AFTER
            )

            if result:
                booking_db.bookings.insert_one({
                    "email": email,
                    "date": selected_date,
                    "slot": slot,
                    "timestamp": datetime.datetime.now()
                })
                flash("Booking confirmed!")
                return redirect(url_for("slot_booking", date=selected_date))
            else:
                flash("Slot full! Please choose another.")

    return render_template(
        "slot_booking.html",
        date=selected_date,
        slots=slot_data,
        dates=dates,
        already_booked=True if existing_booking else False,
        booked_info=existing_booking
    )

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)
