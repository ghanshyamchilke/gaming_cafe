from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import config

app = Flask(__name__)

# SECRET KEY
app.secret_key = config.SECRET_KEY

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///games.db"

app.config["SQLALCHEMY_BINDS"] = {
    "bookings": "sqlite:///bookings.db"
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# IMAGE UPLOAD CONFIG
UPLOAD_FOLDER = "static/images/games"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# CREATE DATABASE
db = SQLAlchemy(app)

# CREATE FOLDER IF NOT EXISTS
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ DATABASE ------------------ #

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    mobile = db.Column(db.String(20))

    password = db.Column(db.String(200), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

class Game(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    system = db.Column(db.String(50))

    price = db.Column(db.Integer)

    image = db.Column(db.String(200))

class Booking(db.Model):

    __bind_key__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    mobile = db.Column(db.String(20))

    time_slot = db.Column(db.String(50))

    game_name = db.Column(db.String(100))

    status = db.Column(db.String(20), default="Pending")

class GameRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    game_name = db.Column(db.String(100))

# ------------------ HOME ------------------ #

@app.route("/")
def home():
    games = Game.query.limit(4).all()
    return render_template("home.html", games=games, systems=config.SYSTEMS)

# ------------------ REGISTER ------------------ #

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = generate_password_hash(request.form["password"])

        user = User(
            name=name,
            email=email,
            mobile=mobile,
            password=password
        )


        db.session.add(user)
        db.session.commit()

        flash("Registration successful")
        return redirect("/login")

    return render_template("register.html")

# ------------------ LOGIN ------------------ #
from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["user_name"] = user.name
            session["is_admin"] = user.is_admin

            return redirect("/")

        else:
            flash("Invalid email or password")

    return render_template("login.html")
# ------------------ LOGOUT ------------------ #

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
# ------------------ GAMES ------------------ #

@app.route("/games")
def games():

    games = Game.query.all()

    return render_template("games.html", games=games)

# ------------------ BOOKING ------------------ #

@app.route("/booking", methods=["GET","POST"])
def booking():

    if "user_id" not in session:
        return redirect("/login")

    games = Game.query.all()

    if request.method == "POST":

        game = request.form["game"]
        system = request.form["system"]
        slot = request.form["slot"]
        mobile = request.form["mobile"]

        book = Booking(
            name=session["user_name"],
            mobile=mobile,
            time_slot=slot,
            game_name=game
        )

        db.session.add(book)
        db.session.commit()
        
        flash("Booking confirmed!")

    return render_template("booking.html", games=games)

# ------------------ PROFILE ------------------ #

@app.route("/profile", methods=["GET","POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])
    bookings = Booking.query.filter_by(name=session["user_name"])

    if request.method == "POST":

        game = request.form["game"]

        req = GameRequest(user_id=session["user"], game_name=game)

        db.session.add(req)
        db.session.commit()

        flash("Game request submitted")

    return render_template("profile.html", user=user, bookings=bookings)

# ------------------ ADMIN DASHBOARD ------------------ #

@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return redirect("/")

    users = User.query.count()
    bookings = Booking.query.count()
    games = Game.query.count()

    return render_template(
        "admin_dashboard.html",
        users=users,
        bookings=bookings,
        games=games
    )

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("is_admin"):
        return redirect("/login")

    users = User.query.count()
    games = Game.query.count()
    bookings = Booking.query.count()

    ps5 = Game.query.filter_by(system="PS5").count()
    pc = Game.query.filter_by(system="PC").count()
    wheel = Game.query.filter_by(system="Steering Wheel").count()

    return render_template(
        "admin_dashboard.html",
        users=users,
        games=games,
        bookings=bookings,
        ps5=ps5,
        pc=pc,
        wheel=wheel
    )

@app.route("/admin/accept_booking/<int:id>")
def accept_booking(id):

    if not session.get("is_admin"):
        return redirect("/login")

    booking = Booking.query.get(id)

    booking.status = "Accepted"

    db.session.commit()

    return redirect("/admin/bookings")

@app.route("/admin/reject_booking/<int:id>")
def reject_booking(id):

    if not session.get("is_admin"):
        return redirect("/login")

    booking = Booking.query.get(id)

    booking.status = "Rejected"

    db.session.commit()

    return redirect("/admin/bookings")

@app.route("/admin/add_game", methods=["GET","POST"])
def add_game():

    if not session.get("is_admin"):
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        system = request.form["system"]
        price = request.form["price"]

        game = Game(
            name=name,
            system=system,
            price=price
        )

        db.session.add(game)
        db.session.commit()

        return redirect("/admin/games")

    return render_template("add_game.html")
# ------------------ ADMIN GAMES ------------------ #
@app.route("/admin/games")
def admin_games():

    if not session.get("is_admin"):
        return redirect("/login")

    games = Game.query.all()

    return render_template("admin_games.html", games=games)

@app.route("/admin/delete_game/<int:id>")
def delete_game(id):

    if not session.get("is_admin"):
        return redirect("/login")

    game = Game.query.get(id)

    db.session.delete(game)
    db.session.commit()

    return redirect("/admin/games")

@app.route("/admin/upload_image/<int:game_id>", methods=["GET","POST"])
def upload_image(game_id):

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":

        image = request.files["image"]

        if image:
            filename = image.filename
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            game.image = filename
            db.session.commit()

        return redirect("/admin/games")

    return render_template("upload_image.html", game=game)
# ------------------ ADMIN BOOKINGS ------------------ #

@app.route("/admin/bookings")
def admin_bookings():

    if not session.get("is_admin"):
        return redirect("/login")

    bookings = Booking.query.all()

    return render_template("admin_bookings.html", bookings=bookings)
# ------------------ RUN APP ------------------ #
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@gamingcafe.com").first()

    if not admin:

        admin_user = User(
            name="Admin",
            email="admin@gamingcafe.com",
            mobile="9999999999",
            password=generate_password_hash("admin123"),
            is_admin=True
        )

        db.session.add(admin_user)
        db.session.commit()
    app.run(debug=True)