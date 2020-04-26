
from flask import Flask, render_template, flash,jsonify, redirect, url_for, session, request, logging,make_response
import json
import requests
import random
import jwt
import uuid 
import datetime
from wtforms import Form, StringField,IntegerField, TextAreaField, PasswordField, validators
from flask_mysqldb import MySQL
from functools import wraps
app = Flask(__name__)
with open("config.json") as r:     #used to get default values
  param=json.load(r)['params']
app.config['SECRET_KEY'] = 'thisissecret'  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)
@app.route('/')
def index():
    return "hello world"
class RegisterForm(Form):
    name=StringField('name', [validators.Length(min=1, max=50)])
    gender=StringField('gender', [validators.Length(min=4, max=25)])
    DOB=IntegerField('DOB', [validators.DataRequired()])
def token_required(f):   #it is used to validate a token
    @wraps(f)
    def decorated(*args, **kwargs):  #decorator
        token = None
        if 'x-access-token' in request.headers:
           token=request.headers['x-access-token']
        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current=data['id']
        except:
            return jsonify({'message' : 'Token is invalid!'}), 403

        return f(current,*args, **kwargs)

    return decorated
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:    #chechking current session
            return f(session['otp'],*args, **kwargs)
        else:
            return make_response("GO get some otp for you")
    return wrap
@app.route('/users/send-otp', methods=['GET', 'POST'])
def sendotp():    #function used to send otp
    mobile=request.form['mobile']
    otp=""
    for i in range(4):
        otp+=str(random.randint(1,9))
    URL = 'https://www.sms4india.com/api/v1/sendCampaign'
    def sendPostRequest(reqUrl, apiKey, secretKey, useType, phoneNo, senderId, textMessage):
        req_params = {
        'apikey':apiKey,
        'secret':secretKey,
        'usetype':useType,
        'phone': phoneNo,
        'message':textMessage,
        'senderid':senderId
        }
        return requests.post(reqUrl, req_params)
    response = sendPostRequest(URL, '2910QIWQW9WJL1K0FYE75D9ZUURASSWL', 'IGZIT5E9TOBIS47H', 'stage', mobile, 'TUSHARG', otp )
    session['logged_in'] = True
    session['otp'] = otp
    return jsonify({"message":"msg sent"}),200

@app.route('/users/otp', methods=['POST'])   
@is_logged_in
def otp(otp2):   #function used to verfiy otp
    mobile =request.form['mobile'] 
    otp = request.form['otp']
    if(mobile =="" or otp ==""):
        return jsonify({"message":"enter params"}),400
    if(otp2==otp):
          return jsonify({'message' : 'You are authenticated'}),200
    else:
          return  jsonify({'message' : 'wrong otp'}),400

@app.route('/users', methods=['GET', 'POST'])
@is_logged_in
def register(id):            #used to register user
         if request.method == 'POST':
               name =request.form['name'] 
               gender = request.form['gender']
               id=str(uuid.uuid4())
               DOB = request.form['DOB']
               if(name =="" or DOB==""):
                   return  jsonify({"message":'empty params'}),400
               if(gender ==""):
                   gender="male"
               if(gender not in param['gender']):
                   return  jsonify({"message":'select valid gender either male or female'}),400
               try:
                   datetime.datetime.strptime(DOB, "%Y-%m-%d")
                   token=jwt.encode({'id':id,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=120)},app.config['SECRET_KEY'])
                   cur = mysql.connection.cursor()
                   cur.execute("INSERT INTO sample_user(name, gender, DOB, id) VALUES(%s, %s, %s, %s)", (name, gender, DOB,id))
                   mysql.connection.commit()
                   cur.close()
                   return jsonify({"message":"user_registered","token":token.decode('UTF-8'),"ID":id}),200
               except:
                   return jsonify({"message":"provide correct format of DOB"}),400

@app.route('/users/<id>', methods=['PUT'])
@token_required
def update(current,id):                #used to update an existing user details
    name =request.form['name']  
    gender = request.form['gender']
    DOB = request.form['DOB']
    if(name =="" and gender =="" and DOB =="" ):
        return jsonify({"message":"Nothing is updated"}),400
    else:
        if(name):
            cur = mysql.connection.cursor()
            cur.execute("UPDATE sample_user SET name = %s WHERE id = %s ", (name,id))
            mysql.connection.commit()
            cur.close()
        if(gender):
            if(gender not in param['gender']):
                return jsonify({"message":"select a default gender"}),400
            else:
                cur = mysql.connection.cursor()
                cur.execute("UPDATE sample_user SET gender =%s WHERE id = %s ", (gender,id))
                mysql.connection.commit()
                cur.close()
        if(DOB):
            try:
                datetime.datetime.strptime(DOB, "%Y-%m-%d")
                cur = mysql.connection.cursor()
                cur.execute("UPDATE sample_user SET DOB =%s WHERE id = %s ", (DOB,id))
                mysql.connection.commit()
                cur.close()
            except:
                return jsonify({"message":"enter correct date format"})
        return jsonify({"message":"updated succesfully"}),200   
    return jsonify({'message' : id})
@app.route('/users/<id>', methods=['GET'])  
@token_required
def get_users(id):                       #used to fetch an current user detail
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM sample_user WHERE id = %s", [id])
    if result > 0:
            data = cur.fetchone()
            return jsonify({"name":data['name'],"gender":data['gender'],"DOB":data['DOB']})
    else:
        return make_response("no user exist")
    cur.close()
@app.route('/users/addcategory', methods=['POST'])    #used to add an category
@token_required
def add_category(current):
    category=request.form['category']
    if(category==""):
        return jsonify({"message":"please pass a valid param"})
    else:
        param['category']+=[category]
        return jsonify({"message":"category added succesfully"})
@app.route('/users/viewcategory', methods=['GET'])    #used to view all the categories
@token_required
def view_category(current):
    return jsonify({"addedcategories":param['category'],'defaultcategory':param['default_category']})
@app.route('/users/deletecategory', methods=['POST'])    #udes to delete a category
@token_required
def delete_category(current):
    category=request.form['category']
    if(category ==""):
        return jsonify({"message":"please pass a valid param"})     
    if(category in param['default_category']):
        return jsonify({'message':"its a default category and cannot be deleted"})
    else:
        param['category'].remove(category)
        return jsonify({"message":"deleted successfully"})
@app.route('/users/filter', methods=['GET'])
@token_required
def filter(current):               #used to filter out the expenses
    category=request.form["category"]
    day=request.form["day"]
    amount_range=request.form["amount_range"]
    range1=amount_range.split("-")
    if(category=="" or day=="" or amount_range==""):
        return jsonify({"message":"please fill out the params"})
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM expense WHERE id = %s and category=%s and day=%s and amount BETWEEN %s AND %s ", (current,category,int(day),int(range1[0]),int(range1[1])))
    if result > 0:
            data = cur.fetchall()
            return jsonify({"expenses":data})
    else:
        return jsonify({"message":"no expenses for current filters"})
    cur.close()
@app.route('/users/expenses', methods=['POST'])
@token_required
def expenses(current):   #used to add an expense
    amount =request.form['amount'] 
    category = request.form['category']
    day = request.form['day']
    month = request.form['month']
    if( month == "" or category == "" or day =="" or amount ==""):
            return jsonify({"message":"please fill out params "}),400
    if(day.isnumeric()==False or month.isnumeric()==False):
        return jsonify({"message":"day and month are not in integer format "}),400
    if(category not in param['category']):
        return jsonify({"message":"this category is not available either you choose a default one or you need to add this category using /addcategory"}),400
    else:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO expense(id, amount, category, day,month) VALUES(%s, %s, %s, %s,%s)", (current,amount, category, day,month))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message":"expense added"}),200
@app.route('/users/view/expenses', methods=['GET'])
@token_required
def view_expenses(current):    #used to view all the expenses
    output=[]
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM expense WHERE id = %s", [current])
    if result > 0:
        data = cur.fetchall()
        for i in data:
            output.append(i)
        return jsonify({"expenses":output})
    else:
        return jsonify({"message":"Not added an expense yet"})
if __name__ == '__main__':
    app.secret_key='intern123'
    app.run(debug=True)