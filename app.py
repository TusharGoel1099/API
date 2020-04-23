
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
import pickle
import json
from textblob import TextBlob
from flask_mysqldb import MySQL
from wtforms import Form, StringField,IntegerField, TextAreaField, PasswordField, validators
from functools import wraps
app = Flask(__name__)
with open("config.json") as r:
  param=json.load(r)['params']
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'tushar_intern'
app.config['MYSQL_DB'] = 'flask'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)
@app.route('/')
def index():
    return render_template('home.html')


class RegisterForm(Form):
    username=StringField('Username', [validators.Length(min=1, max=50)])
    emailid=StringField('Emailid', [validators.Length(min=4, max=25)])
    contact=IntegerField('Contact', [validators.DataRequired()])
    favorite_food_id=StringField('favorite_food_id', [validators.Length(min=6, max=50)])
    password=PasswordField('Password', [
        validators.DataRequired()
    ])
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        emailid = form.emailid.data
        contact = form.contact.data
        password = form.password.data
        favorite_food_id = form.favorite_food_id.data
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(username, emailid, contact, password,favorite_food_id) VALUES(%s, %s, %s, %s,%s)", (username, emailid, contact, password,favorite_food_id))
        mysql.connection.commit()
        cur.close()
        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['password']
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            if(new_password==password):
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
  if request.method=="POST":
        search=request.form['search']
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM finefood WHERE ProductId = %s", [search])
        if result > 0:
            data = cur.fetchall()
            count1=0
            count=0
            dic={'text':[],'score':[],'polarity':[],'positive_co':[],'negative_co':[]}
            dic2={}
            param['texting']=[]
            for i in data:
                param['texting'].append(i['Text'])
            dbfile = open('sentimental', 'rb')      
            db = pickle.load(dbfile) 
            dbfile1 = open('vect', 'rb')      
            db1 = pickle.load(dbfile1) 
            y=db1.transform(param['texting'])
            sentiment=db.predict(y)
            sentiment=list(sentiment)
            counting=0
            for i in data:
                dic['score'].append(i['Score'])
                zen=TextBlob(i['Text']).sentiment.polarity
                dic['polarity'].append(zen)
                dic['text'].append(i['Text'])
                if(sentiment[counting]==0):
                    count1+=1
                    dic['negative_co'].append(i['Text'])
                else:
                    count+=1
                    dic['positive_co'].append(i['Text'])  
                counting+=1
            cur.close()
        dic2['total']=len(sentiment)
        dic2['positive']=round(((count)/len(sentiment))*100,2)
        dic2['negative']=round(((count1)/len(sentiment))*100,2)
        dic2['average']=round(sum(dic['score'])/len(dic['score']),2)
        dic2['positive_co']=dic['positive_co'][:5]
        dic2['negative_co']=dic['negative_co'][:5]
        dic2['username']=session['username']
        return render_template('dashboard.html',data=dic2)
  return render_template("search.html")


if __name__ == '__main__':
    app.secret_key='intern123'
    app.run(debug=True)