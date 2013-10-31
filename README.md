Couchquery
==========
[![Build Status](https://travis-ci.org/nicolaisi/couchquery.png?branch=master)](https://travis-ci.org/nicolaisi/couchquery)
[![Coverage Status](https://coveralls.io/repos/nicolaisi/couchquery/badge.png?branch=master)](https://coveralls.io/r/nicolaisi/couchquery?branch=master)

Python library for simple and dynamic access to CouchDB. This libary is authored by Mikeal Rogers and currently maintained by Nicholas Tan Jerome.

Further document on this library can be obtained [hier](http://mikeal.github.io/couchquery/)


Getting Started
===============
You will need [CouchDB](http://docs.couchdb.org/en/latest/install/index.html)

After installing CouchDB, start it with
    
    sudo couchdb -b
    
You can now launch http://127.0.0.1:5984/_utils/index.html

Shutdown using
    
    sudo couchdb -d

Installation
============
    
    pip install couchquery
    

How to use
==========
Couchquery is meant to be a simple python libary for CouchDB

Create a `Database` object for any CouchDB database you would like to interact with.

    >>> db = Database('http://localhost:5984/buckaroo')

Create a new document in the database.

    >>> db.create({'type':'red-lectroid','name':'John Whorfin'})
    {u'rev': u'1-4198154595', u'ok': True, u'id': u'c581bbc8fd32f49ecb2f8668ed71fe9b'}

After creating a new document you are given the response dict from couch which includes the id of the document. You can also get documents by id.

    >>> info = db.create({'type':'red-lectroid','name':'John Whorfin'})
    >>> doc = db.get(info['id'])
    >>> type(doc)
    <class 'couchquery.Document'>

`Document` objects are just slightly extended dict objects that provide slightly simpler attribute access.

    >>> doc.name
    "John Worfin"
    >>> doc['name']
    "John Worfin"
    >>> doc.location = "The 8th Dimension"
    >>> doc.has_key('location')
    True
    >>> doc.get('fakeattribute', False)
    False
    
When saving documents you must have the latest revision.

    >>> db.update(doc)
    
Please read on the [document](http://nicolaisi.github.io/couchquery/) for further information.

Changes
=======
0.10.0

+ https support
+ supports credentials usage
+ support url encoding on document id
+ better error message for createdb and deletedb

Tests
=====
If you clone this repository, it is a good practice to run the tests first to make sure that you have a working environment.
You can do this by either:

    py.test tests
    
or

    nosetests



