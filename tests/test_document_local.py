import os
import unittest
from couchquery import *


BASE_URI = 'http://localhost:5984/'
URI = BASE_URI + 'couchquery_unittest'


class DocumentLocal(unittest.TestCase):

    def setUp(self):
        self.db = Database(URI)

        try:
            createdb(self.db)
        except CouchDBException as e:
            pass
        this_dir = os.path.abspath(os.path.dirname(__file__))
        self.db.sync_design_doc('banzai', os.path.join(this_dir, 'views'))

    def test_db_exists(self):
        db_test = Database(URI)
        self.assertEqual(db_test.exists(), True)
        db_test = Database(BASE_URI + 'this_db_should_likely_not_exist')
        self.assertEqual(db_test.exists(), False)

    def test_simple_add(self):
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
        for doc in lectroids:
            self.assertEqual(self.db.create(doc)['ok'], True)

    #def test_bulk_update(self):
    #    alldocs = self.db.views.all()
    #    alldocs.species = 'lectroid'
    #    alldocs.save()

    #def test_views(self):
    #    rows = self.db.views.banzai.byType()
        #assert len(rows) is 8
        #assert type(rows[0]) is Document
        #assert rows.offset is 0

    def tearDown(self):
        deletedb(self.db)
        #pass

if __name__ == '__main__':
    unittest.main()
