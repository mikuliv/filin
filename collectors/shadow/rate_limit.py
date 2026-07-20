from __future__ import annotations
class TokenBucket:
    def __init__(self,rate,capacity=None): self.rate=float(rate); self.capacity=float(capacity or rate); self.tokens=self.capacity; self.last=0.0
    def allow(self,now):
        elapsed=max(0.0,now-self.last); self.last=now; self.tokens=min(self.capacity,self.tokens+elapsed*self.rate)
        if self.tokens>=1: self.tokens-=1; return True
        return False
