"""Additional native-D timing absent from its historical optimizer-only field."""
from collections import Counter
from functools import wraps
import time


def install():
    import torch
    import bounded_rgb_pool
    import bounded_cached_rgb
    from online_mapper_runtime import OnlineMapperRuntime
    counters=Counter()
    counters.stream_start = counters.stream_end = None
    def wrap(cls,name,label):
        original=getattr(cls,name)
        @wraps(original)
        def measured(self,*args,**kwargs):
            torch.cuda.synchronize()
            started=time.perf_counter()
            if label=='image_admission_seconds' and counters.stream_start is None:
                counters.stream_start=started
            try: return original(self,*args,**kwargs)
            finally:
                torch.cuda.synchronize()
                counters[label]+=time.perf_counter()-started
        setattr(cls,name,measured)
    wrap(bounded_rgb_pool.BoundedRGBStore,'append_rgb','image_admission_seconds')
    wrap(OnlineMapperRuntime,'dispatch','packet_dispatch_seconds')
    wrap(bounded_cached_rgb.BoundedRGBController,'compact_native_payloads','image_adoption_seconds')
    from online_photometric import OnlinePhotometricTrainer
    original_step=OnlinePhotometricTrainer.step
    @wraps(original_step)
    def measured_step(self,*args,**kwargs):
        before=self.photometric_steps
        try: return original_step(self,*args,**kwargs)
        finally:
            # The existing trainer already synchronizes its stream before return.
            if self.photometric_steps>before: counters.stream_end=time.perf_counter()
    OnlinePhotometricTrainer.step=measured_step
    return counters
