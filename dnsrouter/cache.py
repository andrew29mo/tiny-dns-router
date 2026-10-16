"""Bounded wire-byte LRU; monotonic expiration and conservative RRset aging."""
from collections import OrderedDict
import copy
import math
import time
import dns.flags
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype


def rrsets(message):
    return [rr for section in [message.answer,message.authority,message.additional] for rr in section]


def key(q):
    if (len(q.question)!=1 or q.edns not in [-1,0] or q.options or q.had_tsig
            or q.answer or q.authority or q.additional
            or q.question[0].rdclass!=dns.rdataclass.IN
            or q.question[0].rdtype not in [dns.rdatatype.A,dns.rdatatype.AAAA]):
        return None
    x=q.question[0]
    return (x.name.canonicalize().to_wire(),x.rdtype,x.rdclass,
            q.flags,q.edns,q.ednsflags,q.payload)


def normalize(response, cap):
    """Clamp TTL downward only; return (cache lifetime, kind), or no admission."""
    for rr in rrsets(response):rr.ttl=min(rr.ttl,cap)
    if response.flags & dns.flags.TC or response.rcode() not in [dns.rcode.NOERROR,dns.rcode.NXDOMAIN]:
        return None
    try:chain=response.resolve_chaining()
    except (dns.exception.DNSException,ValueError):return None
    if chain.answer is not None:
        kind='positive'
    else:
        soa=[rr for rr in response.authority if rr.rdtype==dns.rdatatype.SOA
             and chain.canonical_name.is_subdomain(rr.name) and rr.rdclass==dns.rdataclass.IN]
        if not soa:return None
        for rr in soa:rr.ttl=min(rr.ttl,min(x.minimum for x in rr))
        kind='nxdomain' if response.rcode()==dns.rcode.NXDOMAIN else 'nodata'
    sets=rrsets(response)
    ttl=min((rr.ttl for rr in sets),default=0)
    return (ttl,kind) if ttl>0 else None


class Cache:
    def __init__(self,entries,wire_bytes,clock=time.monotonic):
        self.limit=entries;self.byte_limit=wire_bytes;self.clock=clock
        self.items=OrderedDict();self.bytes=0;self.peak_bytes=0;self.evictions=0;self.expired=0

    def remove(self,k,expired=False):
        wire,stamp,ttl,kind=self.items.pop(k);self.bytes-=len(wire)
        if expired:self.expired+=1

    def get(self,k,q):
        if k is None or k not in self.items:return None
        wire,stamp,ttl,kind=self.items[k];age=self.clock()-stamp
        if age>=ttl:self.remove(k,True);return None
        self.items.move_to_end(k)
        r=dns.message.from_wire(wire)
        r.id=q.id;r.question=copy.deepcopy(q.question)
        for rr in rrsets(r):rr.ttl=max(0,rr.ttl-math.ceil(age))
        return r,kind

    def put(self,k,r,lifetime):
        if k is None or lifetime is None or self.limit==0 or self.byte_limit==0:return
        ttl,kind=lifetime;wire=r.to_wire(max_size=65535)
        if len(wire)>self.byte_limit:return
        now=self.clock()
        for old,(_,stamp,life,_) in list(self.items.items()):
            if now-stamp>=life:self.remove(old,True)
        if k in self.items:self.remove(k)
        while self.items and (len(self.items)>=self.limit or self.bytes+len(wire)>self.byte_limit):
            self.remove(next(iter(self.items)));self.evictions+=1
        self.items[k]=(wire,now,ttl,kind);self.bytes+=len(wire)
        self.peak_bytes=max(self.peak_bytes,self.bytes)
