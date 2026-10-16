"""Production asyncio UDP/TCP forwarding service; no resolver simulation."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import secrets
import struct
import time
import traceback
import dns.asyncquery
import dns.exception
import dns.flags
import dns.message
import dns.opcode
import dns.rcode
import dns.rdatatype
from .cache import Cache,key,normalize
from .config import parse,route

ROOT=Path(__file__).resolve().parents[1]

def identity():
    names=['requirements.txt','requirements-dev.txt','pyproject.toml']+[str(p.relative_to(ROOT)) for p in (ROOT/'dnsrouter').glob('*.py')]
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}


def atomic(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def error_wire(wire,rcode):
    if len(wire)<2:return b''
    ident=struct.unpack('!H',wire[:2])[0]
    return struct.pack('!6H',ident,int(dns.flags.QR)|int(rcode),0,0,0,0)


class UDP(asyncio.DatagramProtocol):
    def __init__(self,server):self.server=server
    def connection_made(self,transport):self.transport=transport
    def datagram_received(self,data,addr):
        self.server.stats['requests']+=1
        if not self.server.admit():
            self.transport.sendto(error_wire(data,dns.rcode.SERVFAIL),addr);return
        async def reply():
            result=await self.server.execute(data,'udp')
            if result and not self.transport.is_closing():self.transport.sendto(result,addr)
        task=asyncio.create_task(reply());self.server.track(task)


class Server:
    def __init__(self,config):
        self.cfg=parse(config);self.cache=Cache(self.cfg['cache_entries'],self.cfg['cache_bytes'])
        self.stats={k:0 for k in ['requests','completed','cancelled','rejected','active','peak_active','malformed','unsupported','upstream_attempts','upstream_timeouts','upstream_errors','upstream_exhausted','tcp_fallbacks','cache_hits','cache_misses','negative_hits','internal_errors','tcp_connections','peak_tcp_connections','tcp_rejected','tcp_protocol_errors']}
        self.routes={r['suffix']:0 for r in self.cfg['routes']}
        self.tasks=set();self.writers=set();self.draining=False;self.started=time.monotonic()
        self.transport=None;self.listener=None

    def track(self,task):self.tasks.add(task);task.add_done_callback(self.tasks.discard)

    def admit(self):
        if self.draining or self.stats['active']>=self.cfg['max_inflight']:
            self.stats['rejected']+=1;return False
        self.stats['active']+=1
        self.stats['peak_active']=max(self.stats['peak_active'],self.stats['active']);return True

    def metrics(self):
        return self.stats | dict(cache_entries=len(self.cache.items),cache_wire_bytes=self.cache.bytes,
                                peak_cache_wire_bytes=self.cache.peak_bytes,cache_evictions=self.cache.evictions,
                                cache_expired=self.cache.expired,routes=dict(self.routes),elapsed_s=time.monotonic()-self.started)

    async def forward(self,q,protocol):
        r=route(self.cfg,q.question[0].name);self.routes[r['suffix']]+=1
        for u in r['upstreams']:
            uq=copy.deepcopy(q);uq.id=secrets.randbits(16);self.stats['upstream_attempts']+=1
            try:
                async with asyncio.timeout(self.cfg['upstream_timeout']):
                    if protocol=='tcp':
                        answer=await dns.asyncquery.tcp(uq,u['host'],port=u['port'],timeout=self.cfg['upstream_timeout'])
                    else:
                        answer=await dns.asyncquery.udp(uq,u['host'],port=u['port'],timeout=self.cfg['upstream_timeout'])
                        if answer.flags & dns.flags.TC:
                            self.stats['tcp_fallbacks']+=1
                            answer=await dns.asyncquery.tcp(uq,u['host'],port=u['port'],timeout=self.cfg['upstream_timeout'])
                if answer.flags & dns.flags.TC:raise dns.exception.DNSException('truncated TCP response')
                if not uq.is_response(answer):raise dns.exception.DNSException('mismatched response')
                answer.id=q.id;answer.question=copy.deepcopy(q.question)
                return answer
            except (TimeoutError,dns.exception.Timeout):self.stats['upstream_timeouts']+=1
            except (OSError,dns.exception.DNSException,ValueError):self.stats['upstream_errors']+=1
        self.stats['upstream_exhausted']+=1
        answer=dns.message.make_response(q);answer.set_rcode(dns.rcode.SERVFAIL);return answer

    async def execute(self,wire,protocol):
        try:
            try:
                if len(wire)>self.cfg['max_query_bytes']:raise ValueError('oversize query')
                q=dns.message.from_wire(wire)
                if q.flags & dns.flags.QR or len(q.question)!=1:raise ValueError('not one query')
            except (dns.exception.DNSException,ValueError):
                self.stats['malformed']+=1;return error_wire(wire,dns.rcode.FORMERR)
            if q.opcode()!=dns.opcode.QUERY or q.had_tsig or q.edns>0 or q.question[0].rdtype in [dns.rdatatype.AXFR,dns.rdatatype.IXFR]:
                self.stats['unsupported']+=1
                answer=dns.message.make_response(q);answer.set_rcode(dns.rcode.NOTIMP)
            else:
                k=key(q);cached=self.cache.get(k,q)
                if cached is not None:
                    answer,kind=cached;self.stats['cache_hits']+=1
                    if kind!='positive':self.stats['negative_hits']+=1
                else:
                    self.stats['cache_misses']+=1
                    answer=await self.forward(q,protocol)
                    life=normalize(answer,self.cfg['ttl_cap'])
                    self.cache.put(k,answer,life)
            limit=65535 if protocol=='tcp' else min(1232,max(512,q.payload if q.edns>=0 else 512))
            return answer.to_wire(max_size=limit,prefer_truncation=True)
        except asyncio.CancelledError:
            self.stats['cancelled']+=1;raise
        except Exception:
            self.stats['internal_errors']+=1;traceback.print_exc()
            return error_wire(wire,dns.rcode.SERVFAIL)
        finally:
            self.stats['active']-=1
            # A cancellation produces no answer and has a separate disposition.
            if not asyncio.current_task().cancelling():self.stats['completed']+=1

    async def tcp(self,reader,writer):
        task=asyncio.current_task();self.track(task)
        if self.draining or len(self.writers)>=self.cfg['max_tcp_connections']:
            self.stats['tcp_rejected']+=1;writer.close();return
        self.writers.add(writer);self.stats['tcp_connections']=len(self.writers)
        self.stats['peak_tcp_connections']=max(self.stats['peak_tcp_connections'],len(self.writers))
        try:
            while not self.draining:
                try:
                    async with asyncio.timeout(self.cfg['tcp_idle_timeout']):
                        size=struct.unpack('!H',await reader.readexactly(2))[0]
                        if size>self.cfg['max_query_bytes'] or size<12:
                            self.stats['tcp_protocol_errors']+=1;break
                        wire=await reader.readexactly(size)
                    self.stats['requests']+=1
                    if self.admit():result=await self.execute(wire,'tcp')
                    else:result=error_wire(wire,dns.rcode.SERVFAIL)
                    writer.write(struct.pack('!H',len(result))+result)
                    await asyncio.wait_for(writer.drain(),self.cfg['tcp_idle_timeout'])
                except (asyncio.IncompleteReadError,TimeoutError,ConnectionError,OSError):break
        finally:
            self.writers.discard(writer);self.stats['tcp_connections']=len(self.writers)
            writer.close()
            try:await asyncio.wait_for(writer.wait_closed(),.2)
            except (TimeoutError,OSError):pass

    async def start(self):
        self.listener=await asyncio.start_server(self.tcp,self.cfg['host'],self.cfg['port'],limit=self.cfg['max_query_bytes']+2,backlog=64)
        self.port=self.listener.sockets[0].getsockname()[1]
        try:self.transport,_=await asyncio.get_running_loop().create_datagram_endpoint(lambda:UDP(self),local_addr=(self.cfg['host'],self.port))
        except BaseException:
            self.listener.close();await self.listener.wait_closed();raise
        return self.port

    async def close(self):
        self.draining=True
        if self.listener:self.listener.close()
        await asyncio.sleep(0)
        if self.tasks:
            _,pending=await asyncio.wait(set(self.tasks),timeout=self.cfg['drain_timeout'])
            for t in pending:t.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
        for w in list(self.writers):w.close()
        if self.transport:self.transport.close()
        if self.listener:await asyncio.wait_for(self.listener.wait_closed(),.5)
