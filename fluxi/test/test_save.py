# -*- coding: utf-8 -*-
"""
"""
from fluxi import Fluxi

#def test_save_and_restore():
#    """ check if the values are the same after loading from config file"""
#    for n,v in [("f",11.2),("i",6),("s","sttt"),("b",False),("b",True)]:
#        yield check_restore,n,v

#%%
def check_restore(n,v):
    flx=Fluxi("Save and Restore")
    flx.g(n+":Value").v=v
    assert flx.g(n+":Value").v==v
    flx.save_cfg()
    del flx
    flx=Fluxi("Save and Restore")
    assert flx.g(n+":Value").v==v
    del flx
    
#check_restore("f",11.2)