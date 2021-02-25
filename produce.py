#!/usr/bin/env python3
import csv
import argparse
from ipaddress import IPv4Network, AddressValueError

parser = argparse.ArgumentParser(description='Generate non-China routes for BIRD.')
parser.add_argument('--exclude', metavar='CIDR', type=str, nargs='*',
                    help='IPv4 ranges to exclude in CIDR format')
parser.add_argument('--next', default="wg0", metavar = "INTERFACE OR IP",
                    help='next hop for where non-China IP address, this is usually the tunnel interface')

args = parser.parse_args()

class Node:
    def __init__(self, cidr, parent=None):
        self.cidr = cidr
        self.child = []
        self.dead = False
        self.parent = parent

    def __repr__(self):
        return "<Node %s>" % self.cidr

nchnroutes = []

def dump_nchnroutes(lst):
    for n in lst:
        if n.dead:
            continue

        if len(n.child) > 0:
            dump_nchnroutes(n.child)

        elif not n.dead:
            nchnroutes.append(n.cidr)

RESERVED = [
    IPv4Network('0.0.0.0/8'),
    IPv4Network('10.0.0.0/8'),
    IPv4Network('127.0.0.0/8'),
    IPv4Network('169.254.0.0/16'),
    IPv4Network('172.16.0.0/12'),
    IPv4Network('192.0.0.0/29'),
    IPv4Network('192.0.0.170/31'),
    IPv4Network('192.0.2.0/24'),
    IPv4Network('192.168.0.0/16'),
    IPv4Network('198.18.0.0/15'),
    IPv4Network('198.51.100.0/24'),
    IPv4Network('203.0.113.0/24'),
    IPv4Network('240.0.0.0/4'),
    IPv4Network('255.255.255.255/32'),
    IPv4Network('169.254.0.0/16'),
    IPv4Network('127.0.0.0/8'),
    IPv4Network('224.0.0.0/4'),
    IPv4Network('100.64.0.0/10'),
]

if args.exclude:
    for e in args.exclude:
        RESERVED.append(IPv4Network(e))

def subtract_cidr(sub_from, sub_by):
    for cidr_to_sub in sub_by:
        for n in sub_from:
            if n.cidr == cidr_to_sub:
                n.dead = True
                break

            if n.cidr.supernet_of(cidr_to_sub):
                if len(n.child) > 0:
                    subtract_cidr(n.child, sub_by)

                else:
                    n.child = [Node(b, n) for b in n.cidr.address_exclude(cidr_to_sub)]

                break

root = []

with open("ipv4-address-space.csv", newline='') as f:
    f.readline() # skip the title

    reader = csv.reader(f, quoting=csv.QUOTE_MINIMAL)
    for cidr in reader:
        if cidr[5] == "ALLOCATED" or cidr[5] == "LEGACY":
            block = cidr[0]
            cidr = "%s.0.0.0%s" % (block[:3].lstrip("0"), block[-2:], )
            root.append(Node(IPv4Network(cidr)))

with open("chnroutes.txt") as f:
    for line in f:
        try:
            a = IPv4Network(line.strip())
            subtract_cidr(root, (a,))
        except AddressValueError:
            pass

# get rid of reserved addresses
subtract_cidr(root, RESERVED)

dump_nchnroutes(root)

with open("routes4.conf", "w") as f:
    f.write('\n'.join([f'route {cidr} via "{args.next}";' for cidr in nchnroutes]))

with open("nchnroutes.txt", "w") as f:
    f.write('\n'.join([f'{cidr}' for cidr in nchnroutes]))
