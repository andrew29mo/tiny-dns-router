"""Independent controlled UDP/TCP DNS peer for actual socket tests/measurements."""
import argparse
import asyncio
import json
from pathlib import Path
import signal
import struct
import dns.flags
import dns.message
import dns.rcode
import dns.rrset


def answer(query,marker=10):
    r=dns.message.make_response(query);r.flags|=dns.flags.RA
    q=query.question[0];name=q.name.to_text().lower()
    if name.startswith('nx.') or name.startswith('nodata.'):
        if name.startswith('nx.'):r.set_rcode(dns.rcode.NXDOMAIN)
        if not name.startswith('nx.nosoa.'):
            r.authority.append(dns.rrset.from_text('test.',30,'IN','SOA','ns.test. hostmaster.test. 1 60 60 60 3'))
    elif name.startswith('servfail.'):
        r.set_rcode(dns.rcode.SERVFAIL)
    elif q.rdtype==dns.rdatatype.TXT:
        for i in range(12):r.answer.append(dns.rrset.from_text(f'{i}.{name}',30,'IN','TXT','"'+('x'*100)+'"'))
    else:
        ttl=0 if name.startswith('zero.') else 2 if name.startswith('short.') else 120
        target=name
        if name.startswith('alias.'):
            target='target.test.';r.answer.append(dns.rrset.from_text(q.name,2,'IN','CNAME',target))
        if q.rdtype==dns.rdatatype.AAAA:rr=dns.rrset.from_text(target,ttl,'IN','AAAA',f'2001:db8::{marker}')
        else:rr=dns.rrset.from_text(target,ttl,'IN','A',f'192.0.2.{marker}')
        r.answer.append(rr)
    return dns.message.from_wire(r.to_wire())


class ReferenceServer:
    def __init__(self,marker=10,delay=0.,drop=False,truncate=False,bad_id=False):
        self.marker=marker;self.delay=delay;self.drop=drop;self.truncate=truncate;self.bad_id=bad_id
        self.counts={'udp':0,'tcp':0};self.tasks=set();self.writers=set()
    def track(self,task):self.tasks.add(task);task.add_done_callback(self.tasks.discard)
    async def respond(self,wire,protocol):
        self.counts[protocol]+=1
        if self.drop:
            await asyncio.sleep(30);return None
        if self.delay:await asyncio.sleep(self.delay)
        q=dns.message.from_wire(wire);r=answer(q,self.marker)
        if self.truncate and protocol=='udp':r.answer=[];r.flags|=dns.flags.TC
        if self.bad_id:r.id=(r.id+1)%65536
        return r.to_wire(max_size=65535)
    async def start(self):
        peer=self
        class Protocol(asyncio.DatagramProtocol):
            def connection_made(self,t):self.t=t
            def datagram_received(self,data,addr):
                async def reply():
                    r=await peer.respond(data,'udp')
                    if r and not self.t.is_closing():self.t.sendto(r,addr)
                peer.track(asyncio.create_task(reply()))
        self.listener=await asyncio.start_server(self.tcp,'127.0.0.1',0)
        self.port=self.listener.sockets[0].getsockname()[1]
        self.transport,_=await asyncio.get_running_loop().create_datagram_endpoint(Protocol,local_addr=('127.0.0.1',self.port))
        return self.port
    async def tcp(self,reader,writer):
        self.track(asyncio.current_task());self.writers.add(writer)
        try:
            while True:
                size=struct.unpack('!H',await reader.readexactly(2))[0]
                wire=await reader.readexactly(size);r=await self.respond(wire,'tcp')
                if r is None:continue
                writer.write(struct.pack('!H',len(r))+r);await writer.drain()
        except (asyncio.IncompleteReadError,ConnectionError):pass
        finally:
            self.writers.discard(writer);writer.close()
            try:await writer.wait_closed()
            except OSError:pass
    async def close(self):
        self.listener.close();self.transport.close()
        await asyncio.sleep(0)
        for t in list(self.tasks):t.cancel()
        await asyncio.gather(*list(self.tasks),return_exceptions=True)
        for w in list(self.writers):w.close()
        await asyncio.wait_for(self.listener.wait_closed(),.5)


async def main(args):
    state=args.state;state.mkdir(parents=True,exist_ok=True)
    p=ReferenceServer(args.marker,args.delay,args.drop,args.truncate);port=await p.start()
    (state/'ready.json').write_text(json.dumps({'port':port}))
    event=asyncio.Event()
    for sig in [signal.SIGINT,signal.SIGTERM]:asyncio.get_running_loop().add_signal_handler(sig,event.set)
    await event.wait();await p.close()
    (state/'metrics.json').write_text(json.dumps(p.counts))
    (state/'ready.json').unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);parser.add_argument('--marker',type=int,default=10);parser.add_argument('--delay',type=float,default=0.);parser.add_argument('--drop',action='store_true');parser.add_argument('--truncate',action='store_true')
    asyncio.run(main(parser.parse_args()))
