# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 13:29:38 2020

@author: ansu
"""
import itertools
import numpy as np

import sccTofvs
import canalFunction
from booleanlogic_preprocessing import modeltext2nummodeltext
from booleanlogic_preprocessing import get_interaction_network

def algorithm(booleanlogic, targetattractor):
    # initial setting
    booleanlogicNum, node2num, num2node = modeltext2nummodeltext(booleanlogic)
    dgraph, nodeList, inputNodeState = get_interaction_network(booleanlogicNum)
    dic_hierarchy, dic_fvs, minimal_fvs = sccTofvs.scc2fvs_bruteforce(dgraph)
    hierarchylist =  list(dic_hierarchy.keys())
    hierarchylistorder = hierarchylist.copy()
    hierarchylistorder.reverse()
    minimal_fvs = [minimal_fvs]
    fvs_raw = []
    for scc in dic_fvs:
        if len(fvs_raw) == 0:
            fvs_raw = dic_fvs[scc]
            continue
        fvs2 = []
        for n,k in enumerate(fvs_raw):
            for f in dic_fvs[scc]:
                fvs2.append(fvs_raw[n] + f)
        fvs_raw = fvs2.copy()
    # if no FVS exists, return.
    if not minimal_fvs[0]:
        print('controlled by only input nodes')
        print('============= FINISH =============\n')
        return({},{},{},{})
    # canalizing effect of input nodes
    state_fix = canalFunction.main(inputNodeState,booleanlogicNum)
    ###########################################################################
    # categorize nodes in FVS into canalizing sets and canalized sets using canalizing effect
    dic_CS = {} # dictionary for canalizing sets
    dic_cCS = {} # dictionary for canalized sets
    dic_sccFVS = {} # FVS in each SCC
    # analyze each SCC sequentially
    for i in range(len(hierarchylist)):
        CS = [] # canalizing sets
        cCS = [] # canalized sets
        # analyze all FVS in each SCC
        for currentFVS in fvs_raw:
            sccnodes = hierarchylist[-(i+1)].split('_')
            sccnodeindex = sorted([int(x[1:]) for x in sccnodes])
            sccnodes = ['n'+'0'*(int(np.log10(len(node2num)))+1-len(str(x)))+str(x) for x in sccnodeindex]
            dic_sccFVS[hierarchylist[-(i+1)]] = list(set(sccnodes).intersection(currentFVS)) # current analyzed FVS in the SCC
            state_fix_scc = state_fix.copy() # canalizing effect of input nodes
            node2fix = list(set(nodeList)-set(sccnodes)) # nodes that are not related to the current SCC.
            # fix the nodes' state to target attractor state
            for nscc in node2fix:
                if targetattractor[int(nscc[1:])-1] == '0':
                    state_fix_scc[nscc] = 'False'
                else:
                    state_fix_scc[nscc] = 'True'
            state_fix_scc=canalFunction.main(state_fix_scc,booleanlogicNum) # Canalizing effect of fixed nodes
            node2fix = set([x for x in state_fix_scc if state_fix_scc[x] in ['True','False']])
            scc_fvs = [list(set(sccnodes).intersection(currentFVS) - node2fix)]
            # If scc is fixed by the fixed nodes, then save result and continue
            if '' not in list(state_fix_scc.values()):
                dic_cCS[hierarchylist[-(i+1)]] = [dic_sccFVS[hierarchylist[-(i+1)]]]
                dic_CS[hierarchylist[-(i+1)]] = [[]]
                continue
            # check canalizing effect of FVS subsets
            find_combi = False
            for L, F in enumerate(scc_fvs[0]):
                if find_combi:
                        break
                for cc in itertools.combinations(scc_fvs[0],L+1):
                    cstate = state_fix_scc.copy()
                    for cc2 in cc:
                        if targetattractor[int(cc2[1:])-1] == '0':
                            cstate[cc2] = 'False'
                        else:
                            cstate[cc2] = 'True'
                    ss2=canalFunction.main(cstate,booleanlogicNum) # canalizing effect of FVS subset.
                    if '' not in list(ss2.values()):
                        find_combi=True
                        CS.append(list(cc))
                        cCS.append([sorted(list(set(dic_sccFVS[hierarchylist[-(i+1)]]).difference(cc)))])
        if CS == []:
            dic_cCS[hierarchylist[-(i+1)]] = [dic_sccFVS[hierarchylist[-(i+1)]]]
            dic_CS[hierarchylist[-(i+1)]] = [[]]
            continue
        # select minimum canalizing sets.
        CS_minsize = min([len(x) for x in CS])
        CS_filtered = []
        cCS_filtered = []
        for cs_num in range(len(CS)):
            if len(CS[cs_num]) != CS_minsize:
                continue
            CS_filtered.append(CS[cs_num])
            cCS_filtered.append(cCS[cs_num])
        dic_CS[hierarchylist[-(i+1)]] = CS_filtered
        dic_cCS[hierarchylist[-(i+1)]] = cCS_filtered

    return(dic_CS,dic_cCS, dic_fvs)
    
if __name__ == '__main__':
    booleanlogic = '''
    x1 = x2
    x2 = x1 or x3
    x3 = x2 and x5
    x4 = x5 or x3
    x5 = x4
    '''
    targetattractor = '11111'
    dic_CS,dic_cCS, dic_fvs = algorithm(booleanlogic, targetattractor)
