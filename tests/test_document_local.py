import os
import unittest
from couchquery import *
import time

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

    def test_compaction(self):
        # create doc
        info = self.db.create({'revision': 1})
        id_ = info['id']
        rev_1 = info['rev']
        # make changes to get 2nd revision
        doc = self.db.get(id_)
        doc.revision = 2
        self.db.update(doc)
        # make changes to get 3rd revision
        doc = self.db.get(id_)
        doc.revision = 3
        self.db.update(doc)
        # access both revision, yields true
        doc = self.db.get(id_, rev_1)
        self.assertEqual(doc.revision, 1)
        # run compaction
        self.assertEqual(self.db.compaction(), True)
        # ensure compaction process are done
        time.sleep(5)
        # checking availability of previous revisions
        is_compacted = True
        revs = self.db.get_revs(id_)
        for i, rev in enumerate(revs):
            if i > 0:
                is_compacted = False
            print i, rev
        self.assertEqual(is_compacted, True)

    def tearDown(self):
        deletedb(self.db)
        #pass

if __name__ == '__main__':
    unittest.main()
