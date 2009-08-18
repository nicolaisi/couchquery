from couchquery import *

def setup_module(module):
    db = Database('http://localhost:5984/couchquery_unittest')
    createdb(db)
    module.db = db

lectroids = [
    {'type':'red-lectroid',   'name':'John Whorfin'},
    {'type':'black-lectroid', 'name':'John Parker'},
    {'type':'red-lectroid',   'name':'John Bigboote'},
    {'type':'red-lectroid',   'name':"John O'Connor"},
    {'type':'red-lectroid',   'name':"John Gomez"},
    {'type':'black-lectroid', 'name':"John Emdall"},
    {'type':'red-lectroid',   'name':"John YaYa"},
    {'type':'red-lectroid',   'name':"John Small Berries"},
]

def test_simple_add():
    for doc in lectroids:
        assert db.create(doc)['ok'] == True

def test_bulk_update():
    alldocs = db.views.all()
    alldocs.species = 'lectroid'
    alldocs.save()
    
def test_bulk_delete():
    alldocs = db.views.all()
    alldocs.delete()

def teardown_module(module):
    deletedb(module.db)