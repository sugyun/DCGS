# -*- coding: utf-8 -*-
"""
Created on Fri Dec  4 11:27:55 2020

@author: ansu
"""
import copy
import networkx as nx
from itertools import product
from dcgs import canalFunction
from dcgs.replace_str import replaceMultiple2
import PyBoolNet # code from https://github.com/hklarner/PyBoolNet
# get canalized states by using canalizing effect of fixed FVS
def get_canalized_states(booleanlogic, dgraph, nodeList, inputNodeState, minimal_fvs):
    canalized_states = []
    # Canalizing effect(CE) of input node
    state=canalFunction.main(inputNodeState,booleanlogic)
    state_origin = state.copy()
    # If minimal_fvs is empty, return the state with fixed inputs
    if minimal_fvs == []:
        CSS = state_origin.copy()
        return(CSS, state_origin)
    # generate 0,1 combination
    fvs_len = len(minimal_fvs[0])
    possible_fvs_values = product(('False', 'True'), repeat=fvs_len)
    # calculate canalization of each fvs state
    for fstate in possible_fvs_values:
        state = state_origin.copy()
        for fvn,fs in zip(minimal_fvs[0],fstate):
            state[fvn] = fs
        modeltext = '%s' % booleanlogic
        # Canalizing effect(CE) of fvs fixation
        fixedState=canalFunction.main(state,modeltext)
        canalized_states.append(fixedState)
    CSS = canalized_states
    return(CSS,state_origin)

def getPrimeFromBoolean(booleanlogic):
    bnet = booleanlogic.replace('=',',\t')
    bnet = replaceMultiple2(bnet, [' and ',' or ',' not '], [' & ',' | ',' ! '])
    bnet = replaceMultiple2(bnet, ['True','False'], [' 1 ',' 0 '])
    primes = PyBoolNet.FileExchange.bnet2primes(bnet)
    from collections import OrderedDict
    primes = OrderedDict(sorted(primes.items(), key=lambda t: int(t[0][1:])))
    return(primes)

# edit the PyBoolNet.StateTransitionGraphs.primes2stg code.
# add search_depth option
def primes2stg_search_depth(Primes, Update,  InitialStates, search_depth=0):
	"""
	Creates the state transition graph (STG) of a network defined by *Primes* and *Update*.
	The *InitialStates* are either a list of states (in *dict* or *str* representation),
	a function that flags states that belong to the initial states, or
	a subspace (in *dict* or *str* representation).
	If *InitialStates* is a function then it must take a single parameter *State* in dict representation
	and return a Boolean value that indicates whether it belongs to the initial states or not.
	The STG is constructed by a depth first search (DFS) starting from the given initial states.
	The default for *InitialStates* is ``lambda x: True``, i.e., every state is initial.
	For a single initial state, say *"100"* use *InitialStates="100"*,
	for a set of initial states use *InitialStates=["100", "101"]* and
	for a initial subspace use *InitialStates="1--"* or the *dict* representation of subspaces.
	**arguments**:
		* *Primes*: prime implicants
		* *Update* (str): either *"asynchronous"* or *"synchronous"*
		* *InitialStates* (func/str/dict/list): a function, a subspace, a state or a list of states
	**returns**:
		* *STG* (networkx.DiGraph): state transition graph
	**example**::
		>>> primes = FEX.read_primes("mapk.primes")
		>>> update = "asynchronous"
		>>> init = lambda x: x["ERK"]+x["RAF"]+x["RAS"]>=2
		>>> stg = primes2stg(primes, update, init)
		>>> stg.order()
		32
		>>> stg.edges()[0]
		('01000','11000')
		>>> init = ["00100", "00001"]
		>>> stg = primes2stg(primes, update, init)
		>>> init = {"ERK":0, "RAF":0, "RAS":0, "MEK":0, "p38":1}
		>>> stg = primes2stg(primes, update, init)
	"""

	assert(Update in ['asynchronous','synchronous']) # MIXED has too many transitions to draw stg

	if len(InitialStates)>2**15:
		print("The state transition graph will be generated from the %s (> 2^15) InitialStates."%(len(InitialStates)))
		print("This will take a while and we might run out of memory.")

	stg = nx.DiGraph()

	if Update=="asynchronous":
		successors = lambda x: PyBoolNet.StateTransitionGraphs.successors_asynchronous(Primes, x)
	if Update=="synchronous":
		successors = lambda x: [PyBoolNet.StateTransitionGraphs.successor_synchronous(Primes, x)]

	names =  list(Primes.keys())
	space = len(names)*[[0,1]]

	# function
	if hasattr(InitialStates, '__call__'):
		fringe = [dict(zip(names, values)) for values in product(*space)]
		fringe = [PyBoolNet.StateTransitionGraphs.state2str(x) for x in fringe if InitialStates(x)]

	# subspace
	elif type(InitialStates) in [str,dict]:
		fringe = PyBoolNet.StateTransitionGraphs.list_states_in_subspace(names, InitialStates)

	# some iterable
	else:
		fringe = [PyBoolNet.StateTransitionGraphs.state2str(x) for x in InitialStates]
	
	if search_depth == 0:
		seen = set([])
		while fringe:
			source = fringe.pop()
			if source in seen: continue
	
			for target in successors(source):
				target = PyBoolNet.StateTransitionGraphs.state2str(target)
				stg.add_edge(source, target)
	
				if target not in seen:
					fringe.append(target)
	
			seen.add(source)
	if search_depth > 0:
#		seen = set([])
		while fringe:
			source = fringe.pop()
	#		if source in seen: continue
			for i in range(search_depth):
				for target in successors(source):
					target = PyBoolNet.StateTransitionGraphs.state2str(target)
					stg.add_edge(source, target)
				if source == target:
					break
				else: source = '%s'%target
	
	#			if target not in seen:
	#				fringe.append(target)
	
#			seen.add(source)

	# defaults
	stg.graph["node"]  = {"shape":"rect", "color":"none", "style":"filled", "fillcolor":"none"}
	stg.graph["edge"]  = {}
	stg.graph["subgraphs"]  = []

	# heuristic scaling to avoid overlapping node labels
	if Update=="synchronous":
		stg.graph["overlap"] = "compress"
	else:
		stg.graph["overlap"] = "scale"

	return stg

def get_pointattractorFromCSS(booleanlogic, CSS):   
    primes = getPrimeFromBoolean(booleanlogic)
    initialstates = []
    for css in CSS:
        _s = css.values()
        _ss = [1 if x =='True' else 0 for x in _s]
        _sss = ''.join([str(x) for x in _ss])
        initialstates.append(_sss)
    stg = primes2stg_search_depth(primes,"synchronous",InitialStates=initialstates, search_depth=1)
    steady, _cyclic = PyBoolNet.Attractors.compute_attractors_tarjan(stg)
    paStr = steady.copy()
    paDic = []
    for pastr in paStr:
        pad = {}
        for k,v in zip(CSS[0].keys(),list(pastr)):
            if v == '0':
                pad[k] = 'False'
            elif  v == '1':
                pad[k] = 'True'
        paDic.append(pad)
    return(paStr, paDic)


if __name__ == '__main__':
    from dcgs.booleanlogic_preprocessing import modeltext2nummodeltext
    from dcgs.booleanlogic_preprocessing import get_interaction_network
    from dcgs import sccTofvs
    booleanlogic = '''
    A = B
    E = False
    C = not B and E
    B = A or ( C and D ) 
    D = False
    F = A or G
    G = F
    '''
    booleanlogicNum, node2num, num2node = modeltext2nummodeltext(booleanlogic)
    dgraph, nodeList, inputNodeState = get_interaction_network(booleanlogicNum)
    dic_hierarchy, dic_fvs, minimal_fvs = sccTofvs.scc2fvs_bruteforce(dgraph)
    minimal_fvs = [minimal_fvs]
    CSS, state_origin = get_canalized_states(booleanlogicNum, dgraph, nodeList, inputNodeState, minimal_fvs)
    paStr,paDic = get_pointattractorFromCSS(booleanlogicNum, CSS)
    dgraph_removed = dgraph.copy()
    while 0 in [x[1] for x in dgraph_removed.out_degree()]:
        outdegree = [x for x in dgraph_removed.out_degree()]
        for k in outdegree:
            if k[1] == 0:
                inputNodeState[k[0]] = 'False'
                dgraph_removed.remove_node(k[0])
    BSS, minimalBSS,monodirectFVN = get_blink_states(booleanlogicNum, dgraph, nodeList, inputNodeState, minimal_fvs)
    caStr, caDic = get_cyclicattractorFromBSS(booleanlogicNum, nodeList,minimalBSS)
    print('Attractor landscape seeker')
    print(paStr, caStr)
    # get attractors by pyboolnet
    primes = getPrimeFromBoolean(booleanlogicNum)
    stg = PyBoolNet.StateTransitionGraphs.primes2stg(primes, "synchronous")
    steady, cyclic = PyBoolNet.Attractors.compute_attractors_tarjan(stg)
    print('PyBoolnet')
    print(steady, cyclic)

