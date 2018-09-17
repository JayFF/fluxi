# -*- coding: utf-8 -*-
from fluxi import Fluxi

if __name__ == '__main__':
    fl=Fluxi("Demo")
#%%

def test_setting_and_getting():
    """Sample test method for branch coverage."""
    fl.P("A Float").v=5
    assert fl.F("A Float").v==5

def test_setget_int():
    """ """
    fl.Int("Integer").v=5
    assert fl.Int("Integer").v==5

def test_setget_int2():
    """ """
    fl.Int("Integer").v=5.1
    assert fl.Int("Integer").v==5
    
    
