# -*- coding: utf-8 -*-
"""
Created on Tue Dec 02 13:20:57 2014

@author: q
"""
from pyqtgraph.widgets.SpinBox import SpinBox as GSpinBox#, fn

import re#,math
class SpinBox(GSpinBox):
    def stepBy(self, step):
        """
        do a step up or down according to the position the cursor is found
        """
        import math,decimal

        le=self.lineEdit()   
        st=str(le.displayText())
        #get position of the digit     
        m=re.search('([^-\d]*)([-\d]+)(\.?)(\d*)(.*)',st)
        gr=m.groups()       
        lens=list(map(len,gr))
        digit1pos=lens[0]+lens[1]

        #get the position of the cursor relative to the radix
        pos=le.cursorPosition()        
        exp=digit1pos-min(max(lens[0]+1,pos),lens[0]+lens[1]+lens[2]+lens[3])
        if exp<-1:
            exp+=1
        fl=float(gr[1]+gr[2]+gr[3])
        sgn=math.copysign(1,step)
        step=sgn*10.**exp
        newval=decimal.Decimal(fl)+decimal.Decimal(step)
        
        #set the new value
        text=("%s%."+str(lens[3])+"f%s")%(gr[0],newval,gr[4])
        le.setText(text)       
        self.editingFinishedEvent()
        
        #set cursor pos AND set correct number of digits that the cursor can be there
        m=re.search('([^-\d]*)([-\d]+)(\.?)(\d*)(.*)',text)
        gr=m.groups()       
        lens=list(map(len,gr))
        digit1pos=lens[0]+lens[1]
        pos=digit1pos-exp
        if exp<0:
            pos+=1
        
        fl=float(gr[1]+gr[2]+gr[3])            
        text=("%s%."+str(lens[3])+"f%s")%(gr[0],fl,gr[4])
        le.setText(text)
        le.setCursorPosition(pos)
