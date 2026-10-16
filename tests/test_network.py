import asyncio
import json
import socket
import struct
import unittest
import dns.asyncquery
import dns.flags
import dns.message
import dns.rcode
from dnsrouter.service import Server,identity
from tools.upstream import ReferenceServer
from support import config,query,proxy_process


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):self.resources=[]
    async def asyncTearDown(self):
        for r in reversed(self.resources):await r.close()
    async def peer(self,**kw):
        p=ReferenceServer(**kw);await p.start();self.resources.append(p);return p
    async def router(self,cfg):
        s=Server(cfg);await s.start();self.resources.append(s);return s
    async def test_real_udp_tcp_a_aaaa_and_suffix(self):
        a=await self.peer(marker=10);b=await self.peer(marker=20)
        routes=[dict(suffix=s,upstreams=[dict(host='127.0.0.1',port=p.port)]) for s,p in [('.',a),('lab.test.',b)]]
        s=await self.router(config(a.port,routes=routes))
        for tcp in [False,True]:
            for name,marker in [('www.lab.test.',20),('badlab.test.',10)]:
                for typ in ['A','AAAA']:
                    r=await query(s.port,name,typ,tcp=tcp)
                    self.assertEqual(r.answer[0][0].to_text(),f'192.0.2.{marker}' if typ=='A' else f'2001:db8::{marker}')
        self.assertEqual(s.stats['internal_errors'],0)
    async def test_live_ttl_expiry_negative_and_uncacheable(self):
        p=await self.peer();s=await self.router(config(p.port,ttl_cap=1))
        a=await query(s.port);b=await query(s.port)
        self.assertLessEqual(b.answer[0].ttl,a.answer[0].ttl);self.assertEqual(p.counts['udp'],1)
        await asyncio.sleep(1.02);await query(s.port);self.assertEqual(p.counts['udp'],2)
        for prefix,rcode in [('nx',dns.rcode.NXDOMAIN),('nodata',dns.rcode.NOERROR)]:
            r=await query(s.port,prefix+'.test.');r2=await query(s.port,prefix+'.test.')
            self.assertEqual(r.rcode(),rcode);self.assertEqual(r2.rcode(),rcode)
            self.assertLessEqual(r2.authority[0].ttl,1)
        self.assertEqual(s.stats['negative_hits'],2)
        for name in ['zero.test.','nx.nosoa.test.','servfail.test.']:
            before=p.counts['udp'];await query(s.port,name);await query(s.port,name)
            self.assertEqual(p.counts['udp']-before,2)
    async def test_timeout_failover_same_suffix_udp_and_tcp(self):
        dead=await self.peer(drop=True);good=await self.peer(marker=30)
        routes=[dict(suffix='.',upstreams=[dict(host='127.0.0.1',port=p.port) for p in [dead,good]])]
        s=await self.router(config(good.port,routes=routes,cache_entries=0))
        for tcp in [False,True]:
            r=await query(s.port,tcp=tcp);self.assertEqual(r.answer[0][0].to_text(),'192.0.2.30')
        self.assertEqual(s.stats['upstream_timeouts'],2);self.assertEqual(s.stats['upstream_attempts'],4)
    async def test_all_timeouts_servfail_and_no_negative_cache(self):
        p=await self.peer(drop=True);s=await self.router(config(p.port))
        for _ in range(2):self.assertEqual((await query(s.port)).rcode(),dns.rcode.SERVFAIL)
        self.assertEqual(s.stats['cache_hits'],0);self.assertEqual(s.stats['upstream_exhausted'],2)
    async def test_bad_id_is_not_cached_and_fails_over(self):
        bad=await self.peer(bad_id=True);good=await self.peer()
        s=await self.router(config(good.port,routes=[dict(suffix='.',upstreams=[dict(host='127.0.0.1',port=p.port) for p in [bad,good]])]))
        self.assertEqual((await query(s.port)).answer[0][0].to_text(),'192.0.2.10')
        self.assertEqual(s.stats['upstream_errors'],1)
    async def test_udp_tc_fallback_and_client_truncation(self):
        p=await self.peer(truncate=True);s=await self.router(config(p.port))
        r=await query(s.port);self.assertFalse(r.flags & dns.flags.TC)
        self.assertEqual(p.counts,dict(udp=1,tcp=1));self.assertEqual(s.stats['tcp_fallbacks'],1)
        r=await query(s.port,'large.test.','TXT');self.assertTrue(r.flags & dns.flags.TC)
        r=await query(s.port,'large.test.','TXT',tcp=True);self.assertFalse(r.flags & dns.flags.TC);self.assertEqual(len(r.answer),12)
    async def test_overload_is_bounded_and_recovers(self):
        p=await self.peer(delay=.04);s=await self.router(config(p.port,max_inflight=1,upstream_timeout=.2))
        tasks=[asyncio.create_task(query(s.port,f'{i}.test.')) for i in range(12)]
        results=await asyncio.gather(*tasks)
        self.assertEqual(sum(r.rcode()==dns.rcode.SERVFAIL for r in results),11)
        self.assertEqual(s.stats['peak_active'],1);self.assertEqual(s.stats['rejected'],11)
        self.assertEqual((await query(s.port,'recovered.test.')).rcode(),dns.rcode.NOERROR)
    async def test_tcp_pipelined_order_fragmentation_and_idle_close(self):
        p=await self.peer();s=await self.router(config(p.port))
        reader,writer=await asyncio.open_connection('127.0.0.1',s.port)
        qs=[dns.message.make_query(n,'A') for n in ['a.test.','b.test.']]
        data=b''.join(struct.pack('!H',len(q.to_wire()))+q.to_wire() for q in qs)
        for offset in range(0,len(data),3):writer.write(data[offset:offset+3]);await writer.drain()
        for q in qs:
            n=struct.unpack('!H',await reader.readexactly(2))[0];r=dns.message.from_wire(await reader.readexactly(n));self.assertTrue(q.is_response(r))
        self.assertEqual(await asyncio.wait_for(reader.read(1),1),b'')
        writer.close();await writer.wait_closed()
    async def test_process_bootstrap_identity_shutdown_and_metrics(self):
        p=await self.peer();proc=await asyncio.to_thread(proxy_process,config(p.port))
        try:
            self.assertEqual(proc.ready['source_files'],identity())
            self.assertEqual((await query(proc.port)).answer[0][0].to_text(),'192.0.2.10')
        finally:await asyncio.to_thread(proc.close)
        m=proc.metrics;self.assertEqual(m['internal_errors'],0)
        self.assertEqual(m['requests'],m['completed']+m['cancelled']+m['rejected']+m['active'])
        self.assertEqual(m['active'],0)
    async def test_graceful_and_forced_shutdown_ledger(self):
        p=await self.peer(delay=.04);s=await self.router(config(p.port,upstream_timeout=.5,drain_timeout=.2))
        task=asyncio.create_task(query(s.port));await asyncio.sleep(.01);await s.close()
        self.assertEqual((await task).rcode(),0);self.assertEqual(s.stats['completed'],1);self.assertEqual(s.stats['cancelled'],0)
        p2=await self.peer(drop=True);s2=await self.router(config(p2.port,upstream_timeout=.5,drain_timeout=.02))
        q=dns.message.make_query('www.test.','A')
        task=asyncio.create_task(dns.asyncquery.udp(q,'127.0.0.1',port=s2.port,timeout=.2))
        await asyncio.sleep(.01);await s2.close()
        with self.assertRaises(dns.exception.Timeout):await task
        self.assertEqual(s2.stats['cancelled'],1);self.assertEqual(s2.stats['active'],0)
        self.assertEqual(s2.stats['requests'],s2.stats['completed']+s2.stats['cancelled']+s2.stats['rejected'])
    async def test_malformed_udp_and_oversized_tcp_do_not_kill_service(self):
        p=await self.peer();s=await self.router(config(p.port))
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.setblocking(False)
        try:
            await asyncio.get_running_loop().sock_sendto(sock,b'\x12\x34garbage',('127.0.0.1',s.port))
            data,_=await asyncio.wait_for(asyncio.get_running_loop().sock_recvfrom(sock,512),1)
            self.assertEqual(dns.message.from_wire(data).rcode(),dns.rcode.FORMERR)
        finally:sock.close()
        reader,writer=await asyncio.open_connection('127.0.0.1',s.port)
        writer.write(struct.pack('!H',5000));await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(1),1),b'')
        writer.close();await writer.wait_closed()
        self.assertEqual((await query(s.port)).rcode(),0)
        self.assertEqual(s.stats['malformed'],1);self.assertEqual(s.stats['tcp_protocol_errors'],1)
    async def test_live_eviction_and_tcp_connection_bound(self):
        p=await self.peer();s=await self.router(config(p.port,cache_entries=1,cache_bytes=256,max_tcp_connections=1))
        for name in ['one.test.','two.test.','one.test.']:await query(s.port,name)
        self.assertEqual(p.counts['udp'],3);self.assertEqual(s.cache.evictions,2);self.assertLessEqual(s.cache.bytes,256)
        reader,writer=await asyncio.open_connection('127.0.0.1',s.port)
        await asyncio.sleep(.01)
        r2,w2=await asyncio.open_connection('127.0.0.1',s.port)
        self.assertEqual(await asyncio.wait_for(r2.read(1),1),b'')
        w2.close();await w2.wait_closed();writer.close();await writer.wait_closed()
        self.assertEqual(s.stats['peak_tcp_connections'],1);self.assertEqual(s.stats['tcp_rejected'],1)
    async def test_idle_tcp_cannot_extend_shutdown_deadline(self):
        p=await self.peer();s=await self.router(config(p.port,tcp_idle_timeout=2.,drain_timeout=.02))
        reader,writer=await asyncio.open_connection('127.0.0.1',s.port);await asyncio.sleep(.01)
        await asyncio.wait_for(s.close(),.3)
        self.assertEqual(await asyncio.wait_for(reader.read(1),.2),b'')
        self.assertEqual(s.stats['tcp_connections'],0)
        writer.close();await writer.wait_closed()
    async def test_live_negative_soa_minimum_is_enforced(self):
        p=await self.peer();s=await self.router(config(p.port))
        for name in ['nx.test.','nodata.test.']:
            r=await query(s.port,name);self.assertEqual(r.authority[0].ttl,3)
            r2=await query(s.port,name);self.assertLessEqual(r2.authority[0].ttl,3)
        self.assertEqual(p.counts['udp'],2)
