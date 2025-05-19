from flask import Flask, jsonify, redirect, render_template, session, request
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
import os
from pymongo import MongoClient
from collections import defaultdict
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)


oauth = OAuth(app)

nonce = generate_token()

#client = MongoClient('localhost', 27017)
client = MongoClient('mongodb://root:rootpassword@mongo:27017/mydatabase?authSource=admin')
db = client["mydatabase"]
COMMENTS = db['comments']


oauth.register(
    name=os.getenv('OIDC_CLIENT_NAME'),
    client_id=os.getenv('OIDC_CLIENT_ID'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    #server_metadata_url='http://dex:5556/.well-known/openid-configuration',
    authorization_endpoint="http://localhost:5556/auth",
    token_endpoint="http://dex:5556/token",
    jwks_uri="http://dex:5556/keys",
    userinfo_endpoint="http://dex:5556/userinfo",
    device_authorization_endpoint="http://dex:5556/device/code",
    client_kwargs={'scope': 'openid email profile'}
)

# geeksforgeeks - explanation and syntax/structure help for implementing defaultdict
#https://www.geeksforgeeks.org/defaultdict-in-python/
# digitalocean - return render_template
#https://www.digitalocean.com/community/tutorials/how-to-use-mongodb-in-a-flask-application

#added functionality to when we load home
@app.route('/')
def home():
    #allows us to access current user data so we can use them in our code
    user = session.get('user')
    #load all the comments in db and form a dict using imported defaultdict from collections library
    allComments = list(COMMENTS.find())
    #we use default dict to group the comments so we can later access them based on articleNum
    commDictionary = defaultdict(list)
    for comm in allComments:
        #the following lines convert the id automatically given by mongodb to strings instead of objects
        #so we can use in our html
        comm['_id'] = str(comm['_id'])
        articleNumber = comm.get('articleNum')
        #if comment is a reply to a comment
        if comm.get('root'):
            comm['root'] = str(comm['root'])
        #add entry to dictionary
        commDictionary[articleNumber].append(comm)

    #the below commented out code would automatically make us sign in but that isnt necessary
    #since if you attempt to comment/reply you will be automatically asked/required to login from there
    #renders the html page using the user data and comments stored
    return render_template('index.html', user=user, comments=commDictionary)
    #if user:
        #return f"<h2>Logged in as {user['email']}</h2><a href='/logout'>Logout</a>"
    #return '<a href="/login">Login with Dex</a>'

@app.route('/api/key')
def get_key():
    return jsonify({'apiKey': os.getenv('NYT_API_KEY')})

@app.route('/login')
def login():
    session['nonce'] = nonce
    redirect_uri = 'http://localhost:8000/authorize'
    return oauth.flask_app.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/authorize')
def authorize():
    token = oauth.flask_app.authorize_access_token()
    nonce = session.get('nonce')

    user_info = oauth.flask_app.parse_id_token(token, nonce=nonce)  # or use .get('userinfo').json()
    session['user'] = user_info
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

#digital ocean - post and delete comment structure and syntax
#https://www.digitalocean.com/community/tutorials/how-to-use-mongodb-in-a-flask-application

#geeks for geeks - function formation/syntax/structure
#https://www.geeksforgeeks.org/sending-data-from-a-flask-app-to-mongodb-database/

#new post comment function used by html to post a comment
@app.route('/post-comment', methods=['POST'])
def post_comment():
    #redirect user to login if not logged in and tries to comment
    user = session.get('user', {})
    if not user:
        return redirect('/login')
    #init user data
    commentContent = request.form['comment']
    articleNum = request.form['articleNum']
    root = request.form.get('root')
    comment = {
        "user_name": user.get('name'),
        "comment": commentContent,
        "articleNum": articleNum,
        "root": root,       #is the comment a normal comment or a reply to a comment
        "removed": False    #has comment been deleted?
    }

    COMMENTS.insert_one(comment)

    return redirect('/')

# pyMongo help - help using pyMongo functions and understanding hoiw they work such as $set and update.one()
#https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.delete_one
@app.post('/<id>/delete/')
def delete(id):
    #COMMENTS.delete_one({"_id": ObjectId(id)})
    #instead of straight up deleteing a comment entirely from db we just change its contents
    COMMENTS.update_one({"_id": ObjectId(id)}, {"$set": {'comment': "comment was removed by moderator", 'removed': True}})
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)

