import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    total = 0
    total2 = 0
    data = db.execute("SELECT symbol,share, ROUND(price,2), name, current_price FROM shares WHERE person_id = :user_id AND share != 0",user_id = session["user_id"])
    tot = db.execute("SELECT cash FROM users WHERE id = :user_id",user_id = session["user_id"])
    hist = db.execute("SELECT share, price FROM hist WHERE hist_id = :histid", histid = session["user_id"])
    for row in data:
        total =  total + row['ROUND(price,2)']
    for row in hist:
        total2 = total2 + (-1*row['share']*row['price'])
    total2 = round(total2 + 10000,2)
    total1 = tot[0]["cash"] - total
    if session["login"] == True:
        session["login"] = False
        return render_template("index.html", message = "Login Successful", data = data, total = total1, total2=total2)
    elif session["bought"] == True:
        session["bought"] = False
        return render_template("index.html", message = "Stock bought!",data = data, total = total1, total2=total2)
    elif session["sold"] == True:
        session["sold"] = False
        return render_template("index.html", message = "Stock Sold!",data = data, total = total1,  total2=total2)
    else:
        return render_template("index.html", message = "",data = data, total = total1, total2=total2)



@app.route("/buy", methods=["GET", "POST"])
@login_required

def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        check = lookup(request.form.get("symbol"))
        time = datetime.now()
        if not check:
            return apology("Provide correct Stock Symbol",403)
        cost = float(check['price'])
        share = int(request.form.get("share"))
        amount = db.execute("SELECT * FROM users where id = :userid", userid = session["user_id"])
        if (cost * share) >  amount[0]["cash"]:
            return apology("no money",403)
        amount[0]["cash"] -= cost * share
        #db.execute("UPDATE users SET cash = :cash WHERE id = :userid", cash = amount[0]["cash"], userid = session["user_id"])
        rows = db.execute("SELECT symbol FROM shares WHERE person_id = :user_id", user_id = session["user_id"])
        row = [li['symbol'] for li in rows]
        db.execute("INSERT INTO hist (hist_id, symbol, share, price, time) VALUES (:person_id, :symbol, :share, :price, :time)", person_id = session["user_id"], symbol = request.form.get("symbol"), share = share, price = round(cost,2), time = time)
        if request.form.get("symbol") in row:
            db.execute("UPDATE shares SET share = share + :count, price = price + :price WHERE person_id = :user_id AND symbol = :symbol", count = share, price = round((cost*share),2), user_id = session["user_id"], symbol = request.form.get("symbol") )
        else:
            db.execute("INSERT INTO shares (person_id, symbol, share, price, name, current_price) VALUES (:person_id, :symbol, :share, :price, :name, :current_price)", person_id = session["user_id"], symbol = request.form.get("symbol"), share = share, price = round((cost*share),2), name = check['name'], current_price= check['price'])
        session['bought'] = True
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * from hist WHERE hist_id = :user_id", user_id = session["user_id"])
    return render_template("history.html", history = history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["login"] = True
        session["bought"] = False
        session["sold"] = False
        # Redirect user to home page
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "GET":
        return render_template("add.html")
    else:
        money = request.form.get("addcash")
        db.execute("UPDATE users SET cash = cash + :cash WHERE id = :userid", cash = money, userid = session["user_id"])
        return redirect("/")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        row = lookup(request.form.get("symbol"))
        if not row:
            return apology("Stock not found",403)
        stock_name = row["name"]
        stock_price = usd(row["price"])
        return render_template("quoted.html", quote_name = stock_name, quote_price = stock_price)



@app.route("/register", methods=["GET", "POST"])
def register():

    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        re_password = request.form.get("re_password")
        rows = db.execute("SELECT username FROM users WHERE username = :username", username=username)

        if not username:
            return apology("must provide username", 403)
        elif not password:
            return apology("must provide password", 403)
        elif not re_password:
            return apology("Please Enter confirmation password", 403)
        elif password != re_password:
            return apology("Both passwords not matched", 403)
        hash_password = generate_password_hash(password)
        message = "Redirected"
        if rows:
            return apology("Username already exists", 403)
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash_password)", username = username, hash_password = hash_password)
            flash("Registered")
            return redirect("/")
    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        names = db.execute("Select symbol FROM shares WHERE person_id =:user_id AND share != 0", user_id = session["user_id"])
        return render_template("sell.html", names=names)
    else:
        time = datetime.now()
        check = lookup(request.form.get("symbol"))
        cost = float(check['price'])
        want = int(request.form.get('shares'))
        poss = db.execute("Select share FROM shares WHERE person_id = :user_id AND symbol = :symbol", user_id = session["user_id"], symbol = request.form.get("symbol"))
        if poss[0]['share'] < want:
            return apology("You Don't have sufficient shares to sell",403)
        amount = db.execute("SELECT * FROM users where id = :userid", userid = session["user_id"])
        amount[0]["cash"] += cost * want
        #db.execute("UPDATE users SET cash = :cash WHERE id = :userid", cash = amount[0]["cash"], userid = session["user_id"])
        poss[0]['share'] -= want
        db.execute("UPDATE shares SET share = :sharehave, price = price - :price WHERE person_id = :userid AND symbol = :symbol", sharehave = poss[0]['share'], price = cost * want, userid = session["user_id"], symbol = request.form.get("symbol"))
        db.execute("INSERT INTO hist (hist_id, symbol, share, price, time) VALUES (:person_id, :symbol, :share, :price, :time)", person_id = session["user_id"], symbol = request.form.get("symbol"), share = want * -1, price = cost, time = time)
        session['sold'] = True
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)