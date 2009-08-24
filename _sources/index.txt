.. couchquery documentation master file, created by
   sphinx-quickstart on Mon Aug 17 21:05:22 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

couchquery -- A Python library for CouchDB
======================================

CouchDB is not a relational database. The purpose of couchquery is to provide a simple, flexible and dynamic interface for creating, updating and deleting documents and working with views.

.. toctree::
   :maxdepth: 2

Working with Documents
----------------------

Create a database object for any CouchDB database you would like to interact with.

   >>> db = Database('http://localhost:5984/buckaroo')

Create a new document in the database.

   >>> db.create({'type':'red-lectroid','name':'John Whorfin'})
   {u'rev': u'1-4198154595', u'ok': True, u'id': u'c581bbc8fd32f49ecb2f8668ed71fe9b'}
   
After creating a new document you are given the response dict from couch which includes the id of the document. You can also get documents by id.

   >>> info = db.create({'type':'red-lectroid','name':'John Whorfin'})
   >>> doc = db.get(info['id'])
   >>> type(doc)
   <class 'couchquery.Document'>

Document objects are just slightly extended dict objects that provide slightly simpler attribute access.

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

If you do not have the latest revision you'll get a CouchDBDocumentConflict exception.

   >>> db.update(old_doc)
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
     File "/Users/mikeal/Documents/git/couchquery/couchquery/__init__.py", line 271, in update
       raise CouchDBException(response.body)
   couchquery.CouchDBException: {"error":"conflict","reason":"Document update conflict."}
   
Creating views
--------------

Futon is great, but I like to check my design documents in to version control so that I can push and pull changes to them from different contributors on github.

With couchquery you can create a single directory for each design document where each subdirectory is a view in that design document. Inside the view directories you write a map.js and optional reduce.js file which contains your view functions::

   $ du -a views          
   32      views
   8       views/lectroidByType                                                            
   8       views/lectroidByType/map.js
   8       views/byType
   8       views/byType/map.js
   8       views/byType/reduce.js

You can then "sync" this directory as a design document in your database.::

   db.sync_design_doc('banzai', os.path.join(os.path.dirname(__file__), 'views'))

Now your directory of views is a design document in the database.

Working with views
------------------

The couchquery views API is simple and straight forward provided you already have some understanding of how CouchDB views work.::

   db.views.banzai.lectroidByType(key="red-lectroid")

The view API provides functions for each view that accept keyword arguments which are then converted in to query string arguments to the CouchDB HTTP View API.

These view functions return RowSet objects for each view result. RowSet objects are one of the major highlights of couchquery. A RowSet object represents the **result** of a CouchDB query, it is not an abstraction of the query itself.::

   rows = db.views.banzai.lectroidByType(key="red-lectroid")

Iterating over a RowSet object yields the values from the view result. If the values are documents then it will yield a Document instance for the value.::

   for doc in rows:
       if "lectroid" in doc.type:
           doc.species = 'lectroid'
   rows.save()
   
You can use RowSet.save() to save all changes made to the values in the RowSet provided the values are documents.::

   >>> type(rows[0])
   <class 'couchquery.Document'>
   >>> type(rows['red-lectroid'])
   <class 'couchquery.RowSet'>

You can get a value in the RowSet by position using list style syntax. Dictionary syntax allows you to get new RowSet objects for the selection of rows in the result that matched the given key, this is useful when doing range queries because you can get subsets of the range without making additional queries to the server.::

   >>> rows = db.views.banzai.lectroidByType(startkey=None, endkey={})
   >>> red_lectroids = rows['red-lectroid']
   >>> black_lectroids = rows['black-lectroid']

When applicable, properties like RowSet.offset are preserved and calculated for the new RowSet instance.::
   
   >>> rows.offset
   0
   >>> red_lectroids.offset
   2
   >>> black_lectorids.offset
   0

RowSet objects only assume that values are Documents if they have _id attributes. If not, the value itself is returned by all these value APIs.

RowSet objects also have convenient methods for working with the ids and keys, or more explicitly with values.::

   >>> type(rows.keys())
   <type 'list'>
   >>> type(rows.ids())
   <type 'list'>
   >>> type(rows.values())
   <type 'list'>

Another convenient method is RowSet.items() which returns a list of (key, value) tuples for the keys and values in the view result.::

   for key, value in rows.items():
       if 'lectroid' in key:
           assert 'John' in value.name

The contains operations are also customized. String values are checked against the id's in the result while other objects are checked against the values.

   >>> info = db.create({'type':'black-lectroid', 'name':'John Parker'})
   >>> red_lectroids = db.views.banzai.lectroidByType(key='red-lectroid')
   >>> info['id'] in red_lectroids
   False
   >>> black_lectroids = db.views.banzai.lectroidByType(key='black-lectroid')
   >>> info['id'] in black_lectroids
   True
   >>> db.get(info['id']) in black_lectroids
   True


:mod:`couchquery` --- Simple CouchDB module.
======================================================================

.. module:: couchquery
   :synopsis: Simple CouchDB interface.
.. moduleauthor:: Mikeal Rogers <mikeal.rogers@gmail.com>
.. sectionauthor:: Mikeal Rogers <mikeal.rogers@gmail.com>


