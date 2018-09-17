# -*- coding: utf-8 -*-
"""
Fix some errors in pyqtgraph here
"""

#Fix pyqtgraph error with exponential notation with positive exponent
import pyqtgraph.functions
    
if pyqtgraph.functions.siEval("2e+8")==2.0:
    import re
    from pyqtgraph.functions import SI_PREFIXES
    from pyqtgraph.python2_3 import asUnicode
    
    def siEval(s):
        """
        Convert a value written in SI notation to its equivalent prefixless value
        
        Example::
        
            siEval("100 μV")  # returns 0.0001
        """
        
        s = asUnicode(s)
        m = re.match(r'(-?((\d+(\.\d*)?)|(\.\d+))([eE][-+]?\d+)?)\s*([u' + SI_PREFIXES + r']?).*$', s)
        if m is None:
            raise Exception("Can't convert string '%s' to number." % s)
        v = float(m.groups()[0])
        p = m.groups()[6]
        #if p not in SI_PREFIXES:
            #raise Exception("Can't convert string '%s' to number--unknown prefix." % s)
        if p ==  '':
            n = 0
        elif p == 'u':
            n = -2
        else:
            n = SI_PREFIXES.index(p) - 8
        return v * 1000**n
    pyqtgraph.functions.siEval=siEval
