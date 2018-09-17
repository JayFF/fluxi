"""Some Basic Tests"""

def test_complex_gui():
    """Check some complex gui"""    
    #%%    
    from fluxi import Fluxi
    fl=Fluxi("Testx")
    
    fl.C("A Running Chart")
    fl.log("message")
    fl.G("Graph").set([0,8,11,2,5,12])
    fl.P("A Float").v=10
    fl.S("Folder/A String Input")
    fl.B("More/A Boolean")
    fl.Int("More/An Integer")
#    fl.Choose("More/Choose").setValues(["a","b","c"])
    fl.wait(1)
    del fl
    #%%