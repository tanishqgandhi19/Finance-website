from cs50 import SQL
from datetime import datetime
db = SQL("sqlite:///finance.db")
data = db.execute("SELECT symbol,share, ROUND(price,2), name, current_price FROM shares WHERE person_id = 14 AND share != 0")
for row in data:
    total = 10000 - row['ROUND(price,2)']
print(total)
        