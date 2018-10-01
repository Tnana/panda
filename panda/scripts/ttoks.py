#!/usr/bin/env python2.7

"""
ttoks.py pandalog start_va end_va

Reads in pandalog generated by taint_debian.py and uses it to get a
parse of the input in terms of tainted tokens in the input.

1st arg is path to pandalog file generated by taint_debian.py 

2nd and 3rd args are range of virtual addresses for the executable of
interest.  All taint query results for program counters outside that
range will be ignored. NB: these args are in hex!

Example use:

./ttoks.py taint.plog 0x8000000 0x9000000

This is rather like what we did in the original Taint-based Whitebox
Fuzzing paper, where we taint all bytes in the input positionally
(first byte gets label '0', second gets label '1', etc), and then
query registers used in compare or branch, or ld/st instructions to
see if they derive from input bytes. If they do, then the taint system
tells us which 'token' or extent of input bytes they derive from. It
also tells us things like the taint compute number of those derived
quantities (0 means a direct copy, larger numbers imply more
intervening computation). The program (plus the taint system)
effectively tells us how it is parsing the input.

"""

import sys
import numpy
from plog_reader import PLogReader                                                           

uls = {}

def update_uls(tq):
    for tqe in tq:
        if tqe.HasField("unique_label_set"):
            x = tqe.unique_label_set
            uls[x.ptr] = x.label 

def check_range(pc, range):
    r_min,r_max=range
    if (pc >= r_min) and (pc <= r_max):
        return True
    return False


def get_ttok(tq):
    all_labels = set([])
    tcns = []
    for q in tq:
        tcns.append(q.tcn)
        for l in uls[q.ptr]:
            all_labels.add(l)
    ttok = " ".join([str(x) for x in all_labels])
    return (numpy.mean(tcns), numpy.std(tcns), ttok)

def get_ttoks(filename, pc_range):
    ttoks = {}
    with PLogReader(filename) as plr:
        for m in plr:
            tq = None
            if m.HasField("tainted_branch"): tq = m.tainted_branch.taint_query
            if m.HasField("tainted_ldst"): tq = m.tainted_ldst.taint_query                       
            if m.HasField("tainted_cmp"): tq = m.tainted_cmp.taint_query
            if not (tq is None):
                update_uls(tq)                
                if not check_range(m.pc, pc_range):
                    continue
                (tcnm,tcns,tt) = get_ttok(tq)                
                v = (m.pc,tcnm,tcns,len(tq))
                if not (tt in ttoks):
                    ttoks[tt] = [v]
                else:
                    ttoks[tt].append(v)
    return ttoks


# translate from string to hex to get pc range
ra = (int(sys.argv[2], 16), int(sys.argv[3], 16))

ttoks = get_ttoks(sys.argv[1], ra)

for tt in ttoks.keys():
    print tt
    for x in ttoks[tt]:
        (pc,m,s,sz) = x
        if s==0:
            print "  pc=%x tcn=%d sz=%d" % (pc, m, sz)
        else:
            print "  pc=%x tcn=(%.1f+/%.1f sz=%d" % (pc, m, s, sz)


