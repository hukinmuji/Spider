#import mysql.connector
import hashlib
import time 
from datetime import datetime
from datetime import timedelta

import redis
from pymongo import MongoClient
from pymongo import IndexModel, ASCENDING, DESCENDING


class MongoRedisUrlManager:

    def __init__(self, server_ip='localhost', client=None, expires=timedelta(days=30)):
        """
        client: mongo database client
        expires: timedelta of amount of time before a cache entry is considered expired
        """
        # if a client object is not passed 
        # then try connecting to mongodb at the default localhost port 
        self.client = MongoClient(server_ip, 27017) if client is None else client
        self.redis_client = redis.StrictRedis(host=server_ip, port=6379, db=0) 
        #create collection to store cached webpages,
        # which is the equivalent of a table in a relational database
        self.db = self.client.spider

        # create index if db is empty
        if self.db.jingdong.count() is 0:
            self.db.jingdong.create_index('status')

    def dequeueUrl(self):
        record = self.db.jingdong.find_one_and_update(
            { 'status': 'new'}, 
            { '$set': { 'status' : 'downloading'} }, 
            { 'upsert':False, 'returnNewDocument' : False} 
        )
        if record:
            return record
        else:
            return None

    def enqueueUrl(self, url, status, depth):
        num = self.redis_client.get(url) 
        if num is not None:
            self.redis_client.set(url, int(num) + 1 )
            return
        self.redis_client.set(url, 1)
        self.db.jingdong.insert({
            '_id': hashlib.md5(url.encode('utf8')).hexdigest(), 
            'url': url, 
            'status': status, 
            'queue_time': datetime.utcnow(), 
            'depth': depth,
            'pr':0
        })

    def finishUrl(self, url):
        record = {'status': 'done', 'done_time': datetime.utcnow()}
        self.db.jingdong.update({'_id': hashlib.md5(url.encode('utf8')).hexdigest()}, {'$set': record}, upsert=False)

    def clear(self):
        self.redis_client.flushall()
        self.db.jingdong.drop()

    
    def set_url_links(self, url, links):
        try:
            self.db.urlpr2.insert({
                '_id': hashlib.md5(url.encode('utf8')).hexdigest(), 
                'url': url, 
                'links': links
            })
        except Exception as err:
            pass