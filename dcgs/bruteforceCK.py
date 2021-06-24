# -*- coding: utf-8 -*-
"""
Created on Wed Dec  2 15:18:48 2020

@author: ansu
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 17:01:59 2020

@author: ansu
"""
import pandas as pd
import itertools
import pickle

import PyBoolNet # code from https://github.com/hklarner/PyBoolNet
from dcgs.replace_str import replaceMultiple2
from dcgs.booleanlogic_preprocessing import get_interaction_network,modeltext2nummodeltext
from dcgs.attractorlandscapeSeeker import getPrimeFromBoolean

def algorithm(booleanlogic, targetattractor):
    booleanlogicNum, node2num, num2node = modeltext2nummodeltext(booleanlogic)
    dgraph, nodeList, inputNodeState = get_interaction_network(booleanlogicNum)
    netsize = len(dgraph.nodes())
    inputnode = []
    for n in dgraph.in_degree():
        if n[1] == 0:
            inputnode.append(n[0])
    primes = getPrimeFromBoolean(booleanlogicNum)
    attractor = targetattractor
    bnet = booleanlogicNum.replace('=',',\t')
    bnet = replaceMultiple2(bnet, [' and ',' or ',' not '], [' & ',' | ',' ! '])
    bnet = replaceMultiple2(bnet, ['True','False'], [' 1 ',' 0 '])
    bnetline = bnet.split('\n')
    nodelist_WO_inputnode = list(set(dgraph.nodes())-set(inputnode))
    FindCK = False    
    CK = []
    for combinationnum in range(len(nodelist_WO_inputnode)+1):
        if FindCK == True:
            return(CK)
        combinationset = itertools.combinations(nodelist_WO_inputnode, combinationnum)
        for combinationnodes in combinationset:
            bnetline_pert = bnetline.copy()
            for linenum, line in enumerate(bnetline_pert):
                if line.strip() == '':
                    continue
                Cnode = line.split(',\t')[0].strip()
                if Cnode in combinationnodes:
                    if attractor[int(Cnode[1:])-1] == '1':
                        bnetline_pert[linenum] = Cnode +' ,\t '+str(1)
                    elif attractor[int(Cnode[1:])-1] == '0':
                        bnetline_pert[linenum] = Cnode +' ,\t '+str(0)
            bnet_pert = '\n'.join(bnetline_pert)
            primes_pert = PyBoolNet.FileExchange.bnet2primes(bnet_pert)
            stg = PyBoolNet.StateTransitionGraphs.primes2stg(primes_pert,"synchronous")
            steady, cyclic = PyBoolNet.Attractors.compute_attractors_tarjan(stg)
            if len(cyclic) == 0:
                if len(steady) == 1:
                    CK.append(combinationnodes)
                    FindCK = True
if __name__ == '__main__':
    booleanlogic = '''
    x1 = x2
    x2 = x1 or x3
    x3 = x2 and x5
    x4 = x5 or x3
    x5 = x4
    '''
    targetattractor = '11111'
    CK = algorithm(booleanlogic, targetattractor)
