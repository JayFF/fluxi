"""
ScanFluxi
"""
__version__='0.93'
import time
from fluxi import Fluxi
from fluxi.helper import load_json,save_json
import numpy as np
import scan_globals
from scandata import ScanData
from scan_overviews import Overview

from multiprocessing import dummy as multithreading 
#pool = multithreading.Pool(1)
#%%

ms=Fluxi("Scan")
scan_globals.gui=ms
ms.win.misctoolbar = ms.win.addToolBar('Misc')
#%%
import fluxi.helper
fluxi.helper.install_fault_handler()
    
#%% AREA ######################################################################
ms.P("Area/minx").a=ms.P("Area/maxx").a=ms.P("Area/miny").a=ms.P("Area/maxy").a=Overview.area_corners_changed
ms.P("Area/sizex").a=ms.P("Area/sizey").a=Overview.area_wh_changed

def set_area_to_scan_area(*args):
    global scan
    dims=list(scan.origin)+list(scan.step*np.array(scan.sizepx))
    Overview.area_changed(*dims)
ms.A("Area/set extents to scan").a=set_area_to_scan_area

def crosshair_dragged(pos):
    ms.B("Scan/Scanning").v=False
    set_target_pos(pos)  
Overview.actions["dragged"]=crosshair_dragged


#%%
ms.List("AreaList").setHeaders(["Name","x0","y0","x1","y1","date","desc"],sizes=[])
def load_areas_file(*args):
    li=ms.List("AreaList")
    li.clear()
    li.setDict(load_json(ms.S("Areas/File").v))
ms.A("Areas/Load").a=load_areas_file

def save_areas_file(*args):
    save_json(ms.List("AreaList").getDict(),ms.S("Areas/File").v) 
ms.A("Areas/Save").a=save_areas_file

def setArea(*args):
    items=ms.List("AreaList").mainwidget.selectedItems()
    if len(items)==1:
        item=items[0]
        d=[item.data(i,0) for i in range(item.columnCount())]
        #print((d[1],d[2],d[3]-d[1],d[4]-d[2]))
        Overview.area_changed(d[1],d[2],d[3]-d[1],d[4]-d[2])
ms.A("Areas/use selected area").a=setArea

def addArea(*args):
    ms.List("AreaList").addParent(["unnamed",ms.P("Area/minx").v,ms.P("Area/miny").v,ms.P("Area/maxx").v,ms.P("Area/maxy").v,time.strftime("%Y-%m-%d %H:%M:%S")])
ms.A("Areas/Add").a=addArea

#%% Save and Load #############################################################
scan=None
#%%
def load(*args,name=None):
    global scan
    if name is None:
        name=ms.S("Data/Name").v
    scan=scan_globals.scan_data=ScanData(name) 
    scan.load()  
    ms.P("Areas/Data/stepsize").v=scan.step   
    ms.P("Areas/Data/originx").v,ms.P("Areas/Data/originy").v=scan.origin          
    update_data()
def save(*args):
    scan.save(name=ms.S("Data/Name").v)
    scan.save(name=ms.S("Data/Temp Name").v)
    
    #scan.flush()
    fluxi.helper.save_json(ms.get_values_all(),ms.S("Data/Name").v,add_to_name="values")
    fluxi.helper.save_json(ms.get_values_all(),ms.S("Data/Temp Name").v,add_to_name="values")
    if hasattr(mm, "save_data"):
        mm.save_data()
    if hasattr(lock, "save_data"):
        lock.save_data()
    if ms.B('Pos/PD_readout').v and hasattr(pos,"save_data"):
        pos.save_data()
        
def create(*args):
    global scan
    print("create")
    scan=scan_globals.scan_data=ScanData(ms.S("Data/Temp Name").v) 
    step=ms.P("Area/step").v
    if step==0:
        step=ms.P("Area/step").v=1
    sizepx=(abs(ms.P("Area/maxx").v-ms.P("Area/minx").v)/step,
            abs(ms.P("Area/maxy").v-ms.P("Area/miny").v)/step)
    origin=(ms.P("Area/minx").v,ms.P("Area/miny").v)          
    if sizepx[0]<=0 or sizepx[1]<=0:
        sizepx=100,100
    scan.create(stepsize=step,origin=origin,sizepx=sizepx)
    ms.P("Areas/Data/stepsize").v=scan.step   
    ms.P("Areas/Data/originx").v,ms.P("Areas/Data/originy").v=scan.origin
    if hasattr(mm,"save_calib"):
        mm.save_calib()

         

    update_data()
    
ms.A("Data/Load").a=load
ms.A("Data/Create").a=create
ms.A("Data/Save").a=save
#%%
        
#%%
ms.B("Scan/Scanning").v=False
def scan_start_over(*args):        
    ms.P("Data/xarrpos").v,ms.P("Data/yarrpos").v=scan.realpos_to_array_pos((ms.P("Area/minx").v,ms.P("Area/miny").v))
    nextpos()
    ms.B("Scan/Scanning").v=True
    start_statemachine()
ms.A("Scan/Start over").a=scan_start_over


#%% Update Image and Data ####################################################
ov=Overview("ScanImage",sync_pos_to="Data")
ovPD=Overview("PD_data",sync_pos_to="Data")
#ovT=Overview("record time",sync_pos_to="Data")
#%%
def update_data(value=None): 
    if ms.B("Measure/record").v and value!=None:
        scan.savetoarray("data",value)
        if mm and hasattr(mm,"record"):
            mm.record()
        if lock and hasattr(lock,"record"):
            lock.record()
        if ms.B('Pos/PD_readout').v and hasattr(pos,"record"):
            pos.record()             
    if ms.B("Scanpoints/record points").v and value!=None:
        if mm and hasattr(mm,"recordpoint"):
            mm.recordpoint()
           
    if mmnum%ms.Int("update plot every nth").v==0:
        try:
            data=scan.getArray("data")
            #ov.set_extent(scan.origin,scan.step)
            ov.set_data(data)
        except:
            pass#TODO
            
#    if ms.B("Pos/Show_PD_data_permanent").v:
#        print('bla')
#        show_PD_data        
    
    #ovT.set_data(scan.getArray("record_time")[:])
            
#%%
def show_PD_data(*args):
    if ms.B('Pos/PD_readout').v and hasattr(pos,"show_data"):
        #pos.show_data()
        arr = scan_globals.scan_data.getArray(arrayname="PD_max")
        #ms.Im("PD_max").setImage(arr)
        ovPD.set_data(arr)
        
ms.A("Pos/Show_PD_data").a=show_PD_data
#ms.B("Pos/Show_PD_data_permanent").v=False

#%%

#%% Posi #########################################################
pos=None
#%%
def init_positioners(*wargs):
    """ init the chosen positioner and retrieve the curren position+length, set this also as the current target"""
    global pos
    force_next_state("idle")
    if hasattr(pos,"disconnect"):
            pos.disconnect()
    pos=scan_globals.pos=None       
    if ms.Choose("Pos/positioner").v=="Attocube ECC":
        try:
            from positioners.pos_ecc import PosiECC
            pos=PosiECC()
        except WindowsError:
            ms.log("Could not Load Attocube positioner. DLL not found","Error")
    elif ms.Choose("Pos/positioner").v=="JPE":
        try:
            from positioners.pos_jpe import PosiJPE
            pos=PosiJPE()
        except:
            ms.log("Could not Load PosiJPE positioner","Error")
            raise

    elif ms.Choose("Pos/positioner").v=="PI":
        try:
            from positioners.pos_pi import PosiPI
            pos=PosiPI()
        except WindowsError:
            ms.log("Could not Load PI positioner. DLL not found","Error")
    elif ms.Choose("Pos/positioner").v=="Attocube ANC":
        from positioners.pos_anc import posiANC
        pos=posiANC()
    elif ms.Choose("Pos/positioner").v=="Attocube Scanner":
        from positioners.pos_anc_scanner import posiANCscan
        pos=posiANCscan()
    if pos==None:
        from positioners.pos_dummy import PosiDummy
        pos=PosiDummy()
    scan_globals.pos=pos        
    pos.connect()
    
    check_position(force=True)
    set_target_pos((ms.P("Pos/current x").v,ms.P("Pos/current y").v))
    ms.P('Pos/cavity length').v=pos.getLength()
    force_next_state("start procedure")
ms.Choose("Pos/positioner").setValues(["Dummy","Attocube ECC","PI","Attocube ANC","JPE","Attocube Scanner"]).a=init_positioners    

def pos_panic_shutdown(*args):
    pos.panic()
ms.A2('Pos/Panic!!!').a=pos_panic_shutdown

def pos_center(*args):
    set_target_pos((ms.P("Area/minx").v+ms.P("Area/sizex").v/2,ms.P("Area/miny").v+ms.P("Area/sizey").v/2))
ms.A('Pos/move to center').a=pos_center

def length_changed(p,value):
    pos.setLength(value) 
ms.P('Pos/cavity length').a=length_changed  
    
def set_target_pos(pos):
    ms.P("Pos/target x").v,ms.P("Pos/target y").v=pos
#%%       
def move_to_position():
    pos.setxy(ms.P("Pos/target x").v,ms.P("Pos/target y").v)
    if mm.autoset_CavityLength:
        pos.setLength(ms.P("Pos/cavity length").v)
def check_position(force=False):
    global endline
    tx,ty=ms.P("Pos/target x").v,ms.P("Pos/target y").v
    if ms.B("Pos/check position").v or force or endline:
        x,y=pos.getxy()
    else:
        x,y=tx,ty
    #print(x,y,tx,ty)
    ms.P("Pos/current x").v,ms.P("Pos/current y").v=x,y
    ms.P("Data/xarrpos").v,ms.P("Data/yarrpos").v=scan.set_pos((tx-0.5*scan.step,ty-0.5*scan.step))
    
    Overview.update_crosshairs((x,y))
       
    if ms.B("Pos/check position").v or force or endline:
        ms.P("Pos/current distance").v=max(abs(x-tx),abs(y-ty))
        if max(abs(x-tx),abs(y-ty))>ms.P("Pos/max distance").v:
            time.sleep(0.005)
            return False
        if ms.B("Pos/check length").v:
            if abs(pos.getLength()-ms.P("Pos/cavity length").v)>ms.P("Pos/max length distance").v:
                return False
        return True
    return True    
    

#%% ########################### Lock modules ##################################

lock=None
def set_lock(p=None,mode=None):
    global lock
    if lock:
        lock.disconnect()
        lock=scan_globals.lock=None
    if not mode:
        mode=ms.Choose("Main/Lock module").v
    ms.log("using lock %s"%mode)
    if mode=="twolaser":
        from lock_twolaser import Lock
    elif mode=="rightwlen":
        from lock_rightwlen import Lock        
    elif mode=="johann":
        from lock_johann import Lock    
    elif mode=="sideoffringe":        
        from lock_sideoffringe import Lock           
    elif mode=="max":
        from lock_maxsearch import Lock   
    elif mode=="max posi":
        from lock_maxsearch2 import Lock
    elif mode=="Yokogawa":
        from lock_volt_Yoko import Lock
    elif mode=="Voltage":
        from lock_Voltage import Lock                    
    else:
        from lock_none import Lock
    lock=Lock()
    lock.prepare()
    scan_globals.lock=lock

ms.Choose("Main/Lock module").setValues(["none","johann","twolaser","sideoffringe","max","rightwlen","max posi","Yokogawa","Voltage"]).a=set_lock

#%% ########################### Measure Modules ###############################
modules_loaded={}
mm=None
#winspec=False
def set_measurement(p=None,mode="nothing"):
    global mm
    if mm:
        mm.disconnect()
        #winspec=False
        if hasattr(mm,"gui"):
            mm.gui.win.hide()
        mm=scan_globals.mm=None
    ms.log("now measureing %s"%mode)
    if mode not in modules_loaded:
        if mode=="specstep":
            from m_specstep import MeasureSpecStep
            mm=MeasureSpecStep(ms)
        elif mode=="Voltsweep":
            from m_voltsweep2 import MeasureVoltSweep
            mm=MeasureVoltSweep(ms)
        elif mode=="VoltsweepCF":
            from m_voltsweep3 import MeasureVoltSweep
            mm=MeasureVoltSweep(ms)
        elif mode=="Voltsweep_daq":
            from m_voltsweep_daq import MeasureVoltSweepDaq
            mm=MeasureVoltSweepDaq(ms)            
        elif mode=="spec":
            from m_spec import MeasureSpec
            mm=MeasureSpec(ms)            
        elif mode=="osci":
            from m_osci import MeasureOsci
            mm=MeasureOsci(ms)
        elif mode=="PLE":
            from m_PLE import MeasurePLE 
            mm=MeasurePLE(ms)            
        elif mode=="PLE_victor":
            from m_PLE_victor import MeasurePLE #changed the filename(victor)
            mm=MeasurePLE(ms)            
        elif mode=="jump":       
            from m_jump import MeasureJump
            mm=MeasureJump(ms)         
        elif mode=="analogdaq":       
            from m_analogdaq import MeasureAnalogDaq
            mm=MeasureAnalogDaq(ms)         
        elif mode=="jump":       
            from m_jump import MeasureJump
            mm=MeasureJump(ms)           
        elif mode=="APD":       
            from m_apd import MeasureAPD
            mm=MeasureAPD(ms)
        elif mode=="Finesse":       
            from m_finesse import MeasureFinesse
            mm=MeasureFinesse(ms)  
        elif mode=="Winspec":
            from m_winspec import MeasureWinSpec
            mm=MeasureWinSpec(ms)
            winspec=True
        else:
            from m_base import MeasureBase
            mm=MeasureBase(ms)
        modules_loaded[mode]=mm
    else:
        mm=modules_loaded[mode]
        if hasattr(mm,"gui"):
            mm.gui.win.show()        
    scan_globals.mm=mm
#==============================================================================
#     if winspec:
#         if hasattr(mm,"connect"):
#             pool.apply(mm.connect)
#     else:
#==============================================================================
    if hasattr(mm,"connect"):
        mm.connect()
    mm.prepare()
    
def reinit_m(*args):
    force_next_state("idle")
    set_measurement(mode=ms.Choose("Measure/Measure module").v)  
    mm.newpoint()
    force_next_state("start procedure")   

ms.Choose("Measure/Measure module").setValues(["none","spec","specstep","Voltsweep","VoltsweepCF","osci","jump","PLE","PLE_victor","analogdaq","APD","Finesse","Winspec"]).a=reinit_m 
ms.A2("reinit measmt").a=reinit_m   


#%% ################################## Points #################################
pn=ms.S("Scanpoints/Pointname")        
chs={}
#%%
#def update_point_crosshairs():
#    global chs
#    for n in chs:
#        im.getView().removeItem(chs[n])
#    chs={}
#    
#    for v in ms.Table("Points").v:
#        chs[v[0]]=c=Crosshair(1,{"color":"#31E852","width":2},pos=(float(v[1]),float(v[2])))
#        im.getView().addItem(c)
#        #im.getView().removeItem(chs)   
#update_point_crosshairs()
#%%
ms.P("Scanpoints/current")
ms.P("Scanpoints/Accumulations")
ms.P("Scanpoints/Accumulation #")
ms.B("Scanpoints/Scan Points")

ms.List("PointList").setHeaders(["Name","x","y","r","date","div"],sizes=[],resizing=["content","content","content","content","content","stretch"])
def load_pointlist_file(*args):
    li=ms.List("PointList")
    li.clear()
    try:
        li.setDict(load_json(ms.S("Scanpoints/PointList File").v))
    except:
        pass
ms.A("Scanpoints/Load").a=load_pointlist_file
def save_pointlist_file(*args):
    save_json(ms.List("PointList").getDict(),ms.S("Scanpoints/PointList File").v) 
ms.A("Scanpoints/Save").a=save_pointlist_file

def goToPoint(*args):
    li=ms.List("PointList")
    item=li.getByName(str(ms.S("Scanpoints/Pointname").v),parent=li.getByName(ms.S("Scanpoints/Current list").v))
    data=[item.data(i,0) for i in range(item.columnCount())]
    #print(data)
    xy=np.array([ms.P("Scanpoints/driftoffset x").v,ms.P("Scanpoints/driftoffset y").v])+data[1:3]
    set_target_pos(xy)
ms.A("Scanpoints/Goto Point").a=goToPoint

#%%

def changed_selection(*args):
    li=ms.List("PointList")
    items=li.mainwidget.selectedItems()
    #print(items)
    if len(items)==1:
        ms.S("Scanpoints/Pointname").v=str(items[0].data(0,0))#(col, ?)
#        data=[items[0].data(i,0) for i in range(items[0].columnCount())]
#        print(data)
ms.List("PointList").mainwidget.itemSelectionChanged.connect(changed_selection)

#%%
def addPointList(*args):
    ms.List("PointList").addParent([ms.S("Scanpoints/Current list").v])
ms.A("Scanpoints/Add List").a=addPointList

#%%
def remove_selected_point(*args):
    li=ms.List("PointList")
    items=li.mainwidget.selectedItems()
    #print(items)
    for i in items:   
        if i.parent()==None:
            i.treeWidget().invisibleRootItem().removeChild(i)
        else:
            i.parent().removeChild(i)
    return items
ms.A("Scanpoints/remove selected").a=remove_selected_point
#%%
ms.S("Scanpoints/Current list")
#%%
def get_points():    
    return [i["data"][:3] for i in ms.List("PointList").getSublist(ms.S("Scanpoints/Current list").v)["children"]]       
#%%    
    
def start_pointscan(*args):
    if ms.show_dialog(title='Clear Points?',yes_t='Clear',no_t='Keep'):
        mm.spectra_names=[]
        mm.spectra=[]            
    ms.P("Scanpoints/current").v=0
    ms.B("Scanpoints/record points").v=True
    ms.B("Scanpoints/Scan Points").v=True
    ms.B("Scan/Scanning").v=True
ms.A("Scanpoints/Start").a=start_pointscan
def safe_current_point(*args):
    px,py=pos.getxy()
    parent=ms.List("PointList").getByName(ms.S("Scanpoints/Current list").v)
    ms.List("PointList").addChild([str(ms.S("Scanpoints/Pointname").v),px,py],parent=parent)
    #update_point_crosshairs()
ms.A("Scanpoints/Add point").a=safe_current_point    
#ms.List("PointList").addParent(["Punkte4"])
#%%
def record_point(*args):
    mm.recordpoint()
ms.A("Scanpoints/Record point").a=record_point 

#%%
endline=False
ms.P("Scan/direction").v=1
sleep=False
def nextpoint_scanpoints():
    points=get_points()
    ms.P("Scanpoints/current").v+=1
    if ms.P("Scanpoints/current").v>=len(points):
        ms.B("Scan/Scanning").v=False
        ms.B("Scanpoints/record points").v=False
        return False        
    p=points[int(ms.P("Scanpoints/current").v)]
    ms.S("Scanpoints/Pointname").v=p[0]
    ms.log("measuring point %s"%p[0] )  
    xy=np.array([ms.P("Scanpoints/driftoffset x").v,ms.P("Scanpoints/driftoffset y").v])+list(map(float,p[1:3]))
    set_target_pos(xy)
    return True
    
def nextpos():
    global endline, sleeptime, sleep
    if ms.B("Scanpoints/Scan Points").v:
        nextpoint_scanpoints()
    sleeptime=0.
    end=False
    endline=False
    ydir = ms.B("Scan/Scan in y-direction").v
    onedir = ms.B("Scan/In one direction").v
    _dir=ms.P("Scan/direction").v
    tx,ty=ms.P("Data/xarrpos").v,ms.P("Data/yarrpos").v
    sx,sy=scan.realpos_to_array_pos((ms.P("Area/maxx").v,ms.P("Area/maxy").v))
    waitx=ms.P("Pos/MoveToPositionPause").v*sx*0.3
    waity=ms.P("Pos/MoveToPositionPause").v*sy*0.3
    if sleep:
        if ydir:
            sleeptime=waity
        else:
            sleeptime=waitx
        sleep=False
    x0,y0=scan.realpos_to_array_pos((ms.P("Area/minx").v,ms.P("Area/miny").v))
    if ydir:
        ty+=_dir
        if ty>sy-1 and _dir>0:
            ty=sy-1
            endline = True
        if ty<y0 and _dir<0:
            ty=y0
            endline=True
    else:
        tx+=_dir
        if tx>sx-1 and _dir>0:
            tx=sx-1
            endline=True
        if tx<x0 and _dir<0:
            tx=x0
            endline=True
            
    if endline:
        if not onedir:
             _dir=-_dir
        if ydir:             
            tx=tx+1
            if tx>=sx:
                end=True
            if _dir<0:
                ty=sy-1
            if _dir>0:
                ty=y0
                sleep=True
        else:
             ty=ty+1
             if ty>=sy:
                 end=True
             if _dir<0:
                 tx=sx-1
             if _dir>0:
                 tx=x0
                 sleep=True
                 
    ms.P("Scan/direction").v=_dir
    if end:
        return False
    set_target_pos(scan.arraypos_to_real_pos((tx,ty)))
    return True  
#%%
def remaining_points():
    lefttop=scan.realpos_to_array_pos((ms.P("Area/minx").v,ms.P("Area/miny").v))
    px,py=np.array([ms.P("Data/xarrpos").v,ms.P("Data/yarrpos").v])-lefttop
    sx,sy=np.array(scan.realpos_to_array_pos((ms.P("Area/maxx").v,ms.P("Area/maxy").v)))-lefttop
    if ms.B("Scan/Scan in y-direction").v:
        px,py=py,px
        sx,sy=sy,sx
    if ms.P("Scan/direction").v==-1:
        done=py*sx+sx-px
    else:
        done=py*sx+px
    remaining=sx*sy-done
    return remaining  

#%% Statemachine
state="init"
states=[]
starttime=0
laststates=[]
force_state=None
def st(nextstate):
    """ set what the next state will be """
    global states
    states=[nextstate]
def force_next_state(nextstate):
    """ force what the next state will be, this will not be overwritten by call to st() """
    global force_state,states
    force_state=nextstate
    states=[nextstate]
#%%
mmnum=0
timings={}
sleeptime=0.
def statemachine(p=None,v=None):
    global state,states,starttime,laststates,force_state,lt,mmnum,sleeptime
    lt=time.time()
    pause=ms.P("Main/defaultPause").v
    if force_state is not None:
        state=force_state
        force_state=None
        ms.S("Main/currentState").v="%s" %state
        laststates.append(state)    
    ms.S("Main/currentState").v="%s" %state
    
    if state=="idle":
        pause=0.1
    elif state=="init":
        st("start procedure")
    elif state=="start procedure":
        starttime=time.time()
        sleeptime=0.
        st("move to position")
    elif state=="move to position":
        move_to_position()
        st("check position")
        pause=ms.P("Pos/MoveToPositionPause").v
    elif state=="check position":
        if not check_position():
            st("move to position")
        else:
            st("lock")
    elif state=="lock":
        if not lock.lock():
            st("check position")
            pause=lock.pause()
        else:
            st("start measurement")
    elif state=="start measurement":
#        if winspec:
#            pool.apply(mm.start)
#        else:
        mm.start()
        st("wait measurement end")    
        #pause=mm.q_finished_pause
    elif state=="wait measurement end":
#        if winspec:
#            if not pool.apply(mm.q_finished):
#                st("wait measurement end")
#                pause=mm.q_finished_pause
#            else:  
#                st("check repeat")
#        else:
            #print(winspec)
        if not mm.q_finished():
            st("wait measurement end")
            pause=mm.q_finished_pause
        else:  
                st("check repeat")
    elif state=="check repeat":        
        ms.C("Current Values").add(mm.curvalue())
        mm.updateMainGui()
        if ms.P("Measure/try #").v>ms.P("Measure/max tries").v:
            st("measurement done")
        else:
            if not lock.check() or mm.q_failed():
                ms.P("Measure/try #").v+=1
                st("move to position")
            elif mm.repeat():
                st("move to position")
            else:
                st("measurement done")
    elif state=="measurement done":
        ms.P("Measure/try #").v=0         
        if mm.q_record():
            v=mm.getValue()
            ms.C("Measured Values").add(v)
            lastValues=ms.C("Measured Values").v[0,-20:]
            if lastValues.mean()!=0:
                ms.C("Stddev of Values").add(lastValues.std()/lastValues.mean())
            ms.P("Measure/Last Value").v=v
            update_data(v)
        st("prepare next")
    elif state=="prepare next":     
        mmnum+=1
        st("start procedure")
        dt=time.time()-starttime
        ms.C("measurement times").add(dt)
        scan.savetoarray("record_time",dt)
        ms.P("Measure/Mean time").v=np.nanmean(ms.C("measurement times").arrs,1)[0]  
        ms.P("Measure/Remaining time [h]").v=round((remaining_points()*ms.P("Measure/Mean time").v)/3600,3)
        if ms.B("Scan/Scanning").v:
            ms.S("Data/Last measurement").v=time.strftime("%Y-%m-%d %H:%M:%S")
            pause=sleeptime
            sleeptime=0.
            if not nextpos(): #returns False if we hit the end of the scan
                ms.log("Scan finished")            
                if ms.B("Layer Scan/Layscan On").v:
                    st("new layer") #prepare new layer              
                else:
                    ms.B("Scan/Scanning").v=False #stop scanning 
            if endline and ms.B("Scan/Save at end of line").v:
                save()
        mm.newpoint()
    elif state=="startloop":
        states=["start procedure"]
    elif state=="new layer":
        if ms.P("Pos/cavity length").v+ms.P("Layer Scan/Length Step").v < ms.P("Layer Scan/End Length").v: #ie if next step would take us past end length
            ms.P("Pos/cavity length").v+=ms.P("Layer Scan/Length Step").v
            #TODO: Warning: Not working if scanning in y-direction
            ms.P("Data/xarrpos").v,ms.P("Data/yarrpos").v=0,-1             
            nextpos()
        else:
            ms.B("Scan/Scanning").v=False #stop scanning
        #scan.save_current_data_to_csv(additional_name=str(int(ms.P("Pos/cavity length").v*1000))+"nm")
        st("move to position")
        
    elif state=="move to cavity":
        if pos.gui.B("Objective/Active").v!=True:
            raise ValueError("not currently at objective")            
        l=pos.getLength()
        x,y=pos.getxy()
        pos.gui.B("Objective/Active").v=False
        newlen=ms.P('Pos/cavity length').v=l-pos.gui.P("Objective/offset z").v
        set_target_pos((x,y))
        pos.setLength(newlen)
        pos.setxy(x,y)        
    elif state=="move to objective":
        if pos.gui.B("Objective/Active").v!=False:
            raise ValueError("not currently at cavity")
        l=pos.getLength()        
        if l < 3500:
            raise ValueError("Please make the cavity longer first")
        x,y=pos.getxy()
        pos.gui.B("Objective/Active").v=True  
        newlen=ms.P('Pos/cavity length').v=l+pos.gui.P("Objective/offset z").v
        set_target_pos((x,y))
        pos.setLength(newlen)        
        pos.setxy(x,y)
    else:
        raise NameError("State %s does not exist"%str(state))
       
    #set new state
    try:
        state=states.pop()
    except:
        state="idle"
    statem_loop.setPause(pause)
    laststates.append(state)
    laststates=laststates[-10:]
    try:
        ss=laststates[-2]
        if not ss in timings:
            timings[ss]=0
        timings[ss]+=time.time()-lt        
        lt=time.time()
    except:
        pass

    return state
  

#%%

def start_statemachine(*args):
    global states,state    
    states=[]
    state="startloop"
    statem_loop.start()
ms.A("Main/Start statem").a=start_statemachine    

#%%
def move_to_cavity(*args):
    force_next_state("move to cavity")
ms.A("Pos/Move to Cavity").a=move_to_cavity
def move_to_objective(*args):
    force_next_state("move to objective")
ms.A("Pos/Move to Objective").a=move_to_objective
#%%
def do_save(*args):
    """ save configuration of the scan program AND the current measurement """
    ms.save_cfg()
    if hasattr(mm,"ms"):
        mm.ms.save_cfg()
    if hasattr(mm,"gui"):
        mm.gui.save_cfg()        
    if hasattr(pos,"gui"):        
        pos.gui.save_cfg()        
    if hasattr(lock,"gui"):
        lock.gui.save_cfg()             
ms.A2("Save config").a=do_save

#%%
def clear_graphs(*args):
    ms.C("Measured Values").clear()
    ms.C("Current Values").clear()
    ms.C("measurement times").clear()
    ms.C("Stddev of Values").clear()
ms.A2("Clear Graphs").a=clear_graphs

#%%
def close(*args):
    global pos,mm,lock,scan
    try:
        del mm
        del scan_globals.mm    
    except:
        pass
    try:    
        del scan
        del scan_globals.scan_data
    except:
        pass
    try:    
        del pos
        del scan_globals.pos
    except:
        pass
    try:    
        del lock
        del scan_globals.lock 
    except:
        pass
    
ms.A2("Close").a=close    
#%%
ms.S("Infos/Description")
ms.S("Infos/Filter")
ms.S("Infos/Laser")
ms.S("Infos/Other")
ms.S("Infos/Sample")

#%%
#def reconnect_winspec(*args):
#    if winspec:
#        pool.apply(mm.reset)
        
#%%        
load(name=ms.S("Data/Temp Name").v)
#%%
init_positioners()
#%%
ms.Choose("Measure/Measure module").v="none"
reinit_m()
#ms.A('Measure/Set_Winspec').a=reconnect_winspec
#%%
set_lock()
#%%
statem_loop=ms.g("loop:statemachine").setControl("Main/Statem Running",setControlToCurrentState=True).setControlPause("Main/Pause")
statem_loop.a=statemachine
#%%
start_statemachine()
#%%
#ddir="C:/Users/H240/Dropbox/Cavity/data/"
#%%
#Overview("old/Overview").load(ddir+"CNT20/A1")
#%%
#Overview("old/A2").load(ddir+"CNT20/A2")
#%%
#Overview("old/Overview").load(ms.S("old/Overview/File").v)
##%%
#Overview("old_frb6").load("../../../data/FRB6-full.h5")
##%%
#Overview("old_frb4").load("../../../data/FRB4-full.h5")
##%%
#Overview("old_ca17").load(ddir+"CA17-full.h5")
##%%
#Overview("old_cax12").load(ddir+"CAX12-full.h5")
##%%
#Overview("old_crx1").load(ddir+"CRX1-full.h5")
##%%
#Overview("old_CN8-A1").load(ddir+"CN8-A1-full.h5")
##%%
#Overview("old_CN8-R1").load(ddir+"CN8-R1-full.h5")
#%%
#Overview("old_CN6-R2").load(ddir+"CN6-R2-full.h5")
#%%
#Overview("old/CF1-A1").load(ddir+"/CF1-A1-full.h5")
##%%
#Overview("old/CF1-R1").load(ddir+"CF1-R1-full.h5")
##%%
#Overview("old/RZ4").load(ddir+"../CNT11-2/RZ4-full.h5")

#%%
#Overview("old_CF2-R1").load(ddir+"CF2-R1-full.h5")
##%%
#Overview("old_CF1-RF2").load(ddir+"CF1-RF2-full.h5")
##%%
#Overview("old_CN7-A12").load(ddir+"CN7-A12-full.h5")
#%%
#Overview("scan007y").load(r"E:\01_Data\2015-09-17\scan007")
#%%
#sd=ScanData(ddir+"CF1-R1-full.h5") 
#sd.load()

#%%
def plot_timings():
    global timings
    import matplotlib.pyplot as plt
    ind = np.arange(len(timings)) 
    #plt.figure()#mw.getFigure())
    plt.cla()
    plt.bar(ind, np.array(timings.values())/max(timings.values()), width=1)
    plt.xticks(ind+0.5,timings.keys(),rotation=90)
    plt.tight_layout()
    timings={}


#%%    
#plot_timings()
#%%
#ms.app.exec_()  

#%%
#from positioners.locator import Locator
#
##%%
#lo=Locator()
##%%
#lo.connect()