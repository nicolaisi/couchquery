import os
import sys
import urllib
import copy
import types
from urlparse import urlparse

import httplib2

__version__ = '0.10.1'

try:
    import jsonlib2 as json
except:
    try:
        import yajl as json
    except:
        try:
            import simplejson as json
        except:
            import json

JSON_HEADERS = {"content-type": "application/json",
                "accept": "application/json"}

design_template = {"_id": "_design/"}

content_type_table = {'js': 'application/x-javascript',
                      'html': 'text/html; charset=utf-8',
                      'fallback': 'text/plain; charset=utf-8',
                      'ogg': 'application/ogg',
                      'xhtml': 'text/html; charset=utf-8',
                      'rm': 'audio/vnd.rn-realaudio',
                      'swf': 'application/x-shockwave-flash',
                      'mp3': 'audio/mpeg',
                      'wma': 'audio/x-ms-wma',
                      'ra': 'audio/vnd.rn-realaudio',
                      'wav': 'audio/x-wav',
                      'gif': 'image/gif',
                      'jpeg': 'image/jpeg',
                      'jpg': 'image/jpeg',
                      'png': 'image/png',
                      'tiff': 'image/tiff',
                      'css': 'text/css; charset=utf-8',
                      'mpeg': 'video/mpeg',
                      'mp4': 'video/mp4',
                      'qt': 'video/quicktime',
                      'mov': 'video/quicktime',
                      'wmv': 'video/x-ms-wmv',
                      'atom': 'application/atom+xml; charset=utf-8',
                      'xslt': 'application/xslt+xml',
                      'svg': 'image/svg+xml',
                      'mathml': 'application/mathml+xml',
                      'rss': 'application/rss+xml; charset=utf-8',
                      'ics': 'text/calendar; charset=utf-8'}


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
    def m(self, path, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = JSON_HEADERS
        resp, content = self.request(path, method, **kwargs)
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
                protocol = 'https://' if 'https' in self.uri else 'http://'
                cleaned_uri = self.uri.replace(protocol, '')
                user, password = cleaned_uri.split('@')[0].split(':')
                self.uri = protocol+self.uri.split('@')[1]
                if cache is None:
                    cache = '.cache'
                #path = os.path.dirname(os.path.abspath(__file__))+
                #"contrib/DigiCertHighAssuranceEVRootCA.pem"
                self.http = httplib2.Http(
                    cache,
                    disable_ssl_certificate_validation=True)
                self.http.add_credentials(user, password)
            else:
                self.http = httplib2.Http(cache)
        else:
            self.http = http_override

    def request(self, path, method, headers, body=None):
        return self.http.request(self.uri + path,
                                 method,
                                 headers=headers,
                                 body=body,
                                 redirections=0)

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
        return list(self)

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

        return zip(keys, values)

    @property
    def offset(self):
        if self.__offset is None:
            if self.__parent is not None and self.__parent.offset is not None:
                self.__offset = (self.__parent.offset +
                                 self.__parent.__rows.index(self.__rows[0]))
            else:
                self.__offset = None
        return self.__offset

    def get_offset(self, obj, key='value'):
        if not self.offset:
            raise Exception("offset is not available for this RowSet.")
        return self.offset + [x[key] for x in self.__rows].index(obj)

    def __iter__(self):
        for i in xrange(len(self.__rows)):
            x = self.__rows[i]
            if (type(x) is dict and
                    type(x['value']) is dict and
                    '_id' in x['value']):
                doc = Document(x['value'], db=self.__db)
                self.__rows[i]['value'] = doc
                yield doc
            else:
                yield x['value']

    def __contains__(self, obj):
        if isinstance(obj, basestring):
            return obj in (x['id'] for x in self.__rows)
        else:
            return obj in (x['value'] for x in self.__rows)

    def __getitem__(self, i):
        if type(i) is int:
            if i > len(self.__rows):
                raise IndexError("out of range")
            if (type(self.__rows[i]) is dict and
                    type(self.__rows[i]) is not Document and
                    type(self.__rows[i]['value']) is dict and
                    '_id' in self.__rows[i]['value']):
                doc = Document(self.__rows[i]['value'],
                               db=self.__db)
                self.__rows[i]['value'] = doc
                return doc
            else:
                return self.__rows[i]['value']

        else:
            return RowSet(self.__db,
                          [r for r in self.__rows if r['key'] == i],
                          parent=self)

    def get(self, i, default=None):
        try:
            return self[i]
        except IndexError:
            return default

    def __setattr__(self, name, obj):
        if (name.startswith("__") or
            name.startswith("_" +
                            type(self).__name__.split('.')[-1] +
                            "__")):
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


class ViewException(Exception):
    pass


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
        for k, v in kwargs.iteritems():
            if 'docid' not in k and k != 'stale':
                qs[k] = json.dumps(v)
            else:
                qs[k] = v

        query_string = urllib.urlencode(qs)
        if len(query_string) is not 0:
            path = self.path + '?' + query_string
        else:
            path = self.path

        if not keys:
            response = self.db.http.get(path)
        else:
            response = self.db.http.post(path, body=json.dumps({'keys': keys}))

        result = json.loads(response.body)
        if response.status == 200:
            return RowSet(self.db,
                          result['rows'],
                          offset=result.get('offset', None),
                          total_rows=result.get('total_rows'))
        else:
            raise ViewException(result)


class Design(object):
    def __init__(self, db, _id):
        self.db = db
        self._id = _id

    def __getattr__(self, name):
        response = self.db.http.head(self._id+name+'/')
        if response.status == 200 or response.status == 304:
            setattr(self, name, View(self.db, self._id+'/_view/'+name+'/'))
            return getattr(self, name)
        else:
            raise AttributeError("No view named "+name+". "+str(response.status))


class TempViewException(Exception):
    pass


class Views(object):
    def __init__(self, db):
        self.db = db
        self.path = '_design/'

    def temp_view(self, map_, reduce_=None, language='javascript', **kwargs):
        view = {"map": map_, "language": language}
        if isinstance(reduce_, basestring):
            view['reduce'] = reduce_
        body = json.dumps(view)
        if not kwargs:
            path = self.db.uri+'_temp_view'
        else:
            for k, v in kwargs.iteritems():
                if type(v) is bool:
                    kwargs[k] = str(v).lower()
                if k in ['key', 'startkey', 'endkey']:
                    kwargs[k] = json.dumps(v)
            query_string = urllib.urlencode(kwargs)
            path = self.path+'_temp_view' + '?' + query_string

        response = self.db.http.post(path, body=body)
        if response.status == 200:
            result = json.loads(response.body)
            return RowSet(self.db,
                          result['rows'],
                          offset=result['offset'],
                          total_rows=result['total_rows'])
        else:
            raise TempViewException('Status: ' +
                                    str(response.status) +
                                    '\nBody: ' +
                                    response.body)

    def all(self, keys=None, include_docs=True, **kwargs):
        kwargs['include_docs'] = include_docs
        qs = '&'.join(k+'='+json.dumps(v) for k, v in kwargs.iteritems())
        if keys:
            response = self.db.http.post(
                '_all_docs?' + qs, body=json.dumps({"keys": keys}))
        else:
            response = self.db.http.get('_all_docs?' + qs)
        if response.status == 200:
            result = json.loads(response.body)
            # Normalize alldocs to a standard view result for RowSet
            for row in result['rows']:
                if 'doc' in row:
                    row['rev'] = row['value']['rev']
                    row['value'] = row['doc']
            return RowSet(self.db,
                          result['rows'],
                          offset=result.get('offset', None),
                          total_rows=result.get('total_rows', None))
        else:
            raise Exception(response.body)

    def __getattr__(self, name):
        response = self.db.http.head(self.path+name+'/')
        if response.status == 200 or response.status == 304:
            setattr(self, name, Design(self.db, '_design/'+name))
            return getattr(self, name)
        else:
            raise AttributeError("No view named "+name + " "+str(response.status))


class CouchDBException(Exception):
    pass


class CouchDBDocumentConflict(Exception):
    pass


class CouchDBDocumentDoesNotExist(Exception):
    pass


def createdb(arg):
    if type(arg) is Database:
        db = arg
    else:
        db = Database(arg)
    response = db.http.put('')
    if response.status is not 201:
        raise CouchDBException(response.body)
    return json.loads(response.body)


def deletedb(arg):
    if type(arg) is Database:
        db = arg
    else:
        db = Database(arg)
    response = db.http.delete('')
    if response.status != 200:
        raise CouchDBException(response.body)
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

    def get(self, id_, rev=None):
        """Get a single document by id and
        (optionally) revision from the database."""
        id_ = urllib.quote(id_)
        if rev is None:
            response = self.http.get(id_)
        else:
            response = self.http.get(id_+"?rev="+rev)
        if response.status == 200:
            obj = dict((str(k), v)
                       for k, v in json.loads(response.body).iteritems())
            return Document(obj, db=self)
        else:
            raise CouchDBDocumentDoesNotExist("No document at id "+id_)

    def get_revs(self, id_, fetch=False):
        """Get all revisions of a single document from the database.
        Returns a generator for the revision names or the actual documents,
        depending on whether fetch=True is given (defaults to False).
        """
        response = self.http.get(id_ + "?revs_info=true")
        for rev in json.loads(response.body)["_revs_info"]:
            if rev["status"] != "available":
                continue
            if fetch:
                yield self.get(id_, rev=rev["rev"])
            else:
                yield rev["rev"]

    def compaction(self):
        """Compact database [http://wiki.apache.org/couchdb/Compaction]"""
        response = self.http.post("_compact")
        if response.status == 404:
            return False
        return True

    def all_ids(self):
        """List all documents ids in the database."""
        response = self.http.get("_all_docs")
        obj = dict((str(k), v)
                   for k, v in json.loads(response.body).iteritems())
        ids = []
        for row in obj["rows"]:
            ids.append(str(row["id"]))
        return tuple(ids)

    def exists(self):
        response = self.http.get('')
        if response.status == 404:
            return False
        return True

    def create(self, doc, all_or_nothing=False):
        """Create a document. Accepts any object that can be
        converted in to a dict. If multiple documents are passed
        they are handed off to the bulk document handler.
        """
        if type(doc) not in (dict,
                             Document,
                             list,
                             tuple,
                             types.GeneratorType,
                             RowSet):
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
        """Update a document. Accepts any object that can be
        converted in to a dict. If multiple documents are passed
        they are handed off to the bulk document handler.
        """
        if type(doc) not in (dict,
                             Document,
                             list,
                             tuple,
                             types.GeneratorType,
                             RowSet):
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
        """Delete a document. Accepts any object that can be
        converted in to a dict. Document/s must contain _id
        and _rev properties. If multiple documents are passed
        they are removed using the bulk document API.
        """
        if type(doc) not in (dict,
                             Document,
                             list,
                             tuple,
                             types.GeneratorType,
                             RowSet):
            doc = dict(doc)
        if type(doc) not in (list, tuple, types.GeneratorType, RowSet):
            response = self.http.delete(doc['_id']+'?rev='+str(doc['_rev']))
        else:
            for d in doc:
                d['_deleted'] = True
            self.bulk([doc], all_or_nothing=all_or_nothing)

        if response.status == 200:
            return json.loads(response.body)
        else:
            raise CouchDBException("Delete failed "+response.body)

    def save(self, doc, all_or_nothing=False):
        if type(doc) not in (dict,
                             Document,
                             list,
                             tuple,
                             types.GeneratorType,
                             RowSet):
            doc = dict(doc)

        # Hand off to bulk handler when passing multiple documents
        if type(doc) in (list, tuple, types.GeneratorType, RowSet):
            return self.bulk(doc, all_or_nothing=all_or_nothing)

        if '_id' in doc:
            return self.update(doc)
        else:
            return self.create(doc)

    def bulk(self, docs, all_or_nothing=False):
        body = {'docs': list(docs), 'all_or_nothing': all_or_nothing}
        response = self.http.post('_bulk_docs', body=json.dumps(body))
        if response.status == 201:
            return json.loads(response.body)
        else:
            raise CouchDBException("Bulk update failed "+response.body)

    def add_attachments(self, doc, f, name=None, content_type=None, rev=None):
        if isinstance(doc, basestring):
            id_ = doc
        else:
            id_ = doc["_id"]
        if isinstance(f, basestring):
            assert os.path.isfile(f)
            body = open(f, 'r').read()
            if content_type is None:
                content_type = content_type_table[f.split('.')[-1]]
            name = os.path.split(f)[-1]
        else:
            body = f
            if content_type is None:
                raise Exception("Cannot send a string body"
                                " without a content-type.")
            if name is None:
                raise Exception("Cannot send a string body"
                                " with a name.")
        if rev:
            path = id_+'/'+name+'?rev='+rev
        else:
            path = id_+'/'+name

        response = self.http.put(
            path, body=body, headers={'content-type': content_type})
        assert response.status == 201
        return json.loads(response.body)

    def sync_design_doc(self, name, directory, language='javascript'):
        # TODO support views in python
        document = copy.copy(design_template)
        document['language'] = language
        document['_id'] += name
        d = {}

        ext = {'javascript': 'js', 'python': 'py'}[language]

        for view in os.listdir(directory):
            v = {}
            if view.startswith('.'):
                continue
            if os.path.isfile(os.path.join(directory, view, 'map.'+ext)):
                v['map'] = open(
                    os.path.join(directory, view, 'map.'+ext), 'r').read()
            if os.path.isfile(os.path.join(directory, view, 'reduce.'+ext)):
                v['reduce'] = open(
                    os.path.join(directory, view, 'reduce.'+ext), 'r').read()
            d[view.split('.')[0]] = v
            document['views'] = d
        try:
            current = self.get(document["_id"])
            rev = current.pop('_rev')
            if current != document:
                document["_rev"] = rev
                info = self.save(document)
            else:
                info = {'id': current['_id'], 'rev': rev}
        except Exception, e:
            info = self.save(document)

        rev = info['rev']
        if os.path.isdir(os.path.join(directory, 'attachments')):
            for f in [os.path.join(directory, 'attachments', f) for f in os.listdir(os.path.join(directory, 'attachments'))]:
                rev = self.add_attachments('_design/'+name, f, rev=rev)['rev']
        return info


class Document(dict):
    def __init__(self, *args, **kwargs):
        if 'db' in kwargs:
            object.__setattr__(self, 'db', kwargs.pop('db'))
        super(Document, self).__init__(*args, **kwargs)

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
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

