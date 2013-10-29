#!/usr/bin/env python
import sys, os.path
mydir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(mydir, "..")))
from couchquery import shelve
import couchquery
import unittest
import pickle

URI = 'https://couchquery.iriscouch.com/shelve'

class TestCouchShelve(unittest.TestCase):

    def setUp(self):
        # Make sure we start with a clean-slate
        db = couchquery.Database(URI)
        response = db.http.get('')
        if response.status == 200:
            couchquery.deletedb(db)

    def tearDown(self):
        # Make sure we leave with a clean-slate
        db = couchquery.Database(URI)
        response = db.http.get('')
        if response.status == 200:
            couchquery.deletedb(db)

    def test_simple_set_get(self):
        d = shelve.open(URI)
        d['item1'] = []
        d.close()

        d = shelve.open(URI)
        self.assertEqual(d['item1'], [])
        d.close()

        # Make sure the data actually ended up in the database
        db = couchquery.Database(URI)
        doc = db.get('item1')
        value = pickle.loads(str(doc.value))
        self.assertEqual(value, [])


    def test_writeback_behavior(self):
        # First prove that we need writeback to handle mutables
        d = shelve.open(URI)
        d['item1'] = []
        d['item1'].append(1)
        d.close()

        d = shelve.open(URI)
        self.assertEqual(d['item1'], [])
        d.close()

        # Now prove that writeback works
        d = shelve.open(URI, writeback=True)
        d['item1'] = []
        d['item1'].append(1)
        d.close()

        d = shelve.open(URI)
        self.assertEqual(d['item1'], [1])
        d.close()

        # Now prove that sync works
        d = shelve.open(URI, writeback=True)
        d['item2'] = []
        d['item2'].append(1)
        d.sync()
        self.assertEqual(d._cache, {})

        d2 = shelve.open(URI, writeback=True)
        self.assertEqual(d2['item2'], [1])
        d2.close()
        d.close()
    
    
    def test_other_dict_funcs(self):
        EXPECTED_ITEMS = set([('item1', 1), ('item2', 2), ('item3', 3)]) 
        d = shelve.open(URI)
        for key, value in EXPECTED_ITEMS:
            d[key] = value 
        d.close()
    
        d = shelve.open(URI)
        
        EXPECTED_KEYS = set(['item1', 'item2', 'item3']) 
        FOUND_KEYS = set(d.keys())
        self.assert_(len(EXPECTED_KEYS ^ FOUND_KEYS) == 0)
    
        EXPECTED_VALUES = set([1, 2, 3]) 
        FOUND_VALUES = set(d.values())
        self.assert_(len(EXPECTED_VALUES ^ FOUND_VALUES) == 0)
    
    
        FOUND_ITEMS = set(d.items())
        self.assert_(len(EXPECTED_ITEMS ^ FOUND_ITEMS) == 0)
    
    
        items = []
        generator = d.iteritems()
        try:
            while True:
                items.append(generator.next())
        except StopIteration:
            pass
        FOUND_ITEMS = set(items)
        self.assert_(len(EXPECTED_ITEMS ^ FOUND_ITEMS) == 0)
    

    def test_confict_behavior(self):
        # First prove that we will silently override conflicts
        d = shelve.open(URI)
        d['item1'] = []

        db = couchquery.Database(URI)
        doc = db.get('item1')
        doc.value = pickle.dumps("NotAList")
        db.save(doc)

        d['item1'] = [1]
        self.assertEqual(d['item1'], [1])

        d.close()

if __name__ == '__main__':
    unittest.main()

