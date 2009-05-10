import os
import sys
import urllib
import copy
import httplib2

try:
    import simplejson
except:
    import json as simplejson

jheaders = {"content-type":"application/json",
            "accept"      :"application/json"}

design_template = {"_id":"_design/", "language":"javascript"}

class RowsSet(object):
    def __init__(self, db, rows, parent=None):
        self.__db = db
        self.__rows = rows
        self.__changes = []
        self.__parent = parent
    
    def __iter__(self):
        if ( len(self.__rows) is not 0 and type(self.__rows[0]) is dict 
                                   and self.__rows[0].has_key('id') ):
            for x in self.__rows:
                yield CouchDocument(x['value'], db=self.__db)
        else:
            for x in self.__rows:
                yield x['value']
    
    def __getitem__(self, i):
        if type(i) is int:
            return CouchDocument(self.__rows[i]['value'], db=self.__db)
        else:
            return RowsSet(self.__rows[i], parent=self)
        
    def __setattr__(self, name, obj):
        if name.startswith("__") or "_RowsSet__db":
            return object.__setattr__(self, name, obj)
        for x in self.__rows:
            x[name] = obj
            # batch request
    
    def __len__(self):
        return len(self.__rows)    
        
    def save(self, ): pass

class ViewResult(dict):
    def __init__(self, result, view):
        super(ViewResult, self).__init__(result)
        self.result = result
        self.view = view
        self.rows = RowsSet(view.design.views.db, result["rows"])
    def __len__(self):
        return self.result["total_rows"]

class View(object):
    def __init__(self, design, name):
        self.design = design
        self.name = name
        self.uri = self.design.uri+'_view/'+name+'/'
    def __call__(self, async=False, twisted=False, callback=None, **kwargs):
        for k, v in kwargs.items():
            if type(v) is bool:
                kwargs[k] = str(v).lower()
            if k in ['key', 'startkey', 'endkey']:
                kwargs[k] = simplejson.dumps(v)
        query_string = urllib.urlencode(kwargs)
        if len(query_string) is not 0:
            uri = self.uri + '?' + query_string
        else:
            uri = self.uri
        response, content = httplib2.Http().request(uri, "GET", headers=jheaders)
        assert response.status == 200
        response_body = simplejson.loads(content)
        return ViewResult(response_body, self)
        

class Design(object):
    def __init__(self, views, name):
        self.views = views
        self.name = name
        self.uri = self.views.uri+self.name+'/'
    def __getattr__(self, name):
        resp, content = httplib2.Http().request(self.uri+'_view/'+name+'/', 
                                                "HEAD", headers=jheaders)
        if resp.status == 200:
            setattr(self, name, View(self, name))
            return getattr(self, name)
        else:
            print resp.status
            raise AttributeError("No view named "+name+". "+content)

class Views(object):
    def __init__(self, db):
        self.db = db
        self.uri = self.db.uri+'_design/'
    def __getattr__(self, name):
        resp, content = httplib2.Http().request(self.uri+name+'/', "HEAD", headers=jheaders)
        if resp.status == 200:
            setattr(self, name, Design(self, name))
            return getattr(self, name)
        else:
            raise AttributeError("No view named "+name)

class CouchDBException(Exception): pass

class CouchDBDocumentConflict(Exception): pass

class CouchDBDocumentDoesNotExist(Exception): pass

class CouchDatabase(object):
    def __init__(self, uri):
        self.uri = uri
        if not self.uri.endswith('/'):
            self.uri += '/'
        self.views = Views(self)
        
    def get(self, _id):
        resp, content = httplib2.Http().request(self.uri+_id, "GET", headers=jheaders)
        if resp.status == 200:
            obj = dict([(str(k),v,) for k,v in simplejson.loads(content).items()])
            return CouchDocument(obj, db=self)
        else:
            raise CouchDBDocumentDoesNotExist("No document at id "+_id)
    
    def create(self, doc):
        if type(doc) is not dict:
            doc = dict(doc)
        resp, content = httplib2.Http().request(self.uri, "POST", headers=jheaders, body=simplejson.dumps(doc))
        if resp.status == 201:
            return simplejson.loads(content)
        else:
            raise CouchDBException(content)
    
    def update(self, doc):
        if type(doc) is not dict:
            doc = dict(doc)
        resp, content = httplib2.Http().request(self.uri+doc['_id'], "PUT", headers=jheaders, body=simplejson.dumps(doc))
        if resp.status == 201:
            return simplejson.loads(content)
        elif resp.status == 413:
            raise CouchDBDocumentConflict(content)
        else:
            raise CouchDBException(content)
    
    def delete(self, doc):
        if type(doc) is not dict:
            doc = dict(doc)
        resp, content = httplib2.Http().request(
            self.uri+doc['_id']+'?rev='+str(doc['_rev']), 
            "DELETE", headers=jheaders)
        if resp.status == 200:
            return simplejson.loads(content)
        else:
            raise CouchDBException("Delete failed "+content)
    
    def save(self, doc):
        if type(doc) is not dict:
            doc = dict(doc)
        if doc.has_key('_id'):
            return self.update(doc)
        else:
            return self.create(doc)

    def sync_design_doc(self, name, directory):
        document = copy.copy(design_template)
        document['_id'] += name
        d = {}
        for view in os.listdir(directory):
            v = {}
            if os.path.isfile(os.path.join(directory, view, 'map.js')):
                v['map'] = open(os.path.join(directory, view, 'map.js'), 'r').read()
            if os.path.isfile(os.path.join(directory, view, 'reduce.js')):
                v['reduce'] = open(os.path.join(directory, view, 'reduce.js'), 'r').read()
            d[view] = v
            document['views'] = d
        
        try:
            document["_rev"] = self.get(document["_id"])["_rev"]
        except: pass        
        
        return self.save(document)

db = CouchDatabase

def set_global_db(_gdb):
    global global_db
    global_db = _gdb

class CouchDocument(dict):
    def __init__(self, *args, **kwargs):
        if 'db' in kwargs:
            object.__setattr__(self, 'db', kwargs.pop('db'))
        elif hasattr(self, 'db'): pass
        else:
            object.__setattr__(self, 'db', global_db)
        super(CouchDocument, self).__init__(*args, **kwargs)

    # def __getattribute__(self, name):
    #     if name.startswith('__'):
    #         return object.__getattribute__(self, name)
    #     if name in ['save', 'dict', 'db']:
    #         return object.__getattribute__(self, name)
    #     obj = self.__getitem__(name)
    #     if type(obj) is dict:
    #         obj = CouchDocument(obj)
    #         self.__setitem__(name, obj)
    #     return obj    
    
    __getattr__ = dict.__getitem__
    
    __setattr__ = dict.__setitem__    


doc = CouchDocument

from asynchttp import AsyncHTTPConnection

class CouchAsyncConnection(AsyncHTTPConnection):
    def __init__(self, url, method, obj, callback):
        self.method = method
        self.obj = obj
        self.callback = callback
        AsyncHTTPConnection.__init__(
            self, self.host, self.port
            )
        self._url = url

    def handle_response(self): 
        print "results %s %d %s" % (
            self.response.version,
            self.response.status,
            self.response.reason
            )

    def handle_connect(self):
        AsyncHTTPConnection.handle_connect(self)
        self.putrequest("GET", self._url)
        self.endheaders()
        self.getresponse()


