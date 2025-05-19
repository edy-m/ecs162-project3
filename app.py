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

@app.route('/')
def home():
    user = session.get('user')
    allComments = list(COMMENTS.find())
    commDictionary = defaultdict(list)
    for comm in allComments:
        comm['_id'] = str(comm['_id'])
        articleNumber = comm.get('articleNum')
        if comm.get('root'):
            comm['root'] = str(comm['root'])
        commDictionary[articleNumber].append(comm)
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

@app.route('/post-comment', methods=['POST'])
def post_comment():
    user = session.get('user', {})
    if not user:
        return redirect('/login')
    commentContent = request.form['comment']
    articleNum = request.form['articleNum']
    root = request.form.get('root')
    comment = {
        "user_name": user.get('name'),
        "comment": commentContent,
        "articleNum": articleNum,
        "root": root
    }

    COMMENTS.insert_one(comment)

    return redirect('/')

@app.post('/<id>/delete/')
def delete(id):
    COMMENTS.delete_one({"_id": ObjectId(id)})
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)

