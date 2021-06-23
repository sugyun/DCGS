# -*- coding: utf-8 -*-
"""
Created on Fri Dec  4 10:37:17 2020

@author: ansu
"""

def replaceMultiple(mainString, toBeReplaces, newString):
    for elem in toBeReplaces :
        # Check if string is in the main string
        if elem in mainString :
            # Replace the string
            mainString = mainString.replace(elem, newString)
    return (mainString)
def replaceMultiple2(mainString, toBeReplaces, newStrings):
    for elem, new in zip(toBeReplaces,newStrings) :
        # Check if string is in the main string
        if elem in mainString :
            # Replace the string
            mainString = mainString.replace(elem, new)
    return (mainString)

if __name__ =="__main__":
    mainString = ' a b c e d f g e '
    S1 = replaceMultiple(mainString, 'e', 'E')
    S2 = replaceMultiple(mainString, ['e','f'], 'E')
    S3 = replaceMultiple2(mainString, ['e','g'], ['E','G'])
