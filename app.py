from flask import Flask, render_template, flash, redirect, session, url_for, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# config database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/articles')
def articles():
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()
    cur.close()
    # CLOSE CONNECTION
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        return render_template('articles.html', msg="No Article Found")


@app.route('/article/<string:id>/')
def article(id):
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id= %s", [id])
    article = cur.fetchone()
    cur.close()
    # CLOSE CONNECTION
    if result > 0:
        return render_template('alonearticle.html', article=article)
    else:
        flash("No article Found", "dark")
        return redirect(url_for('articles'))


# Register form
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=3, max=50)])
    username = StringField('Username', [validators.Length(min=5, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        # PERFORM MYSQL QUERY
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)",
                    (name, email, username, password))
        mysql.connection.commit()
        cur.close()
        # CLOSE CONNECTION
        flash('You are registered and can now log in ', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password_candid = request.form['password']
        # PERFORM MYSQL QUERY
        cur = mysql.connection.cursor()
        result = cur.execute(
            'SELECT * FROM users WHERE username = %s', [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            cur.close()
            # CLOSE CONNECTION
            if sha256_crypt.verify(password_candid, password):
                session['logged_in'] = True
                session['username'] = username
                flash("You are now logged in", "success")
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid login")
        else:
            return render_template('login.html', error="Username Not Found")
    return render_template('login.html')


# Check if user is logged in decorator function
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized, Please Login", "danger")
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
def dashboard():
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    result = cur.execute(
        "SELECT * FROM articles WHERE author = %s", [session['username']])
    articles = cur.fetchall()
    cur.close()
    # CLOSE CONNECTION
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        return render_template('dashboard.html', smsg="No Article Found", naf=True)


# article form
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=5, max=255)])
    body = TextAreaField('Body', [validators.Length(min=30)])


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        body = form.body.data
        # PERFORM MYSQL QUERY
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title,body,author) VALUES(%s,%s,%s)",
                    (title, body, session['username']))
        mysql.connection.commit()
        cur.close()
        # CLOSE CONNECTION
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template("add_article.html", form=form)


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    result = cur.fetchone()
    cur.close()
    # CLOSE CONNECTION
    form = ArticleForm(request.form)
    form.title.data = result['title']
    form.body.data = result['body']

    if request.method == "POST" and form.validate():
        title = request.form['title']
        body = request.form['body']
        # PERFORM MYSQL QUERY
        cur = mysql.connection.cursor()
        cur.execute("UPDATE articles SET title=%s , body=%s WHERE id = %s", (title, body, id))
        mysql.connection.commit()
        cur.close()
        # CLOSE CONNECTION
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template("edit_article.html", form=form)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    # CLOSE CONNECTION
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete_me/<string:username>', methods=['POST'])
@is_logged_in
def delete_me(username):
    # PERFORM MYSQL QUERY
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", [username])
    mysql.connection.commit()
    cur.close()
    # CLOSE CONNECTION
    session.clear()
    flash("Account Deleted successfully and their's no way we can restore it", "info")
    return redirect(url_for('register'))


if __name__ == "__main__":
    app.secret_key = "secretla"
    app.run()
