

from __future__ import print_function

import datetime
import itertools
import random

import PyBoolNet.FileExchange
import PyBoolNet.PrimeImplicants
import PyBoolNet.StateTransitionGraphs
import PyBoolNet.AspSolver
import PyBoolNet.InteractionGraphs
import PyBoolNet.ModelChecking
import PyBoolNet.TemporalLogic
import PyBoolNet.Utility


def compute_json(Primes, Update, FnameJson=None, CheckCompleteness=True, CheckFaithfulness=True, CheckUnivocality=True, Silent=False):
    """
    todo: add unit tests

    Computes the attractors object.

    structure of attractor object:
        primes: dict
        update: str
        is_complete: str

        attractors: (tuple)
            is_steady: bool
            is_cyclic: bool
            state:
                str: state string
                dict: state dict
                prop: state proposition
            mintrapspace:
                str: subspace string
                dict: subspace dict
                prop: subspace proposition
                is_univocal: str
                is_faithful: str


    example:
        "primes": {..}
        "update": "asynchronous"
        "is_complete": "yes"
        "attractors": (tuple)
            "is_steady": False
            "is_cyclic": True
            "state":
                "str": "001101"
                "dict": {..}
                "prop": "!v0&!v1..."
            "mintrapspace":
                "str": "00---1"
                "dict": {..}
                "prop": "!v0&!v1..."
                "is_univocal": "unknown"
                "is_faithful": "no"


    **arguments**:
      * *Primes*: prime implicants
      * *Update* (str): description
      * *FnameJson* (str): description
      * *CheckCompleteness* (bool): description
      * *CheckFaithfulness* (bool): description
      * *CheckUnivocality* (bool): description
      * *Silent* (bool): print infos to screen

    **returns**:
        * *AttrJson* (dict): json attractor data

    **example**::

      >>> attrs = compute_json(primes, update, "attrs.json")
      created attrs.json
    """

    assert(Update in PyBoolNet.StateTransitionGraphs.UPDATE_STRATEGIES)
    assert(Primes)

    if not Silent: print("Attractors.compute_json(..)")

    attrs = {}
    attrs["primes"] = PyBoolNet.PrimeImplicants.copy(Primes)
    attrs["update"] = Update

    mintspaces = PyBoolNet.AspSolver.trap_spaces(Primes, "min")

    if CheckCompleteness:
        if not Silent: print(" Attractors.completeness(..)", end="")
        if completeness(Primes, Update):
            attrs["is_complete"] = "yes"
        else:
            attrs["is_complete"] = "no"
        if not Silent: print(" {x}".format(x=attrs["is_complete"]))
    else:
        attrs["is_complete"] = "unknown"


    attrs["attractors"] = []

    for i,mints in enumerate(mintspaces):

        mints_obj = {} # minimal trap space object
        mints_obj["str"] = PyBoolNet.StateTransitionGraphs.subspace2str(Primes, mints)
        mints_obj["dict"] = mints
        mints_obj["prop"] = PyBoolNet.TemporalLogic.subspace2proposition(Primes, mints)

        if not Silent: print(" working on minimal trapspace {i}/{n}: {m}".format(i=i+1, n=len(mintspaces), m=mints_obj["str"]))

        if CheckUnivocality:
            if not Silent: print("  Attractors.univocality(..)", end="")
            if univocality(Primes, Update, mints):
                mints_obj["is_univocal"] = "yes"
            else:
                mints_obj["is_univocal"] = "no"
            if not Silent: print(" {x}".format(x=mints_obj["is_univocal"]))
        else:
            mints_obj["is_univocal"] = "unknown"

        if CheckFaithfulness:
            if not Silent: print("  Attractors.faithfulness(..)", end="")
            if faithfulness(Primes, Update, mints):
                mints_obj["is_faithful"] = "yes"
            else:
                mints_obj["is_faithful"] = "no"
            if not Silent: print(" {x}".format(x=mints_obj["is_faithful"]))
        else:
            mints_obj["is_faithful"] = "unknown"

        if not Silent: print("  Attractors.find_attractor_state_by_randomwalk_and_ctl(..)")
        state = find_attractor_state_by_randomwalk_and_ctl(Primes, Update, InitialState=mints)

        state_obj = {} # attractor state object
        state_obj["str"] = PyBoolNet.StateTransitionGraphs.state2str(state)
        state_obj["dict"] = state
        state_obj["prop"] = PyBoolNet.TemporalLogic.subspace2proposition(Primes, state)

        attractor_obj = {}
        attractor_obj["mintrapspace"] = mints_obj
        attractor_obj["state"] = state_obj
        attractor_obj["is_steady"] = len(mints)==len(Primes)
        attractor_obj["is_cyclic"] = len(mints)!=len(Primes)

        attrs["attractors"].append(attractor_obj)

    attrs["attractors"] = tuple(sorted(attrs["attractors"], key=lambda x: x["state"]["str"]))

    if FnameJson:
        save_json(attrs, FnameJson, Silent)

    return attrs


def save_json(AttrJson, FnameJson, Silent=False):
    """
    todo: add unit tests

    saves the attractor object as a JSON file.

    **arguments**:
        * *AttrJson* (dict): json attractor data, see :ref:`attractors_compute_json`
        * *FnameJson* (str): file name

    **returns**:
        * *None*

    **example**::

        >>> save_attractor(attrs, "attrs.json")
        created attrs.json
    """

    PyBoolNet.Utility.Misc.save_json_data(AttrJson, FnameJson, Silent=Silent)


def open_json(Fname):
    """
    todo: add unit tests

    opens the attractor object, see todo: add :ref:`xxx`

    **arguments**:
        * *Fname* (str): file name

    **returns**:
        * *AttrJson* (dict): json attractor data, see :ref:`attractors_compute_json`

    **example**::

        >>> attrs = open_attractor("attrs.json")
    """

    attrs = PyBoolNet.Utility.Misc.open_json_data(Fname)

    return attrs


def find_attractor_state_by_randomwalk_and_ctl(Primes, Update, InitialState={}, Length=0, Attempts=10, Silent=True):
    """
    Attempts to find a state inside an attractor by the "long random walk" method,
    see :ref:`Klarner2015(b) <klarner2015approx>` Sec. 3.2 for a formal definition.
    The method generates a random walk of *Length* many states, starting from a state defined by *InitialState*.
    If *InitialState* is a subspace then :ref:`random_state` will be used to draw a random state from inside it.
    The function then uses CTL model checking, i.e., :ref:`check_primes <check_primes>`,
    to decide whether the last state of the random walk is inside an attractor.
    If so it is returned, otherwise the process is repeated.
    If no attractor state has been found after *Attempts* many trials an exception is raised.

    .. note::
        The default value for length, namely *Length=0*, will be replaced by::

            Length = 10*len(Primes)

        which proved sufficiently large in our computer experiments.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str):  the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *InitialState* (str / dict): an initial state or subspace
        * *Length* (int): length of random walk
        * *Attempts* (int): number of attempts before exception is raised
        * *Silent* (bool): print infos to screen

    **returns**:
        * *State* (dict): a state that belongs to some attractor
        * raises *Exception* if no attractor state is found

    **example**::

            >>> find_attractor_state_by_randomwalk_and_ctl(primes, "asynchronous")
            {'v1':1, 'v2':1, 'v3':1}
    """

    if type(InitialState) == str:
        InitialState = PyBoolNet.StateTransitionGraphs.state2dict(Primes=Primes, State=InitialState)

    assert(Update in PyBoolNet.StateTransitionGraphs.UPDATE_STRATEGIES)
    assert(set(InitialState).issubset(set(Primes)))

    # length heuristic
    if Length==0:
        Length = 10*len(Primes)

    # transition function
    if Update=='asynchronous':
        transition = lambda current_state: random.choice(PyBoolNet.StateTransitionGraphs.successors_asynchronous(Primes,current_state))

    elif Update=='synchronous':
        transition = lambda current_state: PyBoolNet.StateTransitionGraphs.successor_synchronous(Primes,current_state)

    elif Update=='mixed':
        transition = lambda current_state: PyBoolNet.StateTransitionGraphs.random_successor_mixed(Primes,current_state)

    if not Silent:
        print("find_attractor_state_by_randomwalk_and_ctl(..)")
        print(" len(Primes)={n}, Update={u}, Length={l}, Attempts={a}".format(n=len(Primes), u=Update, l=Length, a=Attempts))

    trials = 0
    while trials < Attempts:
        if not Silent: print(" trial {i}".format(i=trials))

        current_state = PyBoolNet.StateTransitionGraphs.random_state(Primes, InitialState)
        if not Silent: print("  start: {x}".format(x=PyBoolNet.StateTransitionGraphs.state2str(current_state)))

        transitions = 0
        while transitions < Length:
            current_state = transition(current_state)
            transitions+=1

        if not Silent: print("  end:   {x}".format(x=PyBoolNet.StateTransitionGraphs.state2str(current_state)))

        spec = 'CTLSPEC ' + PyBoolNet.TemporalLogic.AGEF_oneof_subspaces(Primes, [current_state])
        init = 'INIT ' + PyBoolNet.TemporalLogic.subspace2proposition(Primes, current_state)

        # todo: remove. this is just for debugging
        # PyBoolNet.ModelChecking.primes2smv(Primes, Update, init, spec, FnameSMV="randomwalk.smv")
        # return

        if PyBoolNet.ModelChecking.check_primes(Primes, Update, init, spec):
            if not Silent: print("  is attractor state")

            return current_state

        trials+=1


    if not Silent:
        print(" could not find attractor state.")
        print(" increase Length or Attempts parameter.")

    raise Exception


def univocality(Primes, Update, Trapspace):
    """
    The model checking and random-walk-based method for deciding whether *Trapspace* is univocal,
    i.e., whether there is a unique attractor contained in it,
    in the state transition graph defined by *Primes* and *Update*.
    The approach is described and discussed in :ref:`Klarner2015(a) <klarner2015trap>`.
    The function performs two steps: first it searches for a state that belongs to an attractor inside of *Trapspace* using
    the random-walk-approach and the function :ref:`random_walk <random_walk>`,
    then it uses CTL model checking, specifically the pattern :ref:`AGEF_oneof_subspaces <AGEF_oneof_subspaces>`,
    to decide if the attractor is unique inside *Trapspace*.

    .. note::
        In the (very unlikely) case that the random walk does not end in an attractor state an exception will be raised.

    .. note::
        Univocality depends on the update strategy, i.e.,
        a trapspace may be univocal in the synchronous STG but not univocal in the asynchronous STG or vice versa.

    .. note::
        A typical use case is to decide whether a minimal trap space is univocal.

    .. note::
        *Trapspace* is in fact not required to be a trap set, i.e., it may be an arbitrary subspace.
        If it is an arbitrary subspace then the involved variables are artificially fixed to be constant.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspace* (str / dict): a subspace

    **returns**:
        * *Answer* (bool): whether *Trapspace* is univocal in the STG defined by *Primes* and *Update*

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> x = mintrapspaces[0]
        >>> univocality(primes, "asynchronous", x)
        True
    """

    if type(Trapspace)==str:
        Trapspace=StateTransitionGraphs.str2subspace(Primes, Trapspace)

    # percolation
    primes = PyBoolNet.PrimeImplicants.copy(Primes)
    PyBoolNet.PrimeImplicants.create_constants(primes, Constants=Trapspace)
    PyBoolNet.PrimeImplicants.percolate_and_remove_constants(primes)

    # trivial case: unique steady state
    if primes == {}:
        return True

    # find attractor state
    attractor_state1 = find_attractor_state_by_randomwalk_and_ctl(primes, Update)

    # univocality
    spec = 'CTLSPEC ' + PyBoolNet.TemporalLogic.EF_oneof_subspaces(primes, [attractor_state1])
    init = 'INIT TRUE'
    answer = PyBoolNet.ModelChecking.check_primes(primes, Update, init, spec)

    return answer


def faithfulness(Primes, Update, Trapspace):
    """
    The model checking approach for deciding whether *Trapspace* is faithful,
    i.e., whether all free variables oscillate in all of the attractors contained in it,
    in the state transition graph defined by *Primes* and *Update*.
    The approach is described and discussed in :ref:`Klarner2015(a) <klarner2015trap>`.
    It is decided by a single CTL query of the pattern :ref:`EF_all_unsteady <EF_all_unsteady>`
    and the random-walk-approach of the function :ref:`random_walk <random_walk>`.

    .. note::
        In the (very unlikely) case that the random walk does not end in an attractor state an exception will be raised.

    .. note::
        Faithfulness depends on the update strategy, i.e.,
        a trapspace may be faithful in the synchronous STG but not faithful in the asynchronous STG or vice versa.

    .. note::
        A typical use case is to decide whether a minimal trap space is faithful.

    .. note::
        *Trapspace* is in fact not required to be a trap set, i.e., it may be an arbitrary subspace.
        If it is an arbitrary subspace then the involved variables are artificially fixed to be constant.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspace* (str / dict): a subspace

    **returns**:
        * *Answer* (bool): whether *Trapspace* is faithful in the STG defined by *Primes* and *Update*

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> x = mintspaces[0]
        >>> faithfulness(primes, x)
        True
    """

    if type(Trapspace)==str:
        Trapspace=StateTransitionGraphs.str2subspace(Primes, Trapspace)

    # trivial case: steady state
    if len(Trapspace)==len(Primes):
        return True

    # percolation
    primes = PyBoolNet.PrimeImplicants.copy(Primes)
    PyBoolNet.PrimeImplicants.create_constants(primes, Constants=Trapspace)
    constants  = PyBoolNet.PrimeImplicants.percolate_and_remove_constants(primes)

    # trivial case: free variables fix due to percolation
    if len(constants)>len(Trapspace):
        return False

    # faithfulness
    spec = 'CTLSPEC AG(%s)'%PyBoolNet.TemporalLogic.EF_unsteady_states(primes)
    init = 'INIT TRUE'
    answer = PyBoolNet.ModelChecking.check_primes(primes, Update, init, spec)

    return answer


def completeness(Primes, Update):
    """
    The ASP and CTL model checking based algorithm for deciding whether the minimal trap spaces of a network are complete.
    The algorithm is discussed in :ref:`Klarner2015(a) <klarner2015trap>`.
    It splits the problem of deciding completeness into smaller subproblems by searching for so-called autonomous sets in the
    interaction graph of the network.
    If the minimal trap spaces of the corresponding restricted networks are complete
    then each of them defines a network reduction that is in turn subjected to a search for autonomous sets.
    The efficiency of the algorithm depends on the existence of small autonomous sets in the interaction graph, i.e.,
    the existence of "hierarchies" rather than a single connected component.

    .. note::
        Completeness depends on the update strategy, i.e.,
        the minimal trap spaces may be complete in the synchronous STG but not complete in the asynchronous STG or vice versa.

    .. note::
        The algorithm returns a counterexample, i.e., a state from which there is no path to one of the minimal trap spaces,
        if the minimal trap spaces are not complete.

    .. note::
        Each line that corresponds to a line of the pseudo code of Figure 3 in :ref:`Klarner2015(a) <klarner2015trap>` is marked by a comment.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*

    **returns**:
        * *Answer* (bool): whether *Subspaces* is complete in the STG defined by *Primes* and *Update*,

    **example**::

            >>> completeness(primes, "asynchronous")
            False
    """

    return _iterative_completeness_algorithm(Primes, Update, ComputeCounterexample=False)


def univocality_with_counterexample(Primes, Update, Trapspace):
    """
    Performs the same steps as :ref:`univocality` but also returns a counterexample which is *None* if it does not exist.
    A counterexample of a univocality test are two states that belong to different attractors.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspace* (str / dict): a subspace

    **returns**:
        * *Answer* (bool): whether *Trapspace* is univocal in the STG defined by *Primes* and *Update*
        * *CounterExample* (dict): two states that belong to different attractors or *None* if no counterexample exists

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> trapspace = mintrapspaces[0]
        >>> answer, counterex = univocality_with_counterexample(primes, trapspace, "asynchronous")
    """

    if type(Trapspace)==str:
        Trapspace=StateTransitionGraphs.str2subspace(Primes, Trapspace)

    # percolation
    primes = PyBoolNet.PrimeImplicants.copy(Primes)
    PyBoolNet.PrimeImplicants.create_constants(primes, Constants=Trapspace)
    constants  = PyBoolNet.PrimeImplicants.percolate_and_remove_constants(primes)

    # trivial case: constants = unique steady state
    if primes == {}:
        return True, None

    # find attractor state
    attractor_state1 = find_attractor_state_by_randomwalk_and_ctl(primes, Update)

    # univocality
    spec = 'CTLSPEC ' + PyBoolNet.TemporalLogic.EF_oneof_subspaces(primes, [attractor_state1])
    init = 'INIT TRUE'
    answer, counterex = PyBoolNet.ModelChecking.check_primes_with_counterexample(primes, Update, init, spec)

    # success
    if answer:
        return True, None

    # failure
    else:
        attractor_state2 = find_attractor_state_by_randomwalk_and_ctl(primes, Update, counterex[-1])

        # need to add constants to get original states
        attractor_state2 = PyBoolNet.Utility.Misc.merge_dicts([attractor_state2,constants])
        attractor_state1 = PyBoolNet.Utility.Misc.merge_dicts([attractor_state1,constants])
        counterex = attractor_state1, attractor_state2

        return False, counterex


def faithfulness_with_counterexample(Primes, Update, Trapspace):
    """
    Performs the same steps as :ref:`faithfulness` but also returns a counterexample which is *None* if it does not exist.
    A counterexample of a faithful test is a state that belongs to an attractor which has more fixed variables than there are in *Trapspace*.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspace* (str / dict): a subspace

    **returns**:
        * *Answer* (bool): whether *Trapspace* is faithful in the STG defined by *Primes* and *Update*
        * *CounterExample* (dict): a state that belongs to an attractor that does not oscillate in all free variables or *None* if no counterexample exists

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> x = mintspaces[0]
        >>> faithfulness(primes, x)
        True
    """

    if type(Trapspace)==str:
        Trapspace=StateTransitionGraphs.str2subspace(Primes, Trapspace)

    # trivial case: steady state
    if len(Trapspace)==len(Primes):
        return True, None

    # percolation
    primes = PyBoolNet.PrimeImplicants.copy(Primes)
    PyBoolNet.PrimeImplicants.create_constants(primes, Constants=Trapspace)
    constants  = PyBoolNet.PrimeImplicants.percolate_and_remove_constants(primes)

    # trivial case: free variables fix due to percolation
    if len(constants)>len(Trapspace):
        counterex = find_attractor_state_by_randomwalk_and_ctl(primes, Update)
        attractor_state = PyBoolNet.Utility.Misc.merge_dicts([counterex, constants])

        return False, attractor_state

    # faithfulness
    spec = 'CTLSPEC AG(%s)'%PyBoolNet.TemporalLogic.EF_unsteady_states(primes)
    init = 'INIT TRUE'
    answer, counterex = PyBoolNet.ModelChecking.check_primes_with_counterexample(primes, Update, init, spec)

    # success
    if answer:
        return True, None

    # failure
    else:
        attractor_state = find_attractor_state_by_randomwalk_and_ctl(primes, Update, counterex[-1])
        attractor_state = PyBoolNet.Utility.Misc.merge_dicts([attractor_state, constants])

        return False, attractor_state


def completeness_with_counterexample(Primes, Update):
    """
    Performs the same steps as :ref:`completeness` but also returns a counterexample which is *None* if it does not exist.
    A counterexample of a completeness test is a state that can not reach one of the minimal trap spaces of *Primes*.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*

    **returns**:
        * *Answer* (bool): whether *Subspaces* is complete in the STG defined by *Primes* and *Update*,
        * *Counterexample* (dict): a state that can not reach one of the minimal trap spaces of *Primes* or *None* if no counterexample exists

    **example**::

            >>> answer, counterex = completeness_with_counterexample(primes, "asynchronous")
            >>> answer
            False
            >>> STGs.state2str(counterex)
            10010111101010100001100001011011111111
    """

    return _iterative_completeness_algorithm(Primes, Update, ComputeCounterexample=True)


def _iterative_completeness_algorithm(Primes, Update, ComputeCounterexample):
    """
    The iterative algorithm for deciding whether the minimal trap spaces are complete.
    The function is implemented by line-by-line following of the pseudo code algorithm given in
    "Approximating attractors of Boolean networks by iterative CTL model checking", Klarner and Siebert 2015. todo: add :ref:``

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *ComputeCounterexample* (bool): whether to compute a counterexample

    **returns**:
        * *Answer* (bool): whether *Subspaces* is complete in the STG defined by *Primes* and *Update*,
        * *Counterexample* (dict): a state that can not reach one of the minimal trap spaces of *Primes* or *None* if no counterexample exists

    **example**::

            >>> answer, counterex = completeness_with_counterexample(primes, "asynchronous")
            >>> answer
            False
            >>> STGs.state2str(counterex)
            10010111101010100001100001011011111111
    """

    primes = PyBoolNet.PrimeImplicants.copy(Primes)

    constants_global = PyBoolNet.PrimeImplicants.percolate_and_remove_constants(primes)

    mintrapspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")   # line  1
    if mintrapspaces==[{}]:             # line  2
        if ComputeCounterexample:
            return (True, None)
        else:
            return True                 # line  3

    currentset = [({}, set([]))]        # line  4
    while currentset:                   # line  5
        p, W = currentset.pop()         # line  6 (p are constatns, W are variables already seen in search for minimal autonomous sets)

        ## line 7: primes_reduced = ReducedNetwork(V,F,p)
        primes_reduced = PyBoolNet.PrimeImplicants.copy(primes)
        PyBoolNet.PrimeImplicants.create_constants(primes_reduced, Constants=p)

        ## line 8: cgraph = CondensationGraph(V_p,F_p)
        igraph = PyBoolNet.InteractionGraphs.primes2igraph(primes_reduced)
        cgraph = PyBoolNet.Utility.DiGraphs.digraph2condensationgraph(igraph)


        ## line 9: cgraph_dash = RemoveComponents(Z,->,W)
        cgraph_dash = cgraph.copy()
        for U in cgraph.nodes():
            if set(U).issubset(set(W)):
                cgraph_dash.remove_node(U)

        ## line 10: W_dash = Copy(W)
        W_dash = W.copy()

        ## line 11
        refinement  = []

        ## line 12: toplayer = TopLayer(Z',->)
        toplayer = [U for U in cgraph_dash.nodes() if cgraph_dash.in_degree(U)==0]

        for U in toplayer:

            ## line 13: U_dash = Above(V_p,F_p,U)
            U_dash = PyBoolNet.Utility.DiGraphs.ancestors(igraph, U)

            ## line 14: primes_restricted = Restriction(V_p,F_p,U_dash)
            primes_restricted = PyBoolNet.PrimeImplicants.copy(primes_reduced)
            PyBoolNet.PrimeImplicants.remove_all_variables_except(primes_restricted, U_dash)

            ## line 15: Q = MinTrapSpaces(U',F|U')
            Q = PyBoolNet.AspSolver.trap_spaces(primes_restricted, "min")

            ## line 16: phi = CompletenessQuery(Q)
            phi = PyBoolNet.TemporalLogic.EF_oneof_subspaces(primes_restricted, Q)

            ## lines 17,18: answer = PyBoolNet.ModelChecking(S'_U, Update, phi)
            init = "INIT TRUE"
            spec = "CTLSPEC %s"%phi

            if ComputeCounterexample:
                answer, counterex = PyBoolNet.ModelChecking.check_primes_with_counterexample(primes_restricted, Update, init, spec)
                if not answer:
                    downstream = [x for x in igraph if not x in U]
                    arbitrary_state = PyBoolNet.StateTransitionGraphs.random_state(downstream)
                    toplayer_state = counterex[-1]
                    counterex = PyBoolNet.Utility.Misc.merge_dicts([constants_global,p,toplayer_state,arbitrary_state])

                    return False, counterex
            else:
                answer = PyBoolNet.ModelChecking.check_primes(primes_restricted, Update, init, spec)
                if not answer:

                    return False

            ## line 19: Refinement.append(Intersection(p,Q))
            ## Intersection(..) is defined below
            refinement+= Intersection([p], Q)

            ## line 20: W_dash = SetUnion(W',U')
            W_dash.update(U_dash)

        ## line 21
        for q in Intersection(refinement):

            ## line 22: q_tilde = Percolation(V,F,q)
            dummy = PyBoolNet.PrimeImplicants.copy(primes)
            PyBoolNet.PrimeImplicants.create_constants(dummy, Constants=q)
            q_tilde = PyBoolNet.PrimeImplicants.percolate_and_keep_constants(dummy)

            ## lines 23, 24
            if q_tilde not in mintrapspaces:
                currentset.append((q_tilde, W_dash))

    if ComputeCounterexample:
        return True, None
    else:
        return True


# todo: refactor using AttrJson
def create_attractor_report(Primes, FnameTXT=None):
    """
    Creates an attractor report for the network defined by *Primes*.

    **arguments**:
        * *Primes*: prime implicants
        * *FnameTXT* (str): the name of the report file or *None*

    **returns**:
        * *FnameTXT* (str): *FnameTXT=None* or *None* if *FnameTXT* is given

    **example**::
         >>> create_attractor_report(primes, "report.txt")
    """

    mints = PyBoolNet.AspSolver.trap_spaces(Primes, "min")
    steady = sorted([x for x in mints if len(x)==len(Primes)])
    cyclic = sorted([x for x in mints if len(x)<len(Primes)])

    lines = ["",""]
    lines+= ["### Attractor Report"]
    lines+= [" * created on %s using PyBoolNet, see https://github.com/hklarner/PyBoolNet"%datetime.date.today().strftime('%d. %b. %Y')]
    lines+= [""]

    lines+= ["### Steady States"]
    if not steady:
        lines+= [" * there are no steady states"]
    else:
        w = max([12,len(Primes)])
        lines+= ["| "+"steady state".ljust(w)+" |"]
        lines+= ["| "+ w*"-" +" | "]

    for x in steady:
        lines+= ["| "+PyBoolNet.StateTransitionGraphs.subspace2str(Primes, x).ljust(w)+" |"]
    lines+= [""]

    width = max([len(Primes), 14])
    spacer1 = lambda x: x.ljust(width)

    lines+= ["### Asynchronous STG"]
    answer = completeness(Primes, "asynchronous")
    lines+= [" * completeness: %s"%answer]

    if not cyclic:
        lines+= [" * there are only steady states"]
    else:
        lines+= [""]
        line = "| "+"trapspace".ljust(width) + " | univocal  | faithful  |"
        lines+= [line]
        lines+= ["| "+ width*"-" +" | --------- | --------- |"]

    for x in cyclic:
        line =  "| "+ ("%s"%PyBoolNet.StateTransitionGraphs.subspace2str(Primes,x)).ljust(width)
        line+= " | "+ ("%s"%univocality(Primes, "asynchronous", x)).ljust(9)
        line+= " | "+ ("%s"%faithfulness(Primes, "asynchronous", x)).ljust(9)+" |"
        lines+= [line]
    lines+=[""]

    lines+= ["### Synchronous STG"]
    answer = completeness(Primes, "synchronous")
    lines+= [" * completeness: %s"%answer]

    if not cyclic:
        lines+= [" * there are only steady states"]
    else:
        lines+= [""]
        line = "| "+"trapspace".ljust(width) + " | univocal  | faithful  |"
        lines+= [line]
        lines+= ["| "+ width*"-" +" | --------- | --------- |"]

    for x in cyclic:
        line =  "| "+ ("%s"%PyBoolNet.StateTransitionGraphs.subspace2str(Primes,x)).ljust(width)
        line+= " | "+ ("%s"%univocality(Primes, "synchronous", x)).ljust(9)
        line+= " | "+ ("%s"%faithfulness(Primes, "synchronous", x)).ljust(9)+" |"
        lines+= [line]
    lines+=[""]


    bnet = []
    for row in PyBoolNet.FileExchange.primes2bnet(Primes).split("\n"):
        if not row.strip(): continue
        t, f = row.split(",")
        bnet.append((t.strip(),f.strip()))

    t_width = max([7]+[len(x) for x,_ in bnet])
    f_width = max([7]+[len(x) for _,x in bnet])
    lines+= ["### Network"]
    t,f = bnet.pop(0)
    lines+= ["| "+t.ljust(t_width)+" | "+f.ljust(f_width)+" |"]
    lines+= ["| "+t_width*"-"+" | "+f_width*"-"+" |"]
    for t,f in bnet:
        lines+= ["| "+t.ljust(t_width)+" | "+f.ljust(f_width)+" |"]

    lines+=["",""]

    if FnameTXT:
        with open(FnameTXT, "w") as f:
            f.writelines("\n".join(lines))
            print("created %s"%FnameTXT)
    else:
        return "\n".join(lines)


def compute_attractors_tarjan(STG):
    """
    Uses `networkx.strongly_connected_components <https://networkx.github.io/documentation/latest/reference/generated/networkx.algorithms.components.strongly_connected.strongly_connected_components.html>`_
    , i.e., Tarjan's algorithm with Nuutila's modifications, to compute the SCCs of *STG* and
    `networkx.has_path <https://networkx.github.io/documentation/latest/reference/generated/networkx.algorithms.shortest_paths.generic.has_path.html>`_
    to decide whether a SCC is reachable from another.
    Returns the attractors as lists of states.


    **arguments**:
        * *STG*: state transition graph

    **returns**:
        * *SteadyStates* (list of str): the steady states
        * *Cyclic* (list of sets of strs): the cyclic attractors

    **example**:

        >>> bnet = ["x, !x&y | z",
        ...         "y, !x | !z",
        ...         "z, x&!y"]
        >>> bnet = "\\n".join(bnet)
        >>> primes = FEX.bnet2primes(bnet)
        >>> stg = STGs.primes2stg(primes, "asynchronous")
        >>> steadystates, cyclic = STGs.compute_attractors_tarjan(stg)
        >>> steadystates
        ['101','000']
        >>> cyclic
        [set(['111','110']), set(['001','011'])]
    """

    condensation_graph = PyBoolNet.Utility.DiGraphs.digraph2condensationgraph(STG)
    steadystates = []
    cyclic = []
    for scc in condensation_graph.nodes():
        if not list(condensation_graph.successors(scc)):
            if len(scc)==1:
                steadystates.append(scc[0])
            else:
                cyclic.append(set(scc))

    return steadystates, cyclic


def completeness_naive(Primes, Update, TrapSpaces):
    """
    The naive approach to deciding whether *Trapspaces* is complete,
    i.e., whether there is no attractor outside of *Trapspaces*.
    The approach is described and discussed in :ref:`Klarner2015(a) <klarner2015trap>`.
    It is decided by a single CTL query of the :ref:`EF_oneof_subspaces <EF_oneof_subspaces>`.
    The state explosion problem limits this function to networks with around 40 variables.
    For networks with more variables (or a faster answer) use :ref:`completeness_iterative <completeness_iterative>`.

    .. note::
        Completeness depends on the update strategy, i.e.,
        a set of subspaces may be complete in the synchronous STG but not complete in the asynchronous STG or vice versa.

    .. note::
        A typical use case is to decide whether the minimal trap spaces of a network are complete.

    .. note::
        The subspaces of *Trapspaces* are in in fact not required to be a trap sets, i.e., it may contain arbitrary subspaces.
        If there are arbitrary subspaces then the semantics of the query is such that it checks whether each attractor *intersects* one of the subspaces.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspaces* (list): list of subspaces in string or dict representation

    **returns**:
        * *Answer* (bool): whether *Subspaces* is complete in the STG defined by *Primes* and *Update*,

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> answer, counterex = completeness_naive(primes, "asynchronous", mintspaces)
        >>> answer
        True
    """

    spec = "CTLSPEC " + PyBoolNet.TemporalLogic.EF_oneof_subspaces(Primes, TrapSpaces)
    init = "INIT TRUE"
    answer = PyBoolNet.ModelChecking.check_primes(Primes, Update, init, spec)

    return answer


def completeness_naive_with_counterexample(Primes, Update, TrapSpaces):
    """
    The naive approach to deciding whether *Trapspaces* is complete,
    i.e., whether there is no attractor outside of *Trapspaces*.
    The approach is described and discussed in :ref:`Klarner2015(a) <klarner2015trap>`.
    It is decided by a single CTL query of the :ref:`EF_oneof_subspaces <EF_oneof_subspaces>`.
    The state explosion problem limits this function to networks with around 40 variables.
    For networks with more variables (or a faster answer) use :ref:`completeness_iterative <completeness_iterative>`.

    .. note::
        Completeness depends on the update strategy, i.e.,
        a set of subspaces may be complete in the synchronous STG but not complete in the asynchronous STG or vice versa.

    .. note::
        A typical use case is to decide whether the minimal trap spaces of a network are complete.

    .. note::
        The subspaces of *Trapspaces* are in in fact not required to be a trap sets, i.e., it may contain arbitrary subspaces.
        If there are arbitrary subspaces then the semantics of the query is such that it checks whether each attractor *intersects* one of the subspaces.

    **arguments**:
        * *Primes*: prime implicants
        * *Update* (str): the update strategy, one of *"asynchronous"*, *"synchronous"*, *"mixed"*
        * *Trapspaces* (list): list of subspaces in string or dict representation

    **returns**:
        * *Answer* (bool): whether *Subspaces* is complete in the STG defined by *Primes* and *Update*,
        * *CounterExample* (dict): a state from which none of the *Subspaces* is reachable (if *Answer* is *False*)

    **example**::

        >>> mintspaces = PyBoolNet.AspSolver.trap_spaces(primes, "min")
        >>> answer, counterex = completeness_naive(primes, "asynchronous", mintspaces)
        >>> answer
        True
    """

    spec = "CTLSPEC " + PyBoolNet.TemporalLogic.EF_oneof_subspaces(Primes, TrapSpaces)
    init = "INIT TRUE"
    answer, counterex = PyBoolNet.ModelChecking.check_primes_with_counterexample(Primes, Update, init, spec)

    if counterex:
        counterex = counterex[-1]

    return answer, counterex


### auxillary functions
def Intersection(*ListOfDicts):
    """
    each argument must be a list of subspaces (dicts)::

        >>> Intersection([{"v1":1}], [{"v1":0}, {"v2":1, "v3":0}])
    """

    return [PyBoolNet.Utility.Misc.merge_dicts(x) for x in itertools.product(*ListOfDicts)]
