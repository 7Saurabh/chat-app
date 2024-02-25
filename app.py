from flask import Flask, render_template, redirect, url_for, request, session, make_response
from flask_socketio import send, join_room, leave_room, SocketIO, emit
import random
from string import ascii_uppercase
from flask_mysqldb import MySQL
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretshshsh"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "Sm@90402002"
app.config["MYSQL_DB"] = "chatrooms"
socketio = SocketIO(app)
mysql = MySQL(app)

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        with mysql.connection.cursor() as cur:
            cur.execute(f"""
            CREATE TABLE {code} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                message VARCHAR(255),
                created_at VARCHAR(255)
            )
            """)
            mysql.connection.commit()
        return code
    
def generate_refer_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        return code

@socketio.on("message")
def message(data):
    room = session.get("room")

    content = {
        "name": session.get("name"),
        "message": data["data"],
        "time": datetime.now().strftime("%I:%M %p")
    }
    send(content, to=room)

    with mysql.connection.cursor() as cur:
        cur.execute(f"INSERT INTO {room} (name, message, created_at) VALUES (%s, %s, %s)", (content["name"], content["message"], content["time"]))
        mysql.connection.commit()
    

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    join_room(room)
    send({"name": name, "message": "has entered the room","time":""}, to=room)

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")

    leave_room(room)
    send({"name": name, "message": "has left the room","time":""}, to=room)

@app.route('/signup',methods=['GET','POST'])
def signup():
    error = "noerror"
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username != None:
            is_space = False
            for space in username:
                    if space == " ":
                        is_space=True
                        
            if is_space == True:
                error="The username should not contain any spaces. Please choose a username without spaces."
            else:

                with mysql.connection.cursor() as cur:
                    cur.execute("SELECT username FROM auth WHERE username=(%s)",(username,))
                    username_exists = cur.fetchone()
                

                if username_exists is None:
                    with mysql.connection.cursor() as cur:
                        cur.execute(f"INSERT INTO auth (username,password,refer_code) VALUES (%s,%s,%s)", (username, password, generate_refer_code(5)))
                        mysql.connection.commit()
                    

                    with mysql.connection.cursor() as cur:
                        cur.execute(f"""
                            CREATE TABLE {username} (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                friend_names VARCHAR(255),
                                friend_codes VARCHAR(255),
                                group_names VARCHAR(255),
                                group_codes VARCHAR(255),
                                friend_status VARCHAR(20)
                            )
                            """)
                        mysql.connection.commit()
                        
                    return redirect(url_for('login'))
                else: error="The username is already taken. Please choose a different username."
    return render_template('signup.html',signup="True",error=error)

@app.route('/',methods=['GET','POST'])
def login():
    error = "noerror"
    if request.method=="POST":
        username = request.form.get("username")
        input_password = request.form.get("password")
        if username != None:
            with mysql.connection.cursor() as cur:
                cur.execute("SELECT password FROM auth WHERE username=(%s)",(username,))
                db_password = cur.fetchone() 
            
            try:
                if input_password == db_password[0]:

                    session['name'] = username
                    return redirect(url_for('userhome'))
                else: error="username password didn't matched !"
            except:
                error =  "username password didn't matched !"
    
    return render_template('signup.html',login="True",error=error)

@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('room', None)
    return(redirect(url_for('login')))


@app.route('/userhome',methods=['GET','POST'])
def userhome():
    username = session.get("name")
    if username is None:
        return redirect(url_for('login'))
    messages = ""
    room = ""
    chat_room_header_name = " value"

    with mysql.connection.cursor() as cur:
        cur.execute(f'SELECT friend_names,friend_codes FROM {username} WHERE friend_status="request_accepted"')
        friends = cur.fetchall() 

    with mysql.connection.cursor() as cur:
        cur.execute(f'SELECT refer_code FROM auth WHERE username="{username}"')
        user_refer_code = cur.fetchone() 

    chat_friend_code = request.form.get("chat_friend_button") #this is code which is common between two users
    if chat_friend_code is not None:
        session["room"] = chat_friend_code

        #ROOM ROUTE ADDED HERE
        room = session.get("room")
        with mysql.connection.cursor() as cur:
            cur.execute(f"SELECT name,message,created_at FROM {room}")
            messages = cur.fetchall()

        #CHATROOM HEAD i.e name of friend while chatting
        with mysql.connection.cursor() as cur:
            cur.execute(f"SELECT friend_names FROM {username} WHERE friend_codes='{room}'")
            chat_room_header_name = cur.fetchone()
               

    #ADDFRIEND ROUTE ADDED HERE 
    username = session.get('name')
    unique_refer_code = generate_unique_code(6)    

    #GETTING WHO'S FREIND REQUESTS HAVE RECEIVED
    with mysql.connection.cursor() as cur:
        cur.execute(f'SELECT friend_names FROM {username} WHERE friend_status="request_received"')
        requests_received = cur.fetchall() 
    

    if request.method == "POST":       
        friend_refer_code = request.form.get("friend_code")

        if friend_refer_code is not None:
            #GETTING FRIEND NAME
            with mysql.connection.cursor() as cur:
                cur.execute(f'SELECT username FROM auth WHERE refer_code=(%s)',(friend_refer_code,))
                friend_name = cur.fetchone() 

            #CHECKING WHETHER USER NOT SENDING REQUEST TO HIMSELF
            if username != friend_name[0]:               

                #CHECKING WHETHER THEY ARE ALREADY FRIENDS
                with mysql.connection.cursor() as cur:            
                    cur.execute(f'SELECT friend_status from {username} WHERE friend_names="{friend_name[0]}"')
                    request_status = cur.fetchone() 

                if request_status is None: #Allowing only when they are not friends to send request
                    print('they are not friends')
                
                    #ADDING friend_status TO USER TABLE
                    with mysql.connection.cursor() as cur:
                        cur.execute(f'INSERT INTO {username} (friend_names,friend_codes,friend_status) VALUES (%s,%s,"request_sent")', (friend_name[0],unique_refer_code,))
                        mysql.connection.commit()
                        
                    #ADDING friend_status TO FRIEND TABLE
                    with mysql.connection.cursor() as cur:
                        cur.execute(f'INSERT INTO {friend_name[0]} (friend_names,friend_codes,friend_status) VALUES (%s,%s,"request_received")', (username,unique_refer_code,))
                        mysql.connection.commit()
                    
                else :print('They are already Friends')

            else:print("they are sending request to themselves only !!!")
        
        #LOGOUT
        if request.form.get("logout") == "logout":
            return redirect(url_for('logout'))
        
        accept_button = request.form.get("accept_button")
        if accept_button is not None:
            friend_name = accept_button
            #ACCEPTING friend_status TO USER TABLE
            with mysql.connection.cursor() as cur:
                cur.execute(f'UPDATE {username} SET friend_status = "request_accepted" WHERE friend_names = (%s)',(friend_name,))
                mysql.connection.commit()
            
            #ACCEPTING friend_status TO FRIEND TABLE
            with mysql.connection.cursor() as cur:
                cur.execute(f'UPDATE {friend_name} SET friend_status = "request_accepted" WHERE friend_names = (%s)',(username,))
                mysql.connection.commit()
            
            return redirect(url_for('userhome')) #change

    return render_template('application.html', chat_room_header_name=chat_room_header_name[0], username=username,code=room,messages=messages,requests_received=requests_received,friends=friends, user_refer_code = user_refer_code[0])

if __name__ == "__main__":
    # socketio.run(app, debug=True,host="0.0.0.0")
    socketio.run(app,debug=True)
