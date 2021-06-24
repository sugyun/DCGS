# -*- coding: utf-8 -*-
"""
Created on Fri Dec  4 11:00:00 2020

@author: ansu
"""
from dcgs.replace_str import replaceMultiple
from dcgs.replace_str import replaceMultiple2
import re
import numpy as np
import networkx as nx

def modeltext2nummodeltext(modeltext):
    modeltextLine = modeltext.splitlines()
    node2num = {}
    num2node = {}
    i = 0
    for m in modeltextLine:
        if not (m.strip() == ""):
            i+=1
            target_node = m.split('=')[0].strip()
            node2num[target_node] = i
            num2node[str(i)] = target_node
    # To avoid the error when node name is included in other node name.
    new_d = {}
    for k in sorted(node2num, key=len, reverse=True):
        new_d[k] = node2num[k]
    node2num = new_d.copy()
    for node in node2num:
        modeltext = replaceMultiple2(modeltext, [node+' ='],['n'+'0'*(int(np.log10(len(node2num)))+1-len(str(node2num[node])))+str(node2num[node])+' ='])
        modeltext = replaceMultiple2(modeltext, [' '+node+' '],[' '+'n'+'0'*(int(np.log10(len(node2num)))+1-len(str(node2num[node])))+str(node2num[node])+' '])
        modeltext = replaceMultiple2(modeltext, [' '+node+'\n'],[' '+'n'+'0'*(int(np.log10(len(node2num)))+1-len(str(node2num[node])))+str(node2num[node])+'\n'])

    return(modeltext, node2num, num2node)

# get pyhsical interaction network from boolean logic text
def get_interaction_network(booleanlogic):
    dgraph = nx.DiGraph()
    inputNodeState = {}
    nodeList = []
    for line in booleanlogic.split('\n'):
        if line.strip() == '':
            continue
        line = line.strip().split('=')
        targetnode = line[0].strip()
        nodeList.append(targetnode)
        sourceline = replaceMultiple(line[1],[' and ',' or ',' not ','(',')'],' ')
        sournodelist = [sn.strip() for sn in sourceline.split(' ') if sn.strip() != '']
        if sournodelist[0] in ['True','False']:
            inputNodeState[targetnode] = sournodelist[0]
            continue
        inputNodeState[targetnode] = ''
        for sourcenode in sournodelist:
            dgraph.add_edge(sourcenode,targetnode)
    return(dgraph, nodeList, inputNodeState)
    
if __name__ == '__main__':
    booleanlogic = '''
    A = B
    E = True
    C = not B and E
    B = A or C
    D = False
    '''
    booleanlogicNum, node2num, num2node = modeltext2nummodeltext(booleanlogic)
#    print('# Search for point attractors')
    dgraph, nodeList, inputNodeState = get_interaction_network(booleanlogic)
    
