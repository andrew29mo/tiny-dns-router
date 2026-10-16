"""Explicit DNS query client; never changes system resolver configuration."""
import argparse
import json
import dns.message
import dns.query
import dns.rcode


def main():
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--type',default='A');p.add_argument('--port',type=int,default=1053);p.add_argument('--tcp',action='store_true');a=p.parse_args()
    q=dns.message.make_query(a.name,a.type);fn=dns.query.tcp if a.tcp else dns.query.udp
    r=fn(q,'127.0.0.1',port=a.port,timeout=3)
    print(json.dumps(dict(rcode=dns.rcode.to_text(r.rcode()),answer=[str(rr) for rr in r.answer],authority=[str(rr) for rr in r.authority]),indent=2))
if __name__=='__main__':main()
