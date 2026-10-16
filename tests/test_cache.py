import copy
import unittest
import dns.flags
import dns.message
import dns.rrset
from dnsrouter.cache import Cache,key,normalize
from dnsrouter.config import parse,route
from tools.upstream import answer
from support import config


class CacheTests(unittest.TestCase):
    def test_ttl_boundary_age_id_case_and_no_mutation(self):
        clock=[10.];c=Cache(2,10000,lambda:clock[0]);q=dns.message.make_query('WWW.test.','A');r=answer(q)
        life=normalize(r,30);c.put(key(q),r,life)
        clock[0]+=1.2;q2=dns.message.make_query('www.TEST.','A');got,_=c.get(key(q2),q2)
        self.assertEqual(got.id,q2.id);self.assertEqual(got.question,q2.question);self.assertEqual(got.answer[0].ttl,28)
        self.assertEqual(r.answer[0].ttl,30)
        clock[0]=40.;self.assertIsNone(c.get(key(q),q));self.assertEqual(c.bytes,0)
    def test_positive_zero_and_negative_soa_minimum(self):
        for prefix,kind,ttl in [('www','positive',120),('nx','nxdomain',3),('nodata','nodata',3)]:
            q=dns.message.make_query(prefix+'.test.','A');r=answer(q)
            self.assertEqual(normalize(r,3600),(ttl,kind))
            if kind!='positive':self.assertEqual(r.authority[0].ttl,3)
        for name in ['zero.test.','nx.nosoa.test.','servfail.test.']:
            self.assertIsNone(normalize(answer(dns.message.make_query(name,'A')),3600))
    def test_cname_and_lru_byte_limits(self):
        q=dns.message.make_query('alias.test.','A');r=answer(q);self.assertEqual(normalize(r,3600),(2,'positive'))
        c=Cache(1,10000);c.put(key(q),r,(2,'positive'))
        q2=dns.message.make_query('other.test.','A');r2=answer(q2);c.put(key(q2),r2,(120,'positive'))
        self.assertIsNone(c.get(key(q),q));self.assertEqual(c.evictions,1)
        c2=Cache(10,len(r.to_wire())-1);c2.put(key(q),r,(2,'positive'));self.assertEqual(c2.bytes,0)
    def test_query_flags_and_edns_partition(self):
        a=dns.message.make_query('www.test.','A');b=copy.deepcopy(a);b.flags|=dns.flags.CD
        self.assertNotEqual(key(a),key(b));self.assertIsNone(key(dns.message.make_query('www.test.','TXT')))
    def test_longest_label_suffix_and_validation(self):
        cfg=parse(config(1234,routes=[{'suffix':s,'upstreams':[{'host':'127.0.0.1','port':p}]} for s,p in [('.',1),('LAB.test.',2),('sub.lab.test.',3)]]))
        for name,port in [('x.lab.test.',2),('badlab.test.',1),('x.sub.lab.test.',3)]:
            self.assertEqual(route(cfg,dns.name.from_text(name))['upstreams'][0]['port'],port)
        for patch in [dict(host='0.0.0.0'),dict(max_inflight=True),dict(upstream_timeout=float('nan')),dict(routes=[])]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):parse(config(1234,**patch))
    def test_lru_hit_promotes_and_expiry_reclaims_bytes(self):
        clock=[0.];c=Cache(2,10000,lambda:clock[0])
        qs=[dns.message.make_query(n+'.test.','A') for n in ['one','two','three']]
        for q in qs[:2]:c.put(key(q),answer(q),(2,'positive'))
        c.get(key(qs[0]),qs[0]);c.put(key(qs[2]),answer(qs[2]),(2,'positive'))
        self.assertIsNone(c.get(key(qs[1]),qs[1]));self.assertIsNotNone(c.get(key(qs[0]),qs[0]))
        self.assertEqual(c.evictions,1)
        clock[0]=2.;c.put(key(qs[1]),answer(qs[1]),(2,'positive'))
        self.assertEqual(c.expired,2);self.assertEqual(len(c.items),1)
        self.assertEqual(c.bytes,len(answer(qs[1]).to_wire()))
    def test_negative_cname_terminal_soa_and_zero_minimum(self):
        q=dns.message.make_query('alias.test.','A')
        for code in [dns.rcode.NXDOMAIN,dns.rcode.NOERROR]:
            r=dns.message.make_response(q);r.set_rcode(code)
            r.answer.append(dns.rrset.from_text('alias.test.',2,'IN','CNAME','missing.other.'))
            r.authority.append(dns.rrset.from_text('test.',30,'IN','SOA','ns.test. hostmaster.test. 1 60 60 60 3'))
            r=dns.message.from_wire(r.to_wire());self.assertIsNone(normalize(r,3600))
            r.authority=[dns.rrset.from_text('other.',30,'IN','SOA','ns.other. hostmaster.other. 1 60 60 60 3')]
            r=dns.message.from_wire(r.to_wire())
            self.assertEqual(normalize(r,3600),(2,'nxdomain' if code==3 else 'nodata'))
            r.authority=[dns.rrset.from_text('other.',30,'IN','SOA','ns.other. hostmaster.other. 1 60 60 60 0')]
            r=dns.message.from_wire(r.to_wire());self.assertIsNone(normalize(r,3600))
