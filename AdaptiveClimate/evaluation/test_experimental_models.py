import copy
import math
import unittest
from experimental_models import Candidate,facade_projection,heat_proxy


def row():
    return dict(room=20,outdoor=10,supply=50,valve=50,ch=True,radiator=.3,
                trv=23,solar=100,wind=4,vent=.5)


class ExperimentalModelsTest(unittest.TestCase):
    def test_command_and_ch_semantics(self):
        self.assertAlmostEqual(heat_proxy(20,50,50,True),.3)
        self.assertEqual(heat_proxy(20,50,50,False),0)
        self.assertEqual(heat_proxy(20,10,50,True),0)

    def test_forecast_is_causal_and_does_not_mutate_inputs(self):
        r=row();before=copy.deepcopy(r);m=Candidate('test',20);m.coefficients=[.02,.1,0]
        first=m.forecast(r,60)
        self.assertEqual(r,before)
        self.assertEqual(first,m.forecast(r,60))
        r['future_room']=1000
        self.assertEqual(first,m.forecast(r,60))
        self.assertTrue(math.isfinite(first))

    def test_fit_deterministic_bounded_and_requires_samples(self):
        samples=[]
        for outside in (0,10,15):
            for heating in (0,.2,.8):
                r=dict(row(),outdoor=outside,radiator=heating)
                samples.append((r,.02*(outside-20)/10+.1*heating+.005))
        a=Candidate('a').fit(samples);b=Candidate('b').fit(samples)
        self.assertEqual(a.coefficients,b.coefficients)
        self.assertAlmostEqual(a.coefficients[0],.02,places=3)
        self.assertAlmostEqual(a.coefficients[1],.1,places=2)
        with self.assertRaises(ValueError):Candidate('empty').fit([])

    def test_missing_trv_not_zero_imputed(self):
        with self.assertRaises(ValueError):
            Candidate('trv',extras=('trv',)).forecast(dict(row(),trv=None),15)

    def test_facade_direction_requires_geometry(self):
        self.assertGreater(facade_projection(300,71.44,30,71.44),0)
        self.assertEqual(facade_projection(300,71.44,30,251.44),0)
        self.assertEqual(facade_projection(300,71.44,-1,71.44),0)
        m=Candidate('facade',extras=('facade',));m.coefficients=[0,0,0,.1]
        with self.assertRaises(ValueError):m.forecast(row(),15)
        self.assertGreater(m.forecast(dict(row(),facade=100),15),20)


if __name__=='__main__':unittest.main()
