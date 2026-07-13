import unittest,pandas as pd
from v037_support import *
from pipeline import scored_rows
class TestWarmupIsolation(unittest.TestCase):
 def test_warmup_excluded_from_support(self):
  frame=pd.DataFrame({'run_id':['r']*3,'window_index':[1,2,3],'warmup':[True,False,False]});self.assertEqual(len(scored_rows(frame)),2)
