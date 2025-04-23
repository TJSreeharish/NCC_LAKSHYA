from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
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
    
    slots = [
        ("8:30", "07:30 - 09:00"),
        ("9:30", "09:00 - 10:30"),
        ("10:30", "10:30 - 12:00"),
        ("11:30", "11:00 - 12:30"),
        ("12:30", "13:00 - 14:30"),
        ("2:30", "15:00 - 16:30"),
        ("3:30", "16:30 - 18:00")
    ]
    dates = ["26 April", "27 April"]
    
    selected_date = request.args.get("date") or dates[0]
    
    # Check if user has already booked any slot on any day
    email = session["email"]
    existing_booking = booking_db.bookings.find_one({"email": email})
    
    slot_data = []
    for slot_code, slot_label in slots:
        count = booking_db.bookings.count_documents({
            "date": selected_date,
            "slot": slot_code
        })
        remaining = 30 - count
        slot_data.append({
            "slot": slot_code,
            "label": slot_label,
            "remaining": remaining,
            "status": "Available" if remaining > 0 else "Full"
        })
    
    if request.method == "POST":
        slot = request.form.get("slot")
        
        # Check if user already has a booking on any day
        if existing_booking:
            flash("Your slot has already been booked. Only one booking per person is allowed.")
        else:
            # Check slot availability
            count = booking_db.bookings.count_documents({
                "date": selected_date,
                "slot": slot
            })
            
            if count >= 30:
                flash("Slot full! Please choose another.")
            else:
                booking_db.bookings.insert_one({
                    "email": email,
                    "date": selected_date,
                    "slot": slot,
                    "timestamp": datetime.datetime.now()
                })
                flash("Booking confirmed!")
                return redirect(url_for("slot_booking", date=selected_date))
    
    return render_template(
        "slot_booking.html", 
        date=selected_date, 
        slots=slot_data, 
        dates=dates, 
        already_booked=True if existing_booking else False,
        booked_info=existing_booking
    )

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)
