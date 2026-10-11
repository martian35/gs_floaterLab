import tempfile
import unittest
from pathlib import Path
import torch
from tiered_rgb import FIFORGBTiers


class FIFOTests(unittest.TestCase):
    def test_roundtrip_and_read_does_not_promote(self):
        for gpu, ram in ((0,0),(0,2),(2,0),(2,3)):
            with self.subTest(gpu=gpu,ram=ram), tempfile.TemporaryDirectory() as root:
                tiers = FIFORGBTiers(Path(root)/'images',gpu,ram,device='cpu')
                values = {u: torch.randint(256,(3,7,9),dtype=torch.uint8) for u in range(10)}
                for uid, raw in values.items(): tiers.add(uid,raw)
                order = (list(tiers.gpu),list(tiers.ram),set(tiers.disk))
                for uid in (0,9,2,7,1,5):
                    self.assertTrue(torch.equal(tiers.cpu(uid)['raw'],values[uid]))
                    self.assertTrue(torch.equal(tiers.image(uid),values[uid]/255.0))
                self.assertEqual(order,(list(tiers.gpu),list(tiers.ram),set(tiers.disk)))
                self.assertEqual(list(tiers.gpu),list(range(10-gpu,10)) if gpu else [])
                self.assertEqual(list(tiers.ram),list(range(10-gpu-ram,10-gpu)) if ram else [])
                self.assertEqual(tiers.report()['logical_entries'],10)
                self.assertLessEqual(tiers.report().get('peak_gpu_entries',0),gpu)
                self.assertLessEqual(tiers.report().get('peak_ram_entries',0),ram)
                with self.assertRaises(ValueError): tiers.add(0,values[0])
                with self.assertRaises(KeyError): tiers.image(11)
                tiers.clear_scratch()
                self.assertIsNone(tiers.gpu_scratch)
                self.assertIsNone(tiers.cpu_scratch)

if __name__=='__main__': unittest.main()
