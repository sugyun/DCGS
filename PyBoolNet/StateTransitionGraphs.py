

import random
import itertools
import heapq
import networkx

from typing import List

import PyBoolNet.FileExchange
import PyBoolNet.AspSolver
import PyBoolNet.Utility.Misc
import PyBoolNet.Utility.DiGraphs

CMD_DOT = PyBoolNet.Utility.Misc.find_command("dot")

UPDATE_STRATEGIES = ["asynchronous", "synchronous", "mixed"]


def energy(Primes, State):
    """
    This integer valued energy function E for Boolean networks is decreasing with transitions.
    That is, E(x) >= E(y) holds for any transition x -> y.
    It is based on the number of free variables in the smallest trapspace that contains *State*.
    The energy is therefore n >= E(x) >= 0 and E(x)=0 for steady states holds.

    **arguments**:
        * *Primes*: prime implicants
        * *State* (dict / str): a state

    **returns**:
        * *Energy* (int): number of free variables in smallest trapspace containing *State*

    **example**::

        >>> primes = Repository.get_primes("raf")
        >>> StateTransitionGraphs.energy(primes, "000")
        1
        >>> StateTransitionGraphs.energy(primes, "010")
        3
        >>> StateTransitionGraphs.energy(primes, "001")
        0
    """
    
    tspace = PyBoolNet.AspSolver.trapspaces_that_contain_state(Primes, State, Type="min", FnameASP=None,
                                                               Representation="str")
    energy = tspace.count('-')
    
    return energy


def dot2image(FnameDOT, FnameIMAGE, LayoutEngine):
    PyBoolNet.Utility.DiGraphs.dot2image(FnameDOT, FnameIMAGE, LayoutEngine)


def primes2stg(Primes, Update, InitialStates=lambda x: True):
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
    
    if Update not in ['asynchronous', 'synchronous']:
        print("The chosen update might lead to a very big STG")
    
    if len(Primes) > 15:
        print("The state transition graph will consist of up to 2**%i=%i states, depending on the InitialStates. " %
              (len(Primes), 2 ** len(Primes)))
        print("This will take a while and we might run out of memory.")
    
    stg = networkx.DiGraph()
    
    if len(Primes) == 0:
        print("No Primes were given. Hence, the stg is empty.") 
        return stg   

    if Update == "asynchronous":
        successors = lambda x: successors_asynchronous(Primes, x)
    if Update == "synchronous":
        successors = lambda x: [successor_synchronous(Primes, x)]
    if Update == "mixed":
        successors = lambda x: [successors_mixed(Primes, x)]
    
    names = sorted(Primes)
    space = len(names) * [[0, 1]]
    
    # function
    if hasattr(InitialStates, '__call__'):
        fringe = [dict(zip(names, values)) for values in itertools.product(*space)]
        fringe = [state2str(x) for x in fringe if InitialStates(x)]
    
    # subspace
    elif type(InitialStates) in [str, dict]:
        fringe = list_states_in_subspace(names, InitialStates)
    
    # some iterable
    else:
        fringe = [state2str(x) for x in InitialStates]
    
    seen = set([])
    while fringe:
        source = fringe.pop()
        if source in seen: continue
        
        for target in successors(source):
            target = state2str(target)
            stg.add_edge(source, target)
            
            if target not in seen:
                fringe.append(target)
        
        seen.add(source)
    
    # defaults
    stg.graph["node"] = {"shape": "rect", "color": "none", "style": "filled", "fillcolor": "none"}
    stg.graph["edge"] = {}
    stg.graph["subgraphs"] = []
    
    # heuristic scaling to avoid overlapping node labels
    if Update == "synchronous":
        stg.graph["overlap"] = "compress"
    else:
        stg.graph["overlap"] = "scale"
    
    return stg


def stg2dot(STG, FnameDOT=None):
    """
    Creates a *dot* file from a state transition graph.
    Graph, node and edge attributes are passed to the *dot* file by adding the respective key and value pairs to the graph, node or edge data.
    Node and edge defaults are set by the specials graph keys *"node"* and *"edge"* and must have attribute dictionaries as values.
    For a list of attributes see http://www.graphviz.org/doc/info/attrs.html.

    **arguments**:
        * *STG*: state transition graph
        * *FnameDOT* (str): name of *dot* file or *None*

    **returns**:
        * *FileDOT* (str): file as string if not *FnameDOT==None*, otherwise it returns *None*

    **example**::

          >>> stg = primes2stg(primes, update, init)
          >>> stg.graph["label"] = "IRMA Network - State Transition Graph"
          >>> stg.graph["node"] = {"style":"filled", "color":"red"}
          >>> stg.graph["edge"] = {"arrowsize": 2.0}
          >>> stg.nodes["001000"]["fontsize"] = 20
          >>> stg.adj["001110"]["001010"]["style"] = "dotted"
          >>> stg2image(stg, "irma_stg.pdf")
    """
    
    return PyBoolNet.Utility.DiGraphs.digraph2dot(STG, FnameDOT)


def stg2image(STG, FnameIMAGE, LayoutEngine="fdp", Silent=False):
    """
    Creates an image file from a state transition graph using :ref:`installation_graphviz` and the *LayoutEngine*.
    Use ``dot -T?`` to find out which output formats are supported on your installation.

    **arguments**:
        * *STG*: state transition graph
        * *FnameIMAGE* (str): name of output file
        * *LayoutEngine*: one of "dot", "neato", "fdp", "sfdp", "circo", "twopi"
        * *Silent* (bool): print infos to screen

    **example**::

          >>> stg2image(stg, "mapk_stg.pdf")
          >>> stg2image(stg, "mapk_stg.jpg", "neato")
          >>> stg2image(stg, "mapk_stg.svg", "dot")
    """
    
    PyBoolNet.Utility.DiGraphs.digraph2image(STG, FnameIMAGE, LayoutEngine, Silent)


def create_image(Primes, Update, FnameIMAGE, InitialStates=lambda x: True, Styles=[], LayoutEngine:str ="dot"):
    """
    A convenience function for drawing state transition graphs directly from the prime implicants.
    *Styles* must be a sublist of ["tendencies", "sccs", "mintrapspaces", "anonymous"].

    **arguments**:
        * *Primes*: prime implicants
        * *FnameIMAGE* (str): name of image
        * *InitialStates* (func/str/dict/list): a function, a subspace, a state or a list of states
        * *Styles* (list): the styles to be applied
        * *LayoutEngine* (str): one of "dot", "neato", "fdp", "sfdp", "circo", "twopi"

    **example**::

          >>> create_image(primes, "asynchronous", "mapk_stg.pdf", Styles=["interactionsigns", "anonymous"])
    """
    
    assert (set(Styles).issubset(set(["tendencies", "sccs", "mintrapspaces", "anonymous"])))
    
    stg = primes2stg(Primes, Update, InitialStates)
    
    if "tendencies" in Styles:
        add_style_tendencies(stg)
    if "sccs" in Styles:
        add_style_sccs(stg)
    if "mintrapspaces" in Styles:
        add_style_mintrapspaces(Primes, stg)
    if "anonymous" in Styles:
        add_style_anonymous(stg)
    
    stg2image(stg, FnameIMAGE, LayoutEngine=LayoutEngine, Silent=False)


def copy(STG):
    """
    Creates a copy of *STG* including all *dot* attributes.

    **arguments**:
        * *STG*: state transition graph

    **returns**:
        * *STG2*: new state transition graph

    **example**::

        >>> stg2 = copy(stg)
    """
    
    newgraph = STG.copy()
    if newgraph.graph["subgraphs"]:
        newgraph.graph["subgraphs"] = [x.copy() for x in newgraph.graph["subgraphs"]]
    
    return newgraph


def add_style_tendencies(STG):
    """
    Sets or overwrites the edge colors to reflect whether a transition increases values (*black*),
    decreases values (*red*), or both (*blue*) which is only possible for non-asynchronous transitions.

    **arguments**:
        * *STG*: state transition graph

    **example**::

          >>> add_style_tendencies(stg)
    """
    
    for source, target, attr in sorted(STG.edges(data=True)):
        inc = any([source[x] + target[x] == "01" for x in range(len(source))])
        dec = any([source[x] + target[x] == "10" for x in range(len(source))])
        
        if inc and dec:
            STG.adj[source][target]["color"] = "dodgerblue"
        
        if inc:
            continue
        
        if dec:
            STG.adj[source][target]["color"] = "red"


def add_style_sccs(STG):
    """
    Adds a subgraph for every non-trivial strongly connected component (SCC) to the *dot* representation of *STG*.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    Each subgraph is filled by a shade of gray that gets darker with an increasing number of SCCs that are above it in the condensation graph.
    Shadings repeat after a depth of 9.

    **arguments**:
        * *STG*: state transition graph

    **example**::

          >>> add_style_sccs(stg)
    """
    
    condensation_graph = PyBoolNet.Utility.DiGraphs.digraph2condensationgraph(STG)
    
    for i, scc in enumerate(condensation_graph.nodes()):
        name = "cluster_%i " % i
        depth = condensation_graph.nodes[scc]["depth"]
        col = 2 + (depth % 8)
    
    subgraph = networkx.DiGraph()
    subgraph.add_nodes_from(scc)
    subgraph.graph["style"] = "filled"
    subgraph.graph["color"] = "black"
    subgraph.graph["fillcolor"] = "/greys9/%i" % col
    
    if not list(condensation_graph.successors(scc)):
        if len(scc) == 1:
            subgraph.graph["label"] = "steady state"
        else:
            subgraph.graph["label"] = "cyclic attractor"
    
    if not STG.graph["subgraphs"]:
        STG.graph["subgraphs"] = []
    
    # overwrite existing subgraphs
    for x in list(STG.graph["subgraphs"]):
        if sorted(x.nodes()) == sorted(subgraph.nodes()):
            STG.graph["subgraphs"].remove(x)
    
    STG.graph["subgraphs"].append(subgraph)


def add_style_subspaces(Primes, STG, Subspaces):
    """
    Adds a *dot* subgraph for every subspace in *Subspace* to *STG* - or overwrites them if they already exist.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    To add custom labels or fillcolors to a subgraph supply a tuple consisting of the
    subspace and a dictionary of subgraph attributes.

    .. note::

        *Subgraphs* must satisfy the following property:
        Any two subgraphs have either empty intersection or one is a subset of the other.
        The reason for this requirement is that *dot* can not draw intersecting subgraphs.

    **arguments**:
        * *Primes*: prime implicants
        * *STG*: state transition graph
        * *Subspaces* (list): list of subspaces in string or dict representation

    **example**:

        >>> subspaces = [{"v1":0},{"v1":0,"v3":1},{"v1":1,"v2":1}]
        >>> add_style_subspaces(primes, stg, subspaces)
        >>> subspaces = ["0--","0-1","11-"]
        >>> add_style_subspaces(primes, stg, subspaces)
    """
    
    names = sorted(Primes)
    
    if not STG.graph["subgraphs"]:
        STG.graph["subgraphs"] = []
    
    for x in Subspaces:
        
        attr = None
        
        # (subspace, attributes)
        if type(x) != dict and len(x) == 2 and type(x[1]) == dict:
            subspace, attr = x
            
            # subspace = "11--1-"
            if type(subspace) == str:
                subspace = subspace2dict(Primes, subspace)
            elif not type(subspace) == dict:
                raise Exception("Invalid Argument 'Subspaces'")
        
        else:
            # subspace = "11--1-"
            if type(x) == str:
                subspace = subspace2dict(Primes, x)
            # subspace = {"v1":0,"v5":1}
            elif type(x) == dict:
                subspace = x
            else:
                raise Exception("Invalid Argument 'Subspaces'")
        
        subgraph = networkx.DiGraph()
        subgraph.add_nodes_from(list_states_in_subspace(Primes, subspace))
        subgraph.graph["color"] = "black"
        subgraph.graph["label"] = "subspace %s" % subspace2str(Primes, subspace)
        if attr:
            subgraph.graph.update(attr)
        
        # overwrite existing subgraphs
        for x in list(STG.graph["subgraphs"]):
            if sorted(x.nodes()) == sorted(subgraph.nodes()):
                STG.graph["subgraphs"].remove(x)
        
        STG.graph["subgraphs"].append(subgraph)


def add_style_subgraphs(STG, Subgraphs):
    """
    Adds the subgraphs given in *Subgraphs* to *STG* - or overwrites them if they already exist.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    *Subgraphs* must consist of tuples of the form *NodeList*, *Attributs* where *NodeList* is a list of graph nodes and *Attributes*
    is a dictionary of subgraph attributes in *dot* format.

    .. note::

        *Subgraphs* must satisfy the following property:
        Any two subgraphs have either empty intersection or one is a subset of the other.
        The reason for this requirement is that *dot* can not draw intersecting subgraphs.

    **arguments**:
        * *STG*: state transition graph
        * *Subgraphs* (list): pairs of lists and subgraph attributes

    **example**:

        >>> sub1 = (["001","010"], {"label":"critical states"})
        >>> sub2 = (["111","011"], {})
        >>> subgraphs = [sub1,sub2]
        >>> add_style_subgraphs(stg, subgraphs)
    """
    
    PyBoolNet.Utility.DiGraphs.add_style_subgraphs(STG, Subgraphs)


def add_style_mintrapspaces(Primes, STG, MaxOutput=100):
    """
    A convenience function that combines :ref:`add_style_subspaces` and :ref:`AspSolver.trap_spaces <trap_spaces>`.
    It adds a *dot* subgraphs for every minimal trap space to *STG* - subgraphs that already exist are overwritten.

    **arguments**:
        * *Primes*: prime implicants
        * *STG*: state transition graph
        * *MaxOutput* (int): maximal number of minimal trap spaces, see :ref:`trap_spaces <sec:trap_spaces>`

    **example**:

        >>> add_style_mintrapspaces(primes, stg)
    """
    
    names = sorted(Primes)
    states = STG.nodes()
    
    for tspace in PyBoolNet.AspSolver.trap_spaces(Primes, "min", MaxOutput=MaxOutput):
        
        subgraph = networkx.DiGraph()
        subgraph.add_nodes_from([x for x in list_states_in_subspace(Primes, tspace) if x in states])
        if not subgraph.nodes():
            continue
        
        subgraph.graph["color"] = "black"
        if len(tspace) == len(Primes):
            subgraph.graph["label"] = "steady state"
        else:
            subgraph.graph["label"] = "min trap space %s" % subspace2str(Primes, tspace)
        
        if not STG.graph["subgraphs"]:
            STG.graph["subgraphs"] = []
        
        # overwrite existing subgraphs
        for x in list(STG.graph["subgraphs"]):
            if sorted(x.nodes()) == sorted(subgraph.nodes()):
                STG.graph["subgraphs"].remove(x)
        
        STG.graph["subgraphs"].append(subgraph)


def add_style_path(STG, Path, Color, Penwidth=3):
    """
    Sets the color of all nodes and edges involved in the given *Path* to *Color*.

    **arguments**:
        * *STG*: state transition graph
        * *Path* (list): state dictionaries or state strings
        * *Color* (str): color of the path
        * *Penwidth* (int): width of nodes and edges involved in *Path* in pt

    **example**::

        >>> path = ["001", "011", "101"]
        >>> add_style_path(stg, path, "red")
    """
    
    assert (Path != None)
    
    Path = [state2str(x) if type(x) == dict else x for x in Path]
    
    for x in Path:
        STG.nodes[x]["color"] = Color
        STG.nodes[x]["penwidth"] = "%i" % Penwidth
    
    if len(Path) > 1:
        for x, y in zip(Path[:-1], Path[1:]):
            STG.adj[x][y]["color"] = Color
            STG.adj[x][y]["penwidth"] = "%i" % Penwidth


def add_style_default(Primes, STG):
    """
    A convenience function that adds styles for tendencies, SCCs and minimal trap spaces.

    **arguments**:
        * *Primes*: primes implicants
        * *STG*: state transition graph

    **example**::

        >>> add_style_default(stg)
    """
    
    add_style_sccs(STG)
    add_style_tendencies(STG)
    add_style_mintrapspaces(Primes, STG)


def add_style_anonymous(STG):
    """
    Removes the labels and draws each state as a filled circle.

    **arguments**:
        * *STG*: state transition graph

    **example**::

        >>> add_style_anonymous(stg)
    """
    
    STG.graph["node"]["shape"] = "circle"
    STG.graph["node"]["style"] = "filled"
    STG.graph["node"]["fillcolor"] = "lightgray"
    STG.graph["node"]["color"] = "none"
    
    for x in STG:
        STG.nodes[x]["label"] = ""


def successor_synchronous(Primes, State):
    """
    Returns the successor of *State* in the fully synchronous transition system defined by *Primes*.
    See :ref:`Klarner2015(b) <klarner2015approx>` Sec. 2.2 for a formal definition.

    **arguments**:
        * *Primes*: prime implicants
        * *State* (str/dict): a state

    **returns**:
        * *Successor* (dict): the synchronous successor of *State*

    **example**::
            >>> primes = {
            'v1': [[{'v2': 0}], [{'v2': 1}]],
            'v2': [[{'v3': 0}, {'v1': 0}], [{'v1': 1, 'v3': 1}]],
            'v3': [[{'v1': 1, 'v2': 0}], [{'v2': 1}, {'v1': 0}]]
            }
            >>> state = "100"
            >>> successor_synchronous(primes, state)
            {'v1': 0, 'v2': 0, 'v3': 0}
    """
    
    if type(State) == str:
        State = state2dict(Primes, State)
    
    successor = {}
    for name in Primes:
        stop = False
        for value in [0, 1]:
            if stop: break
            for prime in Primes[name][value]:
                if stop: break
                if all([State[d] == v for d, v in prime.items()]):
                    successor[name] = value
                    stop = True
    
    return successor


def successors_asynchronous(Primes, State):
    """
    Returns the successors of *State* in the fully asynchronous transition system defined by *Primes*.
    See :ref:`Klarner2015(b) <klarner2015approx>` Sec. 2.2 for a formal definition.

    **arguments**:
        * *Primes*: prime implicants
        * *State* (str/dict): a state

    **returns**:
        * *Successors* (list): the asynchronous successors of *State*

    **example**::
            >>> primes = {
            'v1': [[{'v2': 0}], [{'v2': 1}]],
            'v2': [[{'v3': 0}, {'v1': 0}], [{'v1': 1, 'v3': 1}]],
            'v3': [[{'v1': 1, 'v2': 0}], [{'v2': 1}, {'v1': 0}]]
            }
            >>> state = "101"
            >>> successors_asynchronous(primes, state)
            [{'v1': 0, 'v2': 0, 'v3': 1}, {'v1': 1, 'v2': 1, 'v3': 1}, {'v1': 1, 'v2': 0, 'v3': 0}]
    """
    
    if type(State) == str:
        State = state2dict(Primes, State)
    
    target = successor_synchronous(Primes, State)
    if target == State:
        return [target]
    
    successors = []
    for name in target:
        if State[name] != target[name]:
            successor = State.copy()
            successor[name] = target[name]
            successors.append(successor)
    
    return successors


def successors_mixed(Primes, State):
    """
    Returns the successors of *State* in the mixed transition system defined by *Primes*.
    The mixed update contains the synchronous and asynchronous STGs
    but it also allows transitions in which an arbitrary number of unstable components (but at least one) are updated.

    .. note::
        There are up to 2^n mixed successors for a state (n is the number of variables).

    **arguments**:
        * *Primes*: prime implicants
        * *State* (str/dict): a state

    **returns**:
        * *Successors* (list): the mixed successors of *State*

        **example**::
            >>> primes = {
            'v1': [[{'v2': 0}], [{'v2': 1}]],
            'v2': [[{'v3': 0}, {'v1': 0}], [{'v1': 1, 'v3': 1}]],
            'v3': [[{'v1': 1, 'v2': 0}], [{'v2': 1}, {'v1': 0}]]
            }
            >>> state = "010"
            >>> successors_mixed(primes, state)
            [{'v1': 1, 'v2': 1, 'v3': 0},
             {'v1': 0, 'v2': 0, 'v3': 0},
             {'v1': 0, 'v2': 1, 'v3': 1},
             {'v1': 1, 'v2': 0, 'v3': 0},
             {'v1': 1, 'v2': 1, 'v3': 1},
             {'v1': 0, 'v2': 0, 'v3': 1},
             {'v1': 1, 'v2': 0, 'v3': 1}]
    """
    if type(State) == str:
        State = state2dict(Primes, State)

    target = successor_synchronous(Primes, State)
    if target == State:
        return [target]

    successors = []

    diff = [x for x in target if target[x] != State[x]]
    # non empty powersets:
    combinations = itertools.chain.from_iterable(
        itertools.combinations(diff, r)
        for r in range(1, len(diff) + 1)
    )

    for combination in combinations:
        successor = State.copy()
        for name in combination:
            successor[name] = target[name]
        successors.append(successor)

    return successors


def random_successor_mixed(Primes, State):
    """
    Returns a random successor of *State* in the mixed transition system defined by *Primes*.
    The mixed update contains the synchronous and asynchronous STGs
    but it also allows transitions in which an arbitrary number of unstable components (but at least one) are updated.

    .. note::
        The reason why this function returns a random mixed transition rather than all mixed successors is that there are up to
        2^n mixed successors for a state (n is the number of variables).

    **arguments**:
        * *Primes*: prime implicants
        * *State* (str/dict): a state

    **returns**:
        * *Successor* (dict): a random successor of *State* using the mixed update

    **example**::

            >>> state = "100"
            >>> random_successor_mixed(primes, state)
            {'v1':1, 'v2':1, 'v3':1}
    """

    if type(State) == str:
        State = state2dict(Primes, State)

    target = successor_synchronous(Primes, State)
    if target == State:
        return target
    
    names = [x for x in target if target[x] != State[x]]
    k = random.randint(1, len(names))
    
    successor = State.copy()
    for name in random.sample(names, k):
        successor[name] = target[name]
    
    return successor


def random_state(primes: dict, subspace={}):
    """
    Generates a random state of the transition system defined by *Primes*.
    If *Subspace* is given then the state will be drawn from that subspace.

    **arguments**:
        * *Primes*: prime implicants
        * *Subspace* (str/dict): a subspace

    **returns**:
        * *State* (dict): random state inside *Subspace*

    **example**::

        >>> random_state(primes)
        {'v1':1, 'v2':1, 'v3':1}
        >>> random_state(primes, {"v1":0})
        {'v1':0, 'v2':1, 'v3':0}
        >>> random_state(primes, "0--")
        {'v1':0, 'v2':0, 'v3':1}
    """
    
    if type(subspace) == str:
        assert (len(subspace) == len(primes))
        x = {}
        for name, value in zip(sorted(primes), subspace):
            if value.isdigit():
                x[name] = int(value)
        subspace = x
    else:
        assert (set(subspace).issubset(set(primes)))
    
    items = list(subspace.items()) + [(x, random.choice([0, 1])) for x in primes if x not in subspace]
    
    return dict(items)


def random_walk(Primes, Update, InitialState, Length):
    """
    Returns a random walk of *Length* many states in the transition system defined by *Primes* and *Update*
    starting from a state defined by *InitialState*.
    If *InitialState* is a subspace then :ref:`random_state` will be used to draw a random state from inside it.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *InitialState* (str/dict): an initial state or subspace
        * *Length* (int): length of the random walk

    **returns**:
        * *Path* (list): sequence of states

    **example**::

        >>> path = random_walk(primes, "asynchronous", "11---0", 4)
    """
    
    assert (Update in UPDATE_STRATEGIES)
    
    if type(InitialState) == str:
        assert (len(InitialState) <= len(Primes))
        x = {}
        for name, value in zip(sorted(Primes), InitialState):
            if value.isdigit():
                x[name] = int(value)
        InitialState = x
    else:
        assert (set(InitialState).issubset(set(Primes)))
    
    if Update == 'asynchronous':
        transition = lambda current_state: random.choice(successors_asynchronous(Primes, current_state))
    
    elif Update == 'synchronous':
        transition = lambda current_state: successor_synchronous(Primes, current_state)
    
    else:
        # Update=='mixed':
        transition = lambda current_state: random_successor_mixed(Primes, current_state)
    
    x = random_state(Primes, subspace=InitialState)
    
    Path = [x]
    while len(Path) < Length:
        Path.append(transition(Path[-1]))
    
    return Path


def list_reachable_states(primes: dict, update: str, initial_states: List[str], memory: int, silent: bool = False) -> \
        List[str]:
    """
    Performs a depth-first search in the transition system defined by *primes* and *update* to list all states that
    are reachable from the *inital states*. *Memory* specifies the maximum number of states that can be kept in
    memory as "already explored" before the algorithm terminates.

    **arguments**:
        * *primes*: prime implicants
        * *update* (str): update strategy (either asynchronous or snchronous)
        * *initial_states* (list of str): a list of initial states
        * *memory* (int): maximal number of states memorized before search is stopped
        * *silent* (bool): print infos to screen

    **returns**:
        * *reachable_states* (list of str): a list of all states explored

    **example**::

            >>> initial_states = ["1000", "1001"]
            >>> update = "asynchronous"
            >>> memory = 1000
            >>> states = list_reachable_states(primes, update, initial_states, memory)
            >>> print(len(states))
            287
    """
    
    if not initial_states:
        return []
    
    assert type(initial_states) == list, "initial states must be a list"
    assert type(initial_states[0]) == str, "initial states must be in dict representation: {}".format(initial_states[0])
    assert update in ['asynchronous', 'synchronous']
    
    if update == 'asynchronous':
        transition_func = lambda state: successors_asynchronous(primes, state)
    else:
        transition_func = lambda state: [successor_synchronous(primes, state)]
    
    explored = set([])
    stack = set(initial_states)
    
    memory_reached = False
    counter = 0
    while stack:
        
        state = stack.pop()
        new_states = set([state2str(x) for x in transition_func(state)])
        not_explored = new_states.difference(explored)
        stack.update(not_explored)
        explored.add(state2str(state))
        counter += 1
        
        if len(explored) > memory:
            memory_reached = True
            break
    
    if not silent:
        print('states explored: {}'.format(counter))
        if memory_reached:
            print('result incomplete. stack size at termination: {} increase memory parameter'.format(len(stack)))
    
    return explored


def best_first_reachability(Primes, InitialSpace, GoalSpace, Memory=1000, Silent=False):
    """
    Performs a best-first search in the asynchronous transition system defined by *Primes* to answer the question whether there
    is a path from a random state in *InitalSpace* to a state in *GoalSpace*.
    *Memory* specifies the maximal number of states that can be kept in memory as "already explored" before the algorithm terminates.
    The search is guided by minimizing the Hamming distance between the current state of an incomplete path and the *GoalSpace*
    where variables that are free in *GoalSpace* are ignored.

    .. note::
        If the number of variables is less than 40 you should use LTL or CTL model checking to answer questions of reachability.
        :ref:`best_first_reachability` is meant for systems with more than 40 variables.
        If :ref:`best_first_reachability` returns *None* then that does not prove that there is no path between *InitialSpace* and *GoalSpace*.

    **arguments**:
        * *Primes*: prime implicants
        * *InitialSpace* (str/dict): initial subspace
        * *GoalSpace* (str/dict): goal subspace
        * *Memory* (int): maximal number of states memorized before search is stopped
        * *Silent* (bool): print infos to screen

    **returns**:
        * *Path* (list): a path from *InitalSpace* to *GoalSpace* if it was found, or *None* otherwise.

    **example**::

            >>> initspace = "1--0"
            >>> goalspace = "0--1"
            >>> path = best_first_reachability(primes, initialstate, goalspace)
            >>> if path: print(len(path))
            4
    """
    
    if type(InitialSpace) == str: InitialSpace = subspace2dict(Primes, InitialSpace)
    if type(GoalSpace) == str: GoalSpace = subspace2dict(Primes, GoalSpace)
    
    xdict = random_state(Primes, subspace=InitialSpace)
    x = state2str(xdict)
    
    fringe = []
    seen = set([])
    heapq.heappush(fringe, (hamming_distance(xdict, GoalSpace), [x]))
    seen.add(x)
    
    while fringe:
        dist, path = heapq.heappop(fringe)
        if dist == 0:
            return path
        
        x = path[-1]
        for ydict in successors_asynchronous(Primes, state2dict(Primes, x)):
            y = state2str(ydict)
            if y not in seen:
                seen.add(y)
                heapq.heappush(fringe, (hamming_distance(ydict, GoalSpace), path + [y]))
        
        if len(seen) > Memory:
            break
    
    if not Silent:
        print("best_first_reachability(..)")
        print(" explored %i transitions, no path found." % len(seen))


def state2str(State):
    """
    Converts the dictionary representation of a state into the string representation of a state.
    If *State* is already of type string it is simply returned.

    **arguments**
        * *State* (dict): dictionary representation of state

    **returns**
        * *State* (str): string representation of state

    **example**::

        >>> state = {"v2":0, "v1":1, "v3":1}
        >>> state2str(primes, state)
        '101'
    """
    
    if type(State) == str:
        return State
    
    return ''.join([str(State[x]) for x in sorted(State)])


def states2str(Primes, States):
    """
    Converts the string representation of a list of states into the dictionary representations.
    If *State* is already of type *dict* it is simply returned.

    **arguments**
        * *Primes*: prime implicants or a list of names
        * *States* (list of str): dictionary representation of states

    **returns**
        * *States* (list of dict): string representation of states

    **example**::

        >>> states = [{'v2':0, 'v1':1, 'v3':1},{'v2':0, 'v1':1, 'v3':0}]
        >>> states2str(primes, state)
        ["101", "100"]
    """
    
    return [state2dict(Primes, x) for x in States]


def state2dict(Primes, State):
    """
    Converts the string representation of a state into the dictionary representation of a state.
    If *State* is already of type *dict* it is simply returned.

    **arguments**
        * *Primes*: prime implicants or a list of names
        * *State* (str): string representation of state

    **returns**
        * *State* (dict): dictionary representation of state

    **example**::

        >>> state = "101"
        >>> state2dict(primes, state)
        {'v2':0, 'v1':1, 'v3':1}

    """
    
    if type(State) == dict:
        assert (set(State) == set(Primes))
        return State
    
    assert (len(State) == len(Primes))
    
    return dict((k, int(v)) for k, v in zip(sorted(Primes), State))


def states2dict(Primes, States):
    """
    Converts the string representation of a list of states into the dictionary representations.
    If *State* is already of type *dict* it is simply returned.

    **arguments**
        * *Primes*: prime implicants or a list of names
        * *States* (list of str): string representation of states

    **returns**
        * *States* (list of dict): dictionary representation of states

    **example**::

        >>> states = ["101", "100"]
        >>> states2dict(primes, state)
        [{'v2':0, 'v1':1, 'v3':1},{'v2':0, 'v1':1, 'v3':0}]
    """
    
    return [state2dict(Primes, x) for x in States]


def subspace2str(Primes, Subspace):
    """
    Converts the dictionary representation of a subspace into the string representation of a subspace.
    Uses "-" to indicate free variables.
    If *Subspace* is already of type *str* it is simply returned.

    **arguments**
        * *Primes*: prime implicants or a list of names
        * *Subspace* (dict): a subspace

    **returns**
        * *Subspace* (str): the string representation of *Subspace*

    **example**::

        >>> sub = {"v2":0, "v3":1}
        >>> subspace2str(primes, sub)
        '-01'
    """
    
    if type(Subspace) == str:
        assert (len(Subspace) == len(Primes))
        return Subspace
    
    assert (type(Subspace) == dict)
    assert (set(Subspace).issubset(set(Primes)))
    
    return ''.join([str(Subspace[x]) if x in Subspace else "-" for x in sorted(Primes)])


def subspace2dict(Primes, Subspace):
    """
    Converts the string representation of a subspace into the dictionary representation of a subspace.
    Use "-" to indicate free variables.
    If *Subspace* is already of type *dict* it is simply returned.

    **arguments**
        * *Primes*: prime implicants or a list of names
        * *Subspace* (str): a subspace

    **returns**
        * *Subspace* (dict): the dictionary representation of subspace

    **example**::

        >>> sub = "-01"
        >>> subspace2dict(primes, sub)
        {'v2':0, 'v3':1}
    """
    
    if type(Subspace) == dict:
        assert (set(Subspace).issubset(set(Primes)))
        return Subspace
    
    assert (type(Subspace) == str)
    assert (len(Subspace) == len(Primes))
    
    return dict([(name, int(value)) for name, value in zip(sorted(Primes), Subspace) if not value == "-"])


def list_states_in_subspace(Primes, Subspace):
    """
    Generates all states contained in *Subspace*.

    **arguments**:
        * *Primes*: prime implicants or a list of names
        * *Subspace* (str or dict): a subspace

    **returns**:
        * *States* (list of str): the states contained in *Subspace*

    **example**:

        >>> subspace = "1-1"
        >>> list_states_in_subspace(primes,subspace)
        ['101','111']
    """
    
    if type(Subspace) == str:
        Subspace = subspace2dict(Primes, Subspace)
    else:
        assert (type(Subspace) == dict)
        assert (set(Subspace).issubset(set(Primes)))
    
    ranges = [[Subspace[x]] if x in Subspace else [0, 1] for x in sorted(Primes)]
    
    states = []
    for values in itertools.product(*ranges):
        states.append("".join(map(str, values)))
    
    return states


def enumerate_states(Primes, Proposition):
    """
    Generates all states that are referenced by *Proposition* in the context of the variables given by *Primes*.
    The syntax of *Proposition* should be as in bnet files and TRUE and FALSE in will be treated as 1 and 0.

    .. note::
        This function uses :ref:`bnet2primes <bnet2primes>` and :ref:`list_states_in_subspace <list_states_in_subspace>` to enumerate
        the states referenced by an expression. The efficiency of this approach can decreases a lot starting from around 15 variables
        that appear in *Proposition*.

    **arguments**:
        * *Primes*: prime implicants
        * *Proposition* (str): a propositional formula

    **returns**:
        * *States* (list of str): the referenced states in str format

    **example**:

        >>> prop = "!Erk | (Raf & Mek)"
        >>> enumerate_states(primes,prop)[0]
        '010'
    """
    
    assert ("?" not in Primes)
    
    Proposition = Proposition.replace("TRUE", "1")
    Proposition = Proposition.replace("FALSE", "0")
    
    bnet = "?, %s" % Proposition
    newprimes = PyBoolNet.FileExchange.bnet2primes(bnet)
    
    states = set([])
    for p in newprimes["?"][1]:
        states.update(set(list_states_in_subspace(Primes, p)))
    
    return list(states)


def bounding_box(Primes, Subspaces):
    # not in the manual
    """
    returns the smallest subspaces that contains all *Subspaces*
    """
    
    names = sorted(Primes)
    seen = set([])
    result = {}
    
    for x in Subspaces:
        if type(x) == str:
            assert (len(x) == len(names))
            x = dict(zip(names, map(int, x)))
        
        for name in x:
            if name in seen:
                continue
            
            if name in result:
                if result[name] != x[name]:
                    seen.add(name)
                    result.pop(name)
            else:
                result[name] = x[name]
    
    return result


def hamming_distance(Subspace1, Subspace2):
    """
    Returns the Hamming distance between to subspaces.
    Variables that are free in either subspace are ignored.

    **arguments**:
        * *Subspace1, Subspace2* (dict): subspaces in dictionary representation

    **returns**:
        * *Distance* (int): the distance between *Subspace1* and *Subspace2*

    **example**:

        >>> hamming_distance({"v1":0,"v2":0}, {"v1":1,"v2":1})
        2
        >>> hamming_distance({"v1":1}, {"v2":0})
        0
    """
    
    return len([k for k, v in Subspace1.items() if k in Subspace2 and Subspace2[k] != v])


VAN_HAM_EXTENSIONS = {3: ["_medium", "_high"],
                      4: ["_level1", "_level2", "_level3"],
                      5: ["_level1", "_level2", "_level3", "_level4"]}


def find_vanham_variables(Primes):
    """
    Detects variables that represent multi-valued variables using the Van Ham encoding, see :ref:`Didier2011` for more details.
    E.g. three-valued variables x are encoded via two Boolean variables x_medium and x_high.
    This function is used for example by :ref:`ModelChecking.primes2smv <primes2smv>` to add
    INIT constraints to the smv file that forbid all states that are not admissible, e.g. in which "!x_medium & x_high" is true.

    **arguments**:
        * *Primes*: prime implicants

    **returns**:
        * *Names* (dict): activity levels and names

    **example**::

        >>> find_vanham_variables(primes)
        {2: ['E2F1', 'ATM'],
         3: ['ERK'],
         4: [],
         5: []}
    """
    
    seen_base = []
    seen_names = []
    vanham = {}
    
    for val in sorted(VAN_HAM_EXTENSIONS, reverse=True):
        post = VAN_HAM_EXTENSIONS[val][0]
        base = [x.replace(post, "") for x in Primes if x.endswith(post)]  # possible base names
        base = [x for x in base if not x in seen_base]  # base already seen for larger val
        base = [x for x in base if all(x + y in Primes for y in VAN_HAM_EXTENSIONS[val])]  # bingo
        names = [x + y for x in base for y in VAN_HAM_EXTENSIONS[val]]
        
        vanham[val] = sorted(base)
        seen_base.extend(base)
        seen_names.extend(names)
    
    vanham[2] = sorted(x for x in Primes if not x in seen_names)
    
    return vanham


def size_state_space(Primes, VanHam=True, FixedInputs=False):
    """
    This function computes the number of states in states space of *Primes*.
    Detects if there are variables that encode multi-valued variables via the Van Ham encoding.
    Variables that have the same name module the Van Ham extension (see example below) are identified.
    E.g. the state space of x_medium, x_high is 3 instead of 4 since "!x_medium & x_high" is not an admissible state, see :ref:`Didier2011` for more details.


    **arguments**:
        * *Primes*: prime implicants
        * *VanHam* (bool): exclude states that are not admissible in Van Ham encoding
        * *FixedInputs* (bool): return number of states for single input combination

    **returns**:
        * *Size* (int): number of states

    **example**::

        >>> StateTransitionGraphs.VAN_HAM_EXTENSIONS
        ["_medium", "_high", "_level1", "_level2", "_level3", "_level4", "_level5"]
        >>> size_state_space(primes, VanHam=False)
        256
        >>> size_state_space(primes)
        192
        >>> size_state_space(primes, FixedInputs=True)
        96
    """
    
    if VanHam:
        vanham = find_vanham_variables(Primes)
        
        size = 1
        for x in vanham:
            size *= x ** (len(vanham[x]))
    else:
        size = 2 ** len(Primes)
    
    if FixedInputs:
        factor = 2 ** len(PyBoolNet.PrimeImplicants.find_inputs(Primes))
        size = size / factor
    
    return size


################ The Strongly Connected Component Graph (SCC Graph) ################


def stg2sccgraph(STG):
    """
    Computes the SCC graph of the *STG*. For a definition see Sec. 3.1 of :ref:`Tournier2009 <Tournier2009>`.

    **arguments**:
        * *STG*: state transition graph

    **returns**:
        * *SCCGraph* (networkx.DiGraph): the SCC graph of *STG*

    **example**:

        >>> sccgraph = stg2sccgraph(stg)
    """
    
    graph = PyBoolNet.Utility.DiGraphs.digraph2sccgraph(STG)
    graph.graph["node"] = {"color": "none", "style": "filled", "shape": "rect"}
    
    for node in graph.nodes():
        lines = [",".join(x) for x in PyBoolNet.Utility.Misc.divide_list_into_similar_length_lists(node)]
        graph.nodes[node]["label"] = "<%s>" % ",<br/>".join(lines)
        if len(node) > 1 or STG.has_edge(node[0], node[0]):
            graph.nodes[node]["fillcolor"] = "lightgray"
    
    return graph


def sccgraph2dot(SCCGraph, FnameDOT=None):
    """
    Creates a *dot* file from a SCC graph.

    **arguments**:
        * *SCCGraph*: state transition graph
        * *FnameDOT* (str): name of *dot* file or *None*

    **returns**:
        * *FileDOT* (str): file as string if not *FnameDOT==None*, otherwise it returns *None*


    **example**::

          >>> sccgraph2dot(sccg, "sccgraph.dot")
    """
    
    graph = SCCGraph.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    return PyBoolNet.Utility.DiGraphs.digraph2dot(graph, FnameDOT)


def sccgraph2image(SCCGraph, FnameIMAGE, LayoutEngine="dot", Silent=False):
    """
    Creates an image file from a SCC graph.

    **arguments**:
        * *SCCGraph*: SCC graph
        * *FnameIMAGE* (str): name of output file
        * *LayoutEngine*: one of "dot", "neato", "fdp", "sfdp", "circo", "twopi"
        * *Silent* (bool): print infos to screen

    **example**::

          >>> sccgraph2image(sccgraph, "mapk_sccgraph.pdf")
    """
    
    graph = SCCGraph.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    PyBoolNet.Utility.DiGraphs.digraph2image(graph, FnameIMAGE, LayoutEngine, Silent)


################ The Condensation Graph ################


def stg2condensationgraph(STG):
    """
    Converts the *STG* into the condensation graph, for a definition see :ref:`Klarner2015(b) <klarner2015approx>`.

    **arguments**:
        * *STG*: state transition graph

    **returns**:
        * *CGraph* (networkx.DiGraph): the condensation graph of *STG*

    **example**::

        >>> cgraph = stg2condensationgraph(stg)
    """
    
    graph = PyBoolNet.Utility.DiGraphs.digraph2condensationgraph(STG)
    graph.graph["node"] = {"color": "none", "style": "filled", "fillcolor": "lightgray", "shape": "rect"}
    
    for node in graph.nodes():
        lines = [",".join(x) for x in PyBoolNet.Utility.Misc.divide_list_into_similar_length_lists(node)]
        graph.nodes[node]["label"] = "<%s>" % ",<br/>".join(lines)
    
    return graph


def condensationgraph2dot(CGraph, FnameDOT=None):
    """
    Creates a *dot* file from a condensation graph.

    **arguments**:
        * *CGraph*: state transition graph
        * *FnameDOT* (str): name of *dot* file or *None*

    **returns**:
        * *FileDOT* (str): file as string if not *FnameDOT==None*, otherwise it returns *None*

    **example**::

          >>> condensationgraph2dot(cgraph, "mapk_cgraph.dot")
    """
    
    graph = CGraph.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    return PyBoolNet.Utility.DiGraphs.digraph2dot(graph, FnameDOT)


def condensationgraph2image(CGraph, FnameIMAGE, LayoutEngine="dot", Silent=False):
    """
    Creates an image file from the condensation graph.

    **arguments**:
        * *CGraph*: condensation graph
        * *FnameIMAGE* (str): name of output file
        * *LayoutEngine*: one of "dot", "neato", "fdp", "sfdp", "circo", "twopi"
        * *Silent* (bool): print infos to screen

    **example**::

          >>> condensationgraph2image(cgraph, "dot", "mapk_cgraph.pdf")
    """
    
    graph = CGraph.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    PyBoolNet.Utility.DiGraphs.digraph2image(graph, FnameIMAGE, LayoutEngine, Silent)


################ The Hierarchical Transition Graph (HTG) ################

def stg2htg(STG):
    """
    Computes the HTG of the *STG*. For a definition see :ref:`Berenguier2013 <Berenguier2013>`.

    **arguments**:
        * *STG*: state transition graph

    **returns**:
        * *HTG* (networkx.DiGraph): the HTG of *STG*

    **example**::

        >>> htg = stg2htg(stg)
    """
    
    graph = networkx.DiGraph()
    graph.graph["node"] = {"color": "none"}
    
    sccs = []
    cascades = []
    attractors = []
    for x in networkx.strongly_connected_components(STG):
        x = tuple(sorted(x))
        if len(x) > 1 or STG.has_edge(x[0], x[0]):
            sccs.append(x)
            suc = PyBoolNet.Utility.DiGraphs.successors(STG, x)
            if set(suc) == set(x):
                attractors.append(x)
        else:
            cascades += x
    
    graph.add_nodes_from(sccs, style="filled", fillcolor="lightgray", shape="rect")
    
    sigma = {}
    for x in cascades:
        pattern = []
        for i, A in enumerate(sccs):
            if PyBoolNet.Utility.DiGraphs.has_path(STG, x, A):
                pattern.append(i)
        pattern = tuple(pattern)
        
        if not pattern in sigma:
            sigma[pattern] = []
        sigma[pattern].append(x)
    
    I = [tuple(sorted(x)) for x in sigma.values()]
    graph.add_nodes_from(I)
    
    for X in graph.nodes():
        for Y in graph.nodes():
            if X == Y: continue
            
            if PyBoolNet.Utility.DiGraphs.has_edge(STG, X, Y):
                graph.add_edge(X, Y)
    
    for node in graph.nodes():
        lines = [",".join(x) for x in PyBoolNet.Utility.Misc.divide_list_into_similar_length_lists(node)]
        graph.nodes[node]["label"] = "<%s>" % ",<br/>".join(lines)
    
    return graph


def htg2dot(HTG, FnameDOT=None):
    """
    Creates a *dot* file of the *HTG*.

    **arguments**:
        * *HTG*: HTG
        * *FnameDOT* (str): name of *dot* file or *None*

    **returns**:
        * *FileDOT* (str): file as string if not *FnameDOT==None*, otherwise it returns *None*

    **example**::

          >>> htg2dot(cgraph, "mapk_htg.dot")
    """
    
    graph = HTG.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    return PyBoolNet.Utility.DiGraphs.digraph2dot(graph, FnameDOT)


def htg2image(HTG, FnameIMAGE, LayoutEngine="dot", Silent=False):
    """
    Creates an image file from the *HTG*.

    **arguments**:
        * *HTG*: HTG
        * *FnameIMAGE* (str): name of output file
        * *LayoutEngine*: one of "dot", "neato", "fdp", "sfdp", "circo", "twopi"
        * *Silent* (bool): print infos to screen

    **example**::

          >>> htg2image(cgraph, "mapk_htg.pdf")
    """
    
    graph = HTG.copy()
    PyBoolNet.Utility.DiGraphs.convert_nodes_to_anonymous_strings(graph)
    PyBoolNet.Utility.DiGraphs.digraph2image(graph, FnameIMAGE, LayoutEngine, Silent)


################ Operations on State Space ################

def state_is_in_subspace(Primes, State, Subspace):
    """
    Checks whether *State* is a state in *Subspace*.

    **arguments**:
        * *Primes*: prime implicants
        * *State* (str/dict): a state
        * *Subspace* (str/dict): a subspace

    **returns**:
        * *Answer* (bool): whether *State* is a state in *Subspace*

    **example**::

          >>> state_is_in_subspace(Primes, State, Subspace)
          False
    """
    
    if type(State) == str:
        State = state2dict(Primes, State)
    if type(Subspace) == str:
        Subspace = subspace2dict(Primes, Subspace)
    
    for k in Subspace:
        if State[k] != Subspace[k]:
            return False
    
    return True


def A_is_subspace_of_B(Primes, A, B):
    """
    todo: add unit tests

    Checks whether *A* is a subspace of *B*.

      **arguments**:
        * *Primes*: prime implicants
        * *A*, *B* (str / dict): subspaces in str or dict format

      **returns**:
        * *Answer* (bool)

      **example**::

        >>> A_is_subspace_of_B(primes, sub1, sub2)
        True
    """
    
    if type(A) == str:
        A = subspace2dict(Primes, A)
    if type(B) == str:
        B = subspace2dict(Primes, B)
    
    return set(A.items()).issuperset(set(B.items()))
