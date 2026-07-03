from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "library123"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Root@123",
    database="library_management"
)

cursor = db.cursor()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            cursor.execute("SELECT COUNT(*) FROM books")
            total_books = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM students")
            total_students = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM issued_books WHERE status='Issued'")
            issued_books = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(quantity) FROM books")
            available_books = cursor.fetchone()[0]

            return render_template(
                "dashboard.html",
                total_books=total_books,
                total_students=total_students,
                issued_books=issued_books,
                available_books=available_books
            )
        else:
            return render_template(
                "login.html",
                message="Invalid Username or Password"
            )

    return render_template("login.html")


# ---------------- BOOKS ----------------
@app.route("/books")
def books():
    search = request.args.get("search")

    if search:
        like = "%" + search + "%"

        cursor.execute("""
            SELECT *
            FROM books
            WHERE book_name LIKE %s
               OR author LIKE %s
               OR category LIKE %s
        """, (like, like, like))
    else:
        cursor.execute("SELECT * FROM books")

    books = cursor.fetchall()

    return render_template(
        "books.html",
        books=books,
        search=search
    )


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        book_name = request.form["book_name"]
        author = request.form["author"]
        category = request.form["category"]
        quantity = request.form["quantity"]

        cursor.execute("""
            INSERT INTO books(book_name, author, category, quantity)
            VALUES(%s,%s,%s,%s)
        """, (book_name, author, category, quantity))

        db.commit()
        return redirect("/books")

    return render_template("add_book.html")


@app.route("/edit_book/<int:id>", methods=["GET", "POST"])
def edit_book(id):
    if request.method == "POST":
        book_name = request.form["book_name"]
        author = request.form["author"]
        category = request.form["category"]
        quantity = request.form["quantity"]

        cursor.execute("""
            UPDATE books
            SET book_name=%s,
                author=%s,
                category=%s,
                quantity=%s
            WHERE id=%s
        """, (book_name, author, category, quantity, id))

        db.commit()
        return redirect("/books")

    cursor.execute("SELECT * FROM books WHERE id=%s", (id,))
    book = cursor.fetchone()

    return render_template("edit_book.html", book=book)


@app.route("/delete_book/<int:id>")
def delete_book(id):
    cursor.execute("DELETE FROM books WHERE id=%s", (id,))
    db.commit()
    return redirect("/books")


# ---------------- STUDENTS ----------------
@app.route("/students")
def students():

    query = request.args.get("query")

    if query:
        cursor.execute(
            "SELECT * FROM students WHERE name LIKE %s OR roll_no LIKE %s OR dept LIKE %s",
            ('%' + query + '%', '%' + query + '%', '%' + query + '%')
        )
    else:
        cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template("students.html", students=students)

@app.route("/delete_student/<int:id>")
def delete_student(id):
    try:
        cursor.execute("DELETE FROM students WHERE id=%s", (id,))
        db.commit()
    except mysql.connector.IntegrityError:
        return "Cannot delete this student because they have issued/returned book records."

    return redirect("/students")

@app.route("/add_student", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":
        student_name = request.form["student_name"]
        roll_no = request.form["roll_no"]
        department = request.form["department"]
        year = request.form["year"]
        phone = request.form["phone"]

        cursor.execute("""
            INSERT INTO students
            (student_name, roll_no, department, year, phone)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            student_name,
            roll_no,
            department,
            year,
            phone
        ))

        db.commit()
        return redirect("/students")

    return render_template("add_student.html")

# ---------------- ISSUE BOOK ----------------
@app.route("/issue_book", methods=["GET", "POST"])
def issue_book():
    if request.method == "POST":
        student_id = request.form.get("student_id")
        book_id = request.form.get("book_id")
        issue_date = request.form.get("issue_date")

        cursor.execute("""
            INSERT INTO issued_books
            (student_id, book_id, issue_date, status)
            VALUES (%s,%s,%s,%s)
        """, (student_id, book_id, issue_date, "Issued"))

        cursor.execute("""
            UPDATE books
            SET quantity = quantity - 1
            WHERE id=%s
        """, (book_id,))

        db.commit()

        return redirect(url_for("dashboard"))

    cursor.execute("SELECT id, student_name FROM students")
    students = cursor.fetchall()

    cursor.execute("SELECT id, book_name FROM books WHERE quantity > 0")
    books = cursor.fetchall()

    return render_template(
        "issue_book.html",
        students=students,
        books=books
    )


# ---------------- RETURN BOOK ----------------
@app.route("/return_book", methods=["GET", "POST"])
def return_book():
    if request.method == "POST":
        issue_id = request.form.get("issue_id")
        return_date = request.form.get("return_date")

        if not issue_id:
            return "No issued books available to return."

        cursor.execute("""
            SELECT book_id
            FROM issued_books
            WHERE id=%s
        """, (issue_id,))

        book = cursor.fetchone()
        book_id = book[0]

        cursor.execute("""
            UPDATE issued_books
            SET return_date=%s,
                status='Returned'
            WHERE id=%s
        """, (return_date, issue_id))

        cursor.execute("""
            UPDATE books
            SET quantity = quantity + 1
            WHERE id=%s
        """, (book_id,))

        db.commit()
        return redirect(url_for("dashboard"))

    cursor.execute("""
    SELECT
        issued_books.id,
        students.student_name,
        students.roll_no,
        books.book_name,
        issued_books.issue_date
    FROM issued_books
    JOIN students
        ON issued_books.student_id = students.id
    JOIN books
        ON issued_books.book_id = books.id
    WHERE issued_books.status='Issued'
""")

    issued_books = cursor.fetchall()

    return render_template(
        "return_book.html",
        issued_books=issued_books
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if request.method == "POST":
        student_name = request.form["student_name"]
        roll_no = request.form["roll_no"]
        department = request.form["department"]
        year = request.form["year"]
        phone = request.form["phone"]

        cursor.execute("""
            UPDATE students
            SET student_name=%s,
                roll_no=%s,
                department=%s,
                year=%s,
                phone=%s
            WHERE id=%s
        """, (
            student_name,
            roll_no,
            department,
            year,
            phone,
            id
        ))

        db.commit()
        return redirect("/students")

    cursor.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cursor.fetchone()

    return render_template("edit_student.html", student=student)
@app.route("/dashboard")
def dashboard():

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issued_books WHERE status='Issued'")
    issued_books = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(quantity) FROM books")
    available_books = cursor.fetchone()[0]

    return render_template(
    "dashboard.html",
    total_books=total_books,
    total_students=total_students,
    issued_books=issued_books,
    available_books=available_books
)
 
if __name__ == "__main__":
    app.run(debug=True)