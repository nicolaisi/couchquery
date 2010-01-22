import httplib
import urlparse
import urllib
from threading import Thread

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

class Changes(object):
    
    def __init__(self, db, options={}, since_first=False):
        self.uri = getattr(db, 'uri', db)
        if not self.uri.endswith('/'):
            self.uri += '/'
        self.options = options
        self.options['feed'] = 'continuous'
        self.listeners = []
        self.since_first = since_first
        
    def addListener(self, function):
        self.listeners.append(function)
        
    def removeListener(self, function):
        while function in self.listeners:
            self.listeners.remove(function)
            
    def get_update_seq(self):        
        url = urlparse.urlparse(self.uri)
        conn = httplib.HTTPConnection(url.netloc)
        conn.request("GET", url.path)
        resp = conn.getresponse()
        assert resp.status == 200
        return json.loads(resp.read())['update_seq']
            
    def start(self):
        if 'since' not in self.options and not self.since_first:
            self.options['since'] = self.get_update_seq()
        url = urlparse.urlparse(self.uri)
        conn = httplib.HTTPConnection(url.netloc)
        conn.request("GET", url.path+'_changes?'+urllib.urlencode(self.options))
        print url.path+'_changes?'+urllib.urlencode(self.options)
        response = conn.getresponse()
        assert response.status == 200
        self.conn, self.response = conn, response
        self.thread = Thread(target=self._run)
        self.force_stop = False
        getattr(self.thread, 'setDaemon', lambda x: None)(1)
        self.thread.start()
    
    def dispatch(self, obj):
        for listener in self.listeners:
            listener(obj)
    
    def _run(self):
        line = self.response.fp.readline()
        while line and not self.force_stop:
            try:
                obj = json.loads(line)
            except:
                obj = None
            if obj:
                self.dispatch(obj)
            line = self.response.fp.readline()

if __name__ == "__main__":
    changes = Changes('http://localhost:5984/testdb')
    def printLine(obj):
        print json.dumps(obj)
    changes.addListener(printLine)
    changes.start()
    from time import sleep
    try:
        while 1:
            sleep(1)
    except KeyboardInterrupt:
        pass
    
