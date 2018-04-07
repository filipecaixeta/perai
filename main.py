from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
from bs4 import BeautifulSoup
import requests
from newspaper import Article
import datetime

app = Flask(__name__)

app.config['MONGO_DBNAME'] = ''
app.config['MONGO_URI'] = 'mongodb://root:42@ds131826.mlab.com:31826/perai'

mongo = PyMongo(app)

def getPageRequests(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "lxml")
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()
    return {'title': "", 'text': text}

def getPageArticle(url):
    article = Article(url)
    article.download()
    article.parse()
    return {'title': article.title, 'text': article.text}

def getPage(url):
    return getPageArticle(url)

def createNewsArticle(url):
    data = {
        'url': url,
        'share': [],
        'report': [],
        'created': datetime.datetime.now(),
        **getPage(url)
    }
    _id = mongo.db.posts.insert_one(data)
    return {'_id': _id, **data}

def getNewsArticle(url):
    n = mongo.db.posts.find_one({'url': url})
    if n is None:
        return createNewsArticle(url)
    return n

def getNewsArticleStatistics(url=None):
    q = [{'$project':{'numShare': { '$size': "$share" },
                      'numReport': { '$size': "$report" },
                      'url':True }}]
    if url is not None:
        q = [{'$match': {'url': url}}]+q

    return list(mongo.db.posts.aggregate(q))

def updateNewsArticle(fbid, url, field):
    n = getNewsArticle(url)
    mongo.db.posts.update_one({'_id': n['_id']},
                              {'$addToSet': {field : fbid}},
                              False, True)

def share(fbid, url):
    updateNewsArticle(fbid, url, "share")

def report(fbid,url):
    updateNewsArticle(fbid, url, "report")

@app.route('/post_statistics', methods=['GET'])
def post_statistics():
    url = request.args.get('url', default=None, type=str)
    result = getNewsArticleStatistics(url)
    for r in result:
        if '_id' in r:
            del r['_id']
    return jsonify(result)

def updatePost(func):
    url = request.form.get('url', default=None, type=str)
    fbid = request.form.get('fbid', default=None, type=str)
    if (url is not None) and (fbid is not None):
        func(fbid, url)
        return jsonify({'status':'success'})
    else:
        return jsonify({'status':'missing fields'})

@app.route('/post_share', methods=['POST'])
def post_share():
    return updatePost(share)

@app.route('/post_report', methods=['POST'])
def post_report():
    return updatePost(report)

@app.route('/', methods=['GET','POST'])
def home():
    return jsonify({'status':'server running'})

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0',port=80)
