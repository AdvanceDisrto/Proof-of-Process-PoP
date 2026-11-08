import random
import unittest
from model.tessera_g_model import TesseraModel, State

class TesseraTests(unittest.TestCase):
    def test_genesis_accepted(self):
        self.assertEqual(TesseraModel().append(1), State.ACCEPTED)

    def test_locally_refuted(self):
        self.assertEqual(TesseraModel().append(2), State.REFUTED)

    def test_unknown_is_not_accepted(self):
        self.assertEqual(TesseraModel().append(3), State.UNDETERMINED)

    def test_inherited_failure(self):
        m=TesseraModel(); m.append(1); m.append(2, 0)
        self.assertEqual(m.append(1, 1), State.DEPENDENCY_BLOCKED)

    def test_two_parent_join(self):
        m=TesseraModel(); m.append(1); m.append(1, 0)
        self.assertEqual(m.append(1, 0, 1), State.ACCEPTED)

    def test_fail_closed_if_one_parent_refuted(self):
        m=TesseraModel(); m.append(1); m.append(2)
        self.assertEqual(m.append(1,0,1),State.DEPENDENCY_BLOCKED)

    def test_cycle_and_forward_refused(self):
        m=TesseraModel()
        self.assertEqual(m.append(1,0),State.INVALID_TOPOLOGY)
        self.assertEqual(m.append(1,10),State.INVALID_TOPOLOGY)

    def test_duplicate_parent_refused(self):
        m=TesseraModel(); m.append(1)
        self.assertEqual(m.append(1,0,0),State.INVALID_TOPOLOGY)

    def test_full_and_reset(self):
        m=TesseraModel(max_nodes=2); m.append(1); m.append(1)
        with self.assertRaises(OverflowError):m.append(1)
        self.assertTrue(m.overflow_seen)
        m.reset(); self.assertFalse(m.overflow_seen)
        self.assertEqual(m.append(1), State.ACCEPTED)

    def test_reference_trace_matches_rtl_expected(self):
        m=TesseraModel()
        cases=[(1,None,None,1),(1,0,None,1),(2,0,None,2),(1,2,None,3),
            (1,0,1,1),(1,4,2,3),(1,7,None,5),(1,6,None,3),
            (3,None,None,4),(1,8,None,3),(1,0,0,5),(1,0,12,5),
            (0,None,None,4),(2,None,None,2),(1,None,None,1),(1,14,None,1)]
        for verdict,pa,pb,expected in cases:
            self.assertEqual(m.append(verdict,pa,pb),expected)

    def test_randomized_topological_property(self):
        rng=random.Random(20261107)
        for _ in range(60):
            m=TesseraModel()
            for idx in range(16):
                va=rng.choice((1,1,1,2,3))
                pa = rng.randrange(idx) if idx and rng.randrange(2) else None
                pb = rng.randrange(idx) if idx and rng.randrange(3)==0 else None
                result=m.append(va,pa,pb)
                if result == State.ACCEPTED:
                    self.assertEqual(va, 1)
                    self.assertTrue(all(m.nodes[p].effective == State.ACCEPTED for p in (pa,pb) if p is not None))
                if pa is not None and pa==pb:
                    self.assertEqual(result, State.INVALID_TOPOLOGY)

    def test_visualizer_preserves_two_parents(self):
        m=TesseraModel();m.append(1);m.append(1,0);m.append(1,0,1)
        nodes=m.export_visualizer()
        self.assertEqual((nodes[2]['parent_a'], nodes[2]['parent_b']), (0,1))
        self.assertEqual([x['depth'] for x in nodes], [0,1,2])
        self.assertEqual(nodes[2]['effective'], State.ACCEPTED)

    def test_visualizer_single_parent_bridge(self):
        m=TesseraModel();m.append(1);m.append(2,0);m.append(1,1)
        data=m.export_visualizer()
        self.assertEqual([x['effective'] for x in data],[1,2,3])
        self.assertEqual([x['parent_a'] for x in data],[-1,0,1])
        self.assertEqual([x['parent_b'] for x in data],[-1,-1,-1])
        self.assertEqual([x['depth'] for x in data],[0,1,2])

if __name__ == '__main__':unittest.main()
