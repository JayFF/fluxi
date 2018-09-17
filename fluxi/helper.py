# -*- coding: utf-8 -*-
"""
Some functions that help to configure and prepare ipython and to find errors
"""
import json,re,sys
import numpy as np

         
def install_fault_handler(error_file='fault_error_log.txt'):
    """ 
    enable the foult hanlder to find crashes where python dies
    outpu is written to a file instead to sys.stderr becaus this does not work in
    iPython
    """
    f=open(error_file, 'w')
    import faulthandler
    faulthandler.enable(file=f, all_threads=True)
    

ipython_tweaked=False
def tweak_ipython():
    global ipython_tweaked
    if not ipython_tweaked:
        from IPython import get_ipython
        ipy = get_ipython()
        if not ipy:
            print("Not inside ipython")
            return
        ipy.magic("gui qt")
        ipy.magic("load_ext autoreload")
        ipy.magic("autoreload 2")
        ipython_tweaked=True

def debug():
    #TODO: not used
    from PyQt4.QtCore import pyqtRemoveInputHook
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()
    
    
       
def install(package):
    """ downloads and installs a package using pip """
    import pip
    pip.main(['install', package])        
#%%    

def prepare_iPython():
    """ 
    Enable Interactive GUI Programming
    Then, you can build your UI as usual, except that when you call the toolkit's main loop 
    your user interface will run while you continue to issue commands interactively.
    We save this to the     
    """
    #execute %gui qt to hook the qt main loop
    import IPython.lib.guisupport
#    if QTMODE!=1:#not IPython.lib.guisupport.is_event_loop_running_qt4():
    if True:
        import IPython
        #c=read_file("%s\\profile_default\\startup\\myconf.py" % IPython.utils.path.get_ipython_dir())
        print ("%s\\profile_default\\startup\\myconf.py" % IPython.utils.path.get_ipython_dir())
        save_str("%s\\profile_default\\startup\\myconf.py" % IPython.utils.path.get_ipython_dir(),
        """from IPython import get_ipython
ipython = get_ipython()
ipython.magic("gui qt")
QTMODE=1""")
        print("restart iPython console to proceed in interactive mode")
        #sys.exit()
        sys.exit()
        return 
        #magic_Exit
    #print("QTMODE ON")
        
#%% general helpers

def nearest_idx(array,value):
    """find the element index closest to the value looked for"""
    return (np.abs(array-value)).argmin()
        
#%% File reading and writing ###########################################

class NumpyAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):# and obj.ndim == 1:
            return obj.tolist()
        return json.JSONEncoder.default(self, obj) 
#def read_file(name):  
#    with open (name, "r") as f:
#        return "".join(f.read())#.replace('\n', '')
#
#def write_file(name,string):
#    with open(name, "w") as f:
#        f.write(string)
    
    
def save_json(obj,filename,add_to_name="",ext="json"):
    #print(repr(ext),repr(filename))
    if  not re.search(re.escape('.'+ext), filename):
        if add_to_name!='':
            filename=filename+'.'+add_to_name+'.'+ext
        else:
            filename=filename+'.'+ext   
    with open(filename, 'w') as f:
        json.dump(obj, f, cls=NumpyAwareJSONEncoder, sort_keys=True, indent=4, separators=(',', ': '))  
    #TODO: USE COMPACT PRETTY PRINTING   
    #http://justanyone.blogspot.de/2012/04/how-to-pretty-print-jsondumps-with.html
def load_json(filename,add_to_name="",ext="json"):
    if  not re.search(re.escape('.'+ext), filename):
        if add_to_name!='':
            filename=filename+'.'+add_to_name+'.'+ext
        else:
            filename=filename+'.'+ext
    with open(filename, 'r') as f:
        return json.load(f)

def to_json_str(obj):
    return json.dumps(obj, cls=NumpyAwareJSONEncoder, sort_keys=True, indent=4, separators=(',', ': '))  

def save_tsv(data,filename,add_to_name="",ext="tsv.gz",header=None):
    if  not re.search(re.escape('.'+ext), filename):
        if add_to_name!='':
            filename=filename+'.'+add_to_name+'.'+ext
        else:
            filename=filename+'.'+ext
    if header is not None:
        np.savetxt(filename, data, delimiter='\t',fmt=b'%g',header=header) #%.18e
    else:
        np.savetxt(filename, data, delimiter='\t',fmt=b'%g') #%.18e
        
import os

def load_tsv(filename,add_to_name="",ext="tsv.gz"):
    if  not re.search(re.escape('.'+ext), filename):
        if add_to_name!='':
            filename=filename+'.'+add_to_name+'.'+ext
        else:
            filename=filename+'.'+ext
    if not os.path.isfile(filename):
        raise IOError("File %s Not Found"%filename)
    try:
        d=np.loadtxt(filename, delimiter="\t")
    except:
        print ("could not load File %s"%filename)
        raise 
    return d
    
def save_str(data,filename,add_to_name="",ext="str"):
    """ single command to write a string to a file """
    if  not re.search(re.escape('.'+ext), filename):
        if add_to_name!='':
            filename=filename+'.'+add_to_name+'.'+ext
        else:
            filename=filename+'.'+ext         
    with open(filename, "w") as f:
        f.write(data)
    
def load_str(filename):
    """ single command to read a whole file into a string """
    with open (filename, "r") as f:
        return "".join(f.read())#.replace('\n', '')




import collections
def dict_update(base_dict, add_dict):
    """ recursivly updates a nested dictionary with another (nested) dictionary """
    d=base_dict
    u=add_dict
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            try:
                d[k] = u[k]
            except:
                pass
    return d