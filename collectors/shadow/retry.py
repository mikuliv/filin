from __future__ import annotations
import random

def backoff_ms(attempt,initial=100,maximum=5000,jitter=.2,seed=314):
    base=min(maximum,initial*(2**attempt)); return int(base*(1+random.Random(seed+attempt).uniform(-jitter,jitter)))
