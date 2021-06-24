# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 09:29:48 2020

@author: ssmha
"""

import networkx as nx
import matplotlib.pyplot as plt
import time

import dcgs.fvs as fvs# code from https://github.com/rionbr/CANA

def scc2fvs_combine(DG, thres=20):
    DG2 = DG.copy()
    ih = 0
    dic_hirachy = {}
    dic_fvs = {}
    mfvs = []
    while DG2.nodes():
        for i in nx.attracting_components(DG2):
            sccname = '_'.join([str(x) for x in i])
            dic_hirachy[sccname] = ih
            if len(i) > 1:
                # use bruteforce algorithm when the size of SCC is smaller than 10.
                if len(i) <int(thres):
                    dic_fvs[sccname] = [list(x) for x in fvs.fvs_bruteforce(DG2.subgraph(i), max_search=len(i))]
                # use GRASP algorithm when the size of SCC is large. GRASP find only one FVS
                else:
                    print('Using GRASP algorithm. It is not exact and finds only one possible FVS.')
                    dic_fvs[sccname] = [list(x) for x in fvs.fvs_grasp(DG2.subgraph(i), max_iter=2000)]
                mfvs.extend(dic_fvs[sccname][0])
            # Add selfloop node to FVS
            elif list(i)[0] in nx.nodes_with_selfloops(DG):
                dic_fvs[sccname] = [list(i)]
                mfvs.extend(list(i))
            for n in i:
                DG2.remove_node(n)
        ih += 1
    return(dic_hirachy, dic_fvs, sorted(mfvs))
def scc2fvs_bruteforce(DG):
    DG2 = DG.copy()
    ih = 0
    dic_hirachy = {}
    dic_fvs = {}
    mfvs = []
    while DG2.nodes():
        for i in nx.attracting_components(DG2):
            sccname = '_'.join([str(x) for x in i])
            dic_hirachy[sccname] = ih
            dic_fvs[sccname] = [list(x) for x in fvs.fvs_bruteforce(DG2.subgraph(i), max_search=len(i),  keep_self_loops=True)]
            mfvs.extend(dic_fvs[sccname][0])
            for n in i:
                DG2.remove_node(n)
        ih += 1
    return(dic_hirachy, dic_fvs, sorted(mfvs))

if __name__ == '__main__':
    DG = nx.generators.directed.random_k_out_graph(100, 3, 0.5)
    DG = nx.DiGraph(DG)
    nx.draw(DG, with_labels=True)
    start = time.time()
    dic_hirachy, dic_fvs, mfvs = scc2fvs_combine(DG, thres=20)
    print("scc2fvs_combine time :", time.time() - start)
    start = time.time()
    dic_hirachy, dic_fvs, mfvs = scc2fvs_bruteforce(DG)
    print("scc2fvs_bruteforce time :", time.time() - start)
    start = time.time()
    dic_hirachy, dic_fvs, mfvs = scc2fvs_grasp(DG)
    print("scc2fvs_grasp time :", time.time() - start)
    

