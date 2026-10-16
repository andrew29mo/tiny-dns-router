"""Strict, immutable startup configuration; routing compares DNS labels."""
import ipaddress
import math
import dns.name

DEFAULTS = dict(host="127.0.0.1", port=1053, cache_entries=256,
                cache_bytes=1048576, ttl_cap=3600, max_inflight=64,
                max_tcp_connections=32, max_query_bytes=4096,
                upstream_timeout=.2, tcp_idle_timeout=2., drain_timeout=2.)


def parse(raw):
    if not isinstance(raw, dict) or set(raw)-set(DEFAULTS)-{'routes'}:
        raise ValueError('unknown configuration field')
    cfg = DEFAULTS | raw
    if cfg['host'] != '127.0.0.1':
        raise ValueError('MVP listener must be 127.0.0.1')
    bounds = dict(port=(0,65535),cache_entries=(0,4096),cache_bytes=(0,67108864),
                  ttl_cap=(1,86400),max_inflight=(1,1024),max_tcp_connections=(1,256),
                  max_query_bytes=(512,4096))
    for name,(lo,hi) in bounds.items():
        if type(cfg[name]) is not int or not lo<=cfg[name]<=hi:
            raise ValueError('invalid '+name)
    for name in ['upstream_timeout','tcp_idle_timeout','drain_timeout']:
        v=cfg[name]
        if type(v) not in [int,float] or not math.isfinite(v) or not .01<=v<=30:
            raise ValueError('invalid '+name)
    routes=cfg.get('routes')
    if not isinstance(routes,list) or not 1<=len(routes)<=32:
        raise ValueError('1..32 routes required')
    parsed=[];seen=set()
    for r in routes:
        if not isinstance(r,dict) or set(r)!={'suffix','upstreams'}:
            raise ValueError('route requires suffix and upstreams')
        name=dns.name.from_text(r['suffix']).canonicalize()
        if name in seen:raise ValueError('duplicate canonical suffix')
        seen.add(name)
        if not isinstance(r['upstreams'],list) or not 1<=len(r['upstreams'])<=8:
            raise ValueError('1..8 upstreams per route required')
        us=[]
        for u in r['upstreams']:
            if not isinstance(u,dict) or set(u)!={'host','port'}:
                raise ValueError('upstream requires host and port')
            if not isinstance(ipaddress.ip_address(u['host']),ipaddress.IPv4Address):
                raise ValueError('MVP upstream must be numeric IPv4')
            if type(u['port']) is not int or not 1<=u['port']<=65535:
                raise ValueError('invalid upstream port')
            us.append(dict(u))
        parsed.append(dict(suffix=name.to_text(),upstreams=us))
    if dns.name.root not in seen:raise ValueError('default dot route required')
    cfg['routes']=sorted(parsed,key=lambda r:len(dns.name.from_text(r['suffix']).labels),reverse=True)
    return cfg


def route(cfg, name):
    return next(r for r in cfg['routes'] if name.is_subdomain(dns.name.from_text(r['suffix'])))
