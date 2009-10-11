import os
import urllib
import copy
import types
from urlparse import urlparse

import httplib2

debugging = True

try:
    import simplejson as json
except:
    import json

jheaders = {"content-type":"application/json",
            "accept"      :"application/json"}

design_template = {"_id":"_design/", "language":"javascript"}

class HttpResponse(object):
    pass

class Httplib2Response(HttpResponse):
    def __init__(self, response, content):
        self.body = content
        self._response = response
        self.status = response.status
        self.headers = response

class HttpClient(object):
    pass

def httplib2MethodWrapper(method):
    def m(self, path=None, headers={'content-type':'application/json'}, body=None):
        resp, content = self.request(path, method, headers=headers, body=body)
        return Httplib2Response(resp, content)
    return m
    
class Httplib2Client(HttpClient):
    def __init__(self, uri, cache=None, http_override=None):
        self.uri = uri
        self.parsed = urlparse(uri)
        if not self.uri.endswith('/'):
            self.uri = self.uri + '/'
        
        if http_override is None:
            if '@' in self.uri:
                user, password = self.uri.replace('http://','').split('@')[0].split(':')
                self.uri = 'http://'+self.uri.split('@')[1]
                if cache is None:
                    cache = '.cache'
                self.http = httplib2.Http(cache)
                self.http.add_credentials(user, password)
            else: 
                self.http = httplib2.Http(cache)
        else:
            self.http = http_override
    
    def request(self, path, method, headers, body):
        return self.http.request(self.uri + path, method, headers=headers, body=body, redirections=0)
    
    get = httplib2MethodWrapper("GET")
    put = httplib2MethodWrapper("PUT")
    post = httplib2MethodWrapper("POST")
    delete = httplib2MethodWrapper("DELETE")
    head = httplib2MethodWrapper("HEAD")
        

class RowSet(object):
    def __init__(self, db, rows, offset=None, total_rows=None, parent=None):
        self.__db = db
        self.__rows = rows
        self.__changes = []
        self.__parent = parent
        self.__offset = offset
        object.__setattr__(self, 'total_rows', total_rows)
        
    def raw_rows(self):
        return self.__rows
    
    def keys(self):
        return [x['key'] for x in self.__rows]
    def values(self):
        return [x for x in self]
    def ids(self):
        return [x['id'] for x in self.__rows]
        
    def items(self, key='key', value='value'):
        if value == 'value':
            values = self.values()
        else:
            values = [x[value] for x in self.__rows]
            
        if key == 'value':
            keys = self.values()
        else:
            keys = [x[key] for x in self.__rows]
            
        return map(lambda x, y: (x,y,), keys, values)
        
    @property
    def offset(self):
        if self.__offset is None:
            if self.__parent is not None and self.__parent.offset is not None:
                self.__offset = self.__parent.offset + self.__parent.__rows.index(self.__rows[0])
            else: 
                self.__offset = None
        return self.__offset
    
    def get_offset(self, obj, key='value'):
        if not self.offset:
            raise Exception("offset is not available for this RowSet.")
        return self.offset + [x[key] for x in self.__rows].index(obj)
    
    def __iter__(self):
        for i in range(len(self.__rows)):
            x = self.__rows[i]
            if type(x) is dict and type(x) is not Document and type(x['value']) is dict and x['value'].has_key('_id'):
                doc = Document(x['value'], db=self.__db)
                self.__rows[i]['value'] = doc
                yield doc
            else:
                yield x['value']
    
    def __contains__(self, obj):
        if type(obj) is str:
            return obj in (x['id'] for x in self.__rows)
        else:
            return obj in (x['value'] for x in self.__rows)
    
    def __getitem__(self, i):
        if type(i) is int:
            if i > len(self.__rows):
                raise IndexError("out of range")
            if ( type(self.__rows[i]) is dict ) and (
                 type(self.__rows[i]) is not Document ) and ( 
                 type(self.__rows[i]['value']) is dict ) and ( 
                 self.__rows[i]['value'].has_key('_id') ):
                doc = Document(self.__rows[i]['value'], db=self.__db)
                self.__rows[i]['value'] = doc
                return doc
            else:
                return self.__rows[i]['value']
                        
        else:
            return RowSet(self.__db, [r for r in self.__rows if r['key'] == i], parent=self)
    
    def get(self, i, default=None):
        try:
            return self[i]
        except IndexError:
            return default
        
    def __setattr__(self, name, obj):
        if name.startswith("__") or name.startswith("_"+type(self).__name__.split('.')[-1]+"__"):
            return object.__setattr__(self, name, obj)
        for x in self:
            x[name] = obj
            # batch request
    
    def __len__(self):
        return len(self.__rows)    
        
    def save(self):
        self.__db.update(self)
    
    def delete(self):
        self.__db.delete(self)

# class ViewResult(dict):
#     def __init__(self, result, db):
#         super(ViewResult, self).__init__(result)
#         self.result = result
#         self.rows = RowSet(db, result["rows"])
#     def __len__(self):
#         return len(self.result["rows"])


class ViewException(Exception): pass

class View(object):
    def __init__(self, db, path):
        self.db = db
        self.path = path
    def __call__(self, keys=None, **kwargs):
        # for k, v in kwargs.items():
        #     if type(v) is bool:
        #         kwargs[k] = str(v).lower()
        #     if k in ['key', 'startkey', 'endkey']:
        #         kwargs[k] = json.dumps(v)
        qs = {}
        for k, v in kwargs.items():
            if 'docid' not in k and k != 'stale': qs[k] = json.dumps(v)
            else: qs[k] = v
        
        query_string = urllib.urlencode(qs)
        if len(query_string) is not 0:
            path = self.path + '?' + query_string
        else:
            path = self.path
        
        if not keys:
            response = self.db.http.get(path)
        else:
            response = self.db.http.post(path, body=json.dumps({'keys':keys}))
        
        result = json.loads(response.body)
        if response.status == 200:
            return RowSet(self.db, result['rows'], offset=result.get('offset', None), 
                           total_rows=result.get('total_rows'))
        else:
            raise ViewException(result)

class Design(object):
    def __init__(self, db, _id):
        self.db = db
        self._id = _id
    def __getattr__(self, name):
        if debugging:    
            response = self.db.http.head(self._id+'/_view/'+name+'/')
        if not debugging or response.status == 200:
            setattr(self, name, View(self.db, self._id+'/_view/'+name+'/'))
            return getattr(self, name)
        else:
            raise AttributeError("No view named "+name+". "+response.body)

class TempViewException(Exception): pass

class Views(object):
    def __init__(self, db):
        self.db = db
        self.path = '_design/'
        
    def temp_view(self, map, reduce=None, **kwargs):
        view = {"map":map}
        if type(reduce) is str:
            view['reduce'] = reduce
        body = json.dumps(view)
        if len(kwargs) is 0:
            path = self.db.uri+'_temp_view'
        else:
            for k, v in kwargs.items():
                if type(v) is bool:
                    kwargs[k] = str(v).lower()
                if k in ['key', 'startkey', 'endkey']:
                    kwargs[k] = json.dumps(v)
            query_string = urllib.urlencode(kwargs)
            path = self.path+'_temp_view' + '?' + query_string

        response = self.db.http.post(path, body=body)
        if response.status == 200:
            result = json.loads(response.body)
            return RowSet(self.db, result['rows'], offset=result['offset'], 
                           total_rows=result['total_rows'])
        else:
            raise TempViewException('Status: '+str(response.status)+'\nBody: '+response.body)
    
    def all(self, keys=None, include_docs=True, **kwargs):
        kwargs['include_docs'] = include_docs
        qs = '&'.join([k+'='+json.dumps(v) for k,v in kwargs.items()])
        if keys:
            response = self.db.http.post('_all_docs?' + qs, body=json.dumps({"keys":keys}))
        else:
            response = self.db.http.get('_all_docs?' + qs)
        if response.status == 200:
            result = json.loads(response.body)
            # Normalize alldocs to a standard view result for RowSet
            for row in result['rows']:
                if 'doc' in row:
                    row['rev'] = row['value']['rev']
                    row['value'] = row['doc']
            return RowSet(self.db, result['rows'], offset=result.get('offset', None), 
                          total_rows=result.get('total_rows', None))
        else:
            raise Exception(response.body)
        
    def __getattr__(self, name):
        if debugging:
            response = self.db.http.head(self.path+name+'/')
        if not debugging or response.status == 200:
            setattr(self, name, Design(self.db, '_design/'+name))
            return getattr(self, name)
        else:
            raise AttributeError("No view named "+name)

class CouchDBException(Exception): pass

class CouchDBDocumentConflict(Exception): pass

class CouchDBDocumentDoesNotExist(Exception): pass

def createdb(arg):
    if type(arg) is Database:
        db = arg
    else: db = Database(arg)
    response = db.http.put('')
    assert response.status == 201
    return json.loads(response.body)

def deletedb(arg):
    if type(arg) is Database:
        db = arg
    else: db = Database(arg)
    response = db.http.delete('')
    assert response.status == 200
    return json.loads(response.body)

class Database(object):
    def __init__(self, uri, http=None, http_engine=None, cache=None):
        if not uri.endswith('/'):
            uri += '/'
        self.uri = uri
        
        if type(http) is httplib2.Http:
            self.http = Httplib2Client(uri, http_override=http)
        elif http_engine is None:
            self.http = Httplib2Client(uri, cache)
        else:
            self.http = http
        self.views = Views(self)
        
    def get(self, _id):
        """Get a single document by id from the database."""
        response = self.http.get(_id)
        if response.status == 200:
            obj = dict([(str(k),v,) for k,v in json.loads(response.body).items()])
            return Document(obj, db=self)
        else:
            raise CouchDBDocumentDoesNotExist("No document at id "+_id)
    
    def create(self, doc, all_or_nothing=False):
        """Create a document. Accepts any object that can be converted in to a dict.
        If multiple documents are passed they are handed off to the bulk document handler.
        """        
        if type(doc) not in (dict, Document, list, tuple, types.GeneratorType, RowSet):
            doc = dict(doc)
        
        # Hand off to bulk handler when passing multiple documents    
        if type(doc) in (list, tuple, types.GeneratorType, RowSet):
            return self.bulk(doc, all_or_nothing=all_or_nothing)
            
        response = self.http.post('', body=json.dumps(doc))
        if response.status == 201:
            return json.loads(response.body)
        else:
            raise CouchDBException(response.body)
    
    def update(self, doc, all_or_nothing=False):
        """Update a document. Accepts any object that can be converted in to a dict.
        If multiple documents are passed they are handed off to the bulk document handler.
        """
        if type(doc) not in (dict, Document, list, tuple, types.GeneratorType, RowSet):
            doc = dict(doc)
        
        # Hand off to bulk handler when passing multiple documents    
        if type(doc) in (list, tuple, types.GeneratorType, RowSet):
            return self.bulk(doc, all_or_nothing=all_or_nothing)
        
        response = self.http.put(doc['_id'], body=json.dumps(doc))
        if response.status == 201:
            return json.loads(response.body)
        elif response.status == 413:
            raise CouchDBDocumentConflict(response.body)
        else:
            raise CouchDBException(response.body)
    
    def delete(self, doc, all_or_nothing=False):
        """Delete a document. Accepts any object that can be converted in to a dict.
        Document/s must contain _id and _rev properties.
        If multiple documents are passed they are removed using the bulk document API.
        """
        if type(doc) not in (dict, Document, list, tuple, types.GeneratorType, RowSet):
            doc = dict(doc)
        if type(doc) not in (list, tuple, types.GeneratorType, RowSet):
            response = self.http.delete(doc['_id']+'?rev='+str(doc['_rev']))
        else:
            for d in doc:
                d['_deleted'] = True
            self.bulk(d, all_or_nothing=all_or_nothing)
        
        if response.status == 200:
            return json.loads(response.body)
        else:
            raise CouchDBException("Delete failed "+response.body)
    
    def save(self, doc, all_or_nothing=False):
        if type(doc) not in (dict, Document, list, tuple, types.GeneratorType, RowSet):
            doc = dict(doc)
        
        # Hand off to bulk handler when passing multiple documents    
        if type(doc) in (list, tuple, types.GeneratorType, RowSet):
            return self.bulk(doc, all_or_nothing=all_or_nothing)    
            
        if doc.has_key('_id') :
            return self.update(doc)
        else:
            return self.create(doc)
            
    def bulk(self, docs, all_or_nothing=False):
        body = {'docs':list(docs), 'all_or_nothing':all_or_nothing}
        response = self.http.post('_bulk_docs', body=json.dumps(body))
        if response.status == 201:
            return json.loads(response.body)
        else:
            raise CouchDBException("Bulk update failed "+response.body)

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
            current = self.get(document["_id"])
            rev = current.pop('_rev')
            if current != document:
                document["_rev"] = rev
                return self.save(document)
        except Exception, e: 
            return self.save(document)

Database = Database

def set_global_db(_gdb):
    global global_db
    global_db = _gdb

class Document(dict):
    def __init__(self, *args, **kwargs):
        if 'db' in kwargs:
            object.__setattr__(self, 'db', kwargs.pop('db'))
        super(Document, self).__init__(*args, **kwargs)
    
    __getattr__ = dict.__getitem__
    def __setattr__(self, k, v):
        self[k] = v
    __delattr__ = dict.__delitem__

# from asynchttp import AsyncHTTPConnection
# 
# class CouchAsyncConnection(AsyncHTTPConnection):
#     def __init__(self, url, method, obj, callback):
#         self.method = method
#         self.obj = obj
#         self.callback = callback
#         AsyncHTTPConnection.__init__(
#             self, self.host, self.port
#             )
#         self._url = url
# 
#     def handle_response(self): 
#         print "results %s %d %s" % (
#             self.response.version,
#             self.response.status,
#             self.response.reason
#             )
# 
#     def handle_connect(self):
#         AsyncHTTPConnection.handle_connect(self)
#         self.putrequest("GET", self._url)
#         self.endheaders()
#         self.getresponse()


