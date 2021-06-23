import copy
from sympy import sympify, true, false, Or
from replace_str import replaceMultiple2
def main(state, booleanlogic):
    step = True
    STATE = state.copy()
    booleanlogic = replaceMultiple2(booleanlogic, [' and ',' or ',' not '], [' & ',' | ',' ~ '])
    booleanlogicLine = booleanlogic.splitlines()
    booleanlogicDic = {}
    for line in booleanlogicLine:
        if line.strip() == "":
            continue
        linelist = line.strip().split('=')
        booleanlogicDic[linelist[0].strip()] = ' '+ linelist[1].strip()+' '
        if STATE[linelist[0].strip()] in ['True','False']:
            booleanlogicDic[linelist[0].strip()] = STATE[linelist[0].strip()]
    while step:
        new_booleanlogicDic = copy.deepcopy(booleanlogicDic) 
        for fvn in STATE:
            if STATE[fvn] == '':
                continue
            for n in booleanlogicDic:
                if fvn in booleanlogicDic[n]:
                    new_booleanlogicDic[n] = new_booleanlogicDic[n].replace(' '+fvn+' ', ' '+STATE[fvn]+' ')
        if new_booleanlogicDic == booleanlogicDic:
            step = False
            return(STATE)
        elif new_booleanlogicDic != booleanlogicDic:
            booleanlogicDic = copy.deepcopy(new_booleanlogicDic)
            for fvn in booleanlogicDic.keys():
                line = booleanlogicDic[fvn]
                line = replaceMultiple2(line, ['True', 'False'], ['true','false'])
                line_sim = ' '+str(sympify(line))+' '
                if STATE[fvn] == '':
                    if line_sim in [' False ',' True ']:     
                        STATE[fvn] = line_sim.strip()                  
                else:
                    booleanlogicDic[fvn] = line_sim
if __name__ == '__main__':
    from booleanlogic_preprocessing import modeltext2nummodeltext
    from booleanlogic_preprocessing import get_interaction_network
    booleanlogic = '''
    A = B
    E = False
    C = not B and E
    B = A or C
    D = False
    '''
    booleanlogicNum, node2num, num2node = modeltext2nummodeltext(booleanlogic)
    dgraph, nodeList, inputNodeState = get_interaction_network(booleanlogicNum)
    canalizedState = main(inputNodeState,booleanlogicNum)
    
