from checks import unittest, verify_case

class TestV0315ScheduleFreeze(unittest.TestCase):
    def test_schedule_freeze(self): verify_case(self, __name__.split(".")[-1])
