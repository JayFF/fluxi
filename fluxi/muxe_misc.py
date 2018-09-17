# -*- coding: utf-8 -*-
"""

"""
try:
    from PyQt4 import QtCore
    from PyQt4.QtCore import pyqtSlot as Slot
    from PyQt4.QtCore import QObject
except ImportError:
    from PyQt5 import QtCore
    from PyQt5.QtCore import pyqtSlot as Slot    
    from PyQt5.QtCore import QObject
import numpy as np
import pyqtgraph as pg
import time,sys
from fluxi.muxe import MuxBase
#%%
class MuxSlowLoop(MuxBase):
    """A slow loop executed in the main thread. For anything <100Hz that takes less then approx 50ms"""
    minpause=0.001
    def __init__(self,id,fluxi):        
        super().__init__(id,fluxi)
        self.passes=0
        self.running=False
        self.timings=np.full((10,),np.NAN)
        self.timing=0        
        #self.a=action
        self._control,self._control_pause=None,None
        #self.control=control
        #self.control_pause=control_pause

        self.timer=QtCore.QTimer(timeout=self.loop,singleShot=True)
        
        self.setPause(1)
        #pause
        #self.setControlPause(control_pause)
        #if pause!=None:
        #    self.setPause(pause)
        #elif not control_pause:
        #   
        
        #on/off switch            
#        if start==True:
#            self.start()    
#            self.setControl(control,setControlToCurrentState=True)
#        elif start==False:
#            self.setControl(control,setControlToCurrentState=True)
#        else:
#            self.setControl(control)
        

    def loop(self,*args):
        if not self.running:
            return
        self.passes+=1
        t0=time.time()
        try:
            if self.action!=None:
                stop=self.action(self)
            else:
                stop=False
        except:
            self.stop()
            raise
#        finally:
#            if self.continueonerror
#TODO:            
        self.timing=time.time()-t0
        self.timings=np.roll(self.timings, -1)
        self.timings[-1]=self.timing
        pause=max(self._pause,self.timing,self.minpause)
        #self.getfluxi().dbg("p",pause)
        if not stop and self.running:
            #self.timer.singleShot(pause*1000, self.loop)       
            self.timer.start(pause*1000)
        else:
            self.stop()
    def start(self):
        if not self.running:
            self.running=True
            if self._control:
                self._control.v=True
            self.loop()
        return self
         
    def stop(self):
        if self.running:
            self.running=False
            if self._control:
                self._control.v=False
        return self
    def delete(self):
        if not hasattr(self,"alreadydeleted"):
            self.control=False
            self.control_pause=False
            self.stop()
            self.alreadydeleted=True

    def getTiming(self):
        return np.nanmean(self.timings)
        
    def setControl(self, control,setControlToCurrentState=False):
        if self._control:
            self._control.p.sigValueChanged.disconnect(self._on_control_change)
        if isinstance(control,str):
            control=self.getfluxi().B(control)                    
        self._control=control  
        if control: 
            if setControlToCurrentState:
                self._control.v=self.running
            else:
                if self._control.v:
                    self.start()
                else:
                    self.stop()       
            self._control.p.sigValueChanged.connect(self._on_control_change)
        return self
    def _on_control_change(self,p,v):
        if v:
            self.start()
        else:
            self.stop()
            

    def setControlPause(self, control):
        if self._control_pause:
            self._control_pause.p.sigValueChanged.disconnect(self._on_control_pause_change)
        if isinstance(control,str):
            control=self.getfluxi().P(control)     
        self._control_pause=control
        if control:            
            control.p.sigValueChanged.connect(self._on_control_pause_change)
            self.setPause(control.v)
        return self
    def _on_control_pause_change(self,p,v):
        self.setPause(v)
    @property
    def pause(self):
        return self._pause               
    def setPause(self,pause):
        self._pause=pause
        if self._control_pause:
           self._control_pause.v=pause 
    def every_nth(self,n):
        return self.passes%n==0            


    
             
import weakref
class LoopInThread(QtCore.QThread):
    #GIL and threads: http://stackoverflow.com/questions/1595649/threading-in-a-pyqt-application-use-qt-threads-or-python-threads
    guineedsupdate = QtCore.pyqtSignal(object)
    ended = QtCore.pyqtSignal()
    died= QtCore.pyqtSignal(object,object)
    minpause=0
    def __init__(self,loopmux=None):
        QtCore.QThread.__init__(self)
        self.running=True
        self.passes=0
        self.timing_length=30
        self.timings=np.full((self.timing_length,),np.NAN)
        #http://stackoverflow.com/questions/15176619/timing-the-cpu-time-of-a-python-program
        self._timer=time.clock#default_timer#perf_counter
        self.loopmux_ref=weakref.ref(loopmux)
        self.action=None
    def run(self):        
        #print "starting"
        while self.running:
            self.passes+=1
            t0=self._timer()
            try:
                if self.action is not None:
                    self.action(self.loopmux_ref())
            except Exception as e:
                print("except")
                self.died.emit(e, sys.exc_info())
                self.exit()
                raise
            #finally:
            #     TODO:if self.continueonerror
            self.timing=self._timer()-t0
            self.timings[self.passes%self.timing_length]=self.timing
#            self.timings=np.roll(self.timings, -1)
#            self.timings[-1]=self.timing
            if self.pause!=0:
                time.sleep(self.pause)        
        self.exit()
#    def run(self):
#        loop = 0
#        while not self.exiting:
#            time.sleep(self.loopMux.pause)
#            loop += 1
#            newdata=loop
#            try:
#                
#            self.guineedsupdate.emit(newdata)    
    def exit(self,error=False):
        self.ended.emit()
        #print("died")
#    def __del__(self):
#        self.quit()
#        self.wait()
#        self.exit()
        

             
class MuxBgLoop(MuxBase, QObject):    
    minpause=0.00001
    #http://qt-project.org/forums/viewthread/6567
    def __init__(self,id,fluxi):
        super().__init__(id,fluxi)  
        
        self.thread=LoopInThread(self)
        self.thread.finished.connect(self.stop)
        self.thread.died.connect(self.died)            

        self.running=False
#        self.a=action        
        self._control,self._control_pause=None,None
        
        self.setPause(1) 
        
        #pause
#        self.setControlPause(control_pause)
#        if pause!=None:
#            self.setPause(pause)
#        elif not control_pause:
#           self.setPause(1) 
        
        #on/off switch
#        if start==True:
#            self.start()    
#            self.setControl(control,setControlToCurrentState=True)
#        elif start==False:
#            self.setControl(control,setControlToCurrentState=True)
#        else:
#            self.setControl(control)
        
        
    @Slot(object,object)
    def died(self,exception,exc_info):
        #TODO: proper showing of errors
        #self.getfluxi().showError(exception)
        raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
        #raise exc_info[0],exc_info[1],exc_info[2]
            
    def start(self):
        #print ("starting",self.name)
        if not self.running:
            self.running=True               
            if self._control:
                self._control.v=True
            self.thread.start()      
    
    def stop(self):
        #print ("stopping",self.name)
        if self.running:
            self.running=False
            if self._control:
                self._control.v=False   
    @property
    def running(self):
        return self.thread.running
    @running.setter
    def running(self,v):
        self.thread.running=v
#    @property
#    def pause(self):
#        return self.thread.pause        
    @property
    def a(self):
        return self.action
    @a.setter
    def a(self, action):
        self.thread.action=action
        self.action=action  

    def delete(self):
        if not hasattr(self,"alreadydeleted"):
            self.control=False
            self.control_pause=False
            self.stop()
            self.thread.quit()
            self.thread.wait()        
            self.alreadydeleted=True

    def getTiming(self):
        return np.nanmean(self.timings)
        
    def setControl(self, control,setControlToCurrentState=False):
        if self._control:
            self._control.p.sigValueChanged.disconnect(self._on_control_change)
        #print type(control)
        if isinstance(control,str):
            control=self.getfluxi().B(control)
        self._control=control
        if control:
            if setControlToCurrentState:
                self._control.v=self.running
            else:
                if self._control.v:
                    self.start()
                else:
                    self.stop()
            self._control.p.sigValueChanged.connect(self._on_control_change)
        return self
        
    def _on_control_change(self,p,v):
        #print "och"
        if v:
            self.start()
        else:
            self.stop()
            
    def setControlPause(self, control):
        if self._control_pause:
            self._control_pause.p.sigValueChanged.disconnect(self._on_control_pause_change)
        if isinstance(control,str):
            control=self.getfluxi().P(control)     
        self._control_pause=control  
        if control:
            control.p.sigValueChanged.connect(self._on_control_pause_change)
            self.setPause(control.v)
        return self
    def _on_control_pause_change(self,p,v):
        #print "och"
        self.setPause(v)
        
    @property
    def pause(self):
        return self.thread.pause
    def setPause(self,pause):
        self.thread.pause=pause
        if self._control_pause:
           self._control_pause.v=pause
        return self
    def nth(self,n):
        """ returns true every nth pass """
        return self.thread.passes%n==0
    def every_nth(self,n,action):
        """ executes action every nth pass"""
        if self.thread.passes%n==0:
            action()
#    def getHz(self):
#        """ gets the frequency """
#        if self.loop.thread.passes%200==0:
#            t1=time.time()
#            -t1            
#            self.gui.C("kHz").add(200/())       
#            self.t0
#%%

from fluxi.helper import dict_update

class MuxCrosshair(MuxBase):
    """ An Crosshair """
    dragged = QtCore.pyqtSignal(pg.Point)
    def __init__(self,name,fluxi,value=None,opts=None,**kwargs): 
        super().__init__(name,fluxi)        
        self.type="Crosshair"
        self._style={
            'size':4,
            'pen':{"color":"g","width":2},
            'draggable':True
        }
        self.widget=self.mainwidget=Crosshair()
        self.update_style(self._style)
        if value is None:
            self.value=(0,0)
        else:
            self.value=value
        self.widget.dragged.connect(self._ui_element_changed)
        self._requestRedraw()
        
    def draw(self):
        if self.value is not None:
            self.widget.setPos(*self.value)
        
    def _ui_element_changed(self,pos,noaction=False):
        self.value=list(pos)
        if not noaction:
            self.emitChanged(pos)            
            
#    def __del__(self):
#        del self.widget    
            
    def attach(self,parentMux):
        #self.im.plot.getView().addItem(self.ch)
        parentMux.mainwidget.getView().addItem(self.widget)
        
    def update_style(self,style_dict):
        self._style=dict_update(self._style,style_dict)
        self.mainwidget.size=self._style["size"]
        self.mainwidget.pen=self._style["pen"]
        self.mainwidget.draggable=self._style["draggable"]
        if self._style["draggable"]:
            self.mainwidget.setCursor(QtCore.Qt.CrossCursor)
        else:
            self.mainwidget.setCursor(QtCore.Qt.ArrowCursor)
            
        
        
#%%        


class Crosshair(pg.GraphicsObject):
    dragged = QtCore.pyqtSignal(pg.Point)
    def __init__(self,size=4,pen='g',pos=None):
        super().__init__()
        self.size=size
        self.pen=pen
        self.draggable=True
        if pos!=None:
            self.setPos(*pos)
        
    def paint(self, p, *args):
        p.setPen(pg.mkPen(self.pen))
        p.drawLine(-self.size, 0, self.size, 0)
        p.drawLine(0, -self.size, 0, self.size)
    
    def boundingRect(self):
        return QtCore.QRectF(-self.size-3, -self.size-3, self.size*2+3, self.size*2+3)
    
    def mouseDragEvent(self, ev):
        if self.draggable:
            ev.accept()
            if ev.isStart():
                self.startPos = self.pos()
            pos=self.startPos + ev.pos() - ev.buttonDownPos()
            self.setPos(pos)
            self.dragged.emit(pos)    
        
    def __del__(self):
        self.parentWidget().removeItem(self)
        self.deleteLater()
        
 

             
#class MuxBgExecution(MuxBase):    
#    #http://qt-project.org/forums/viewthread/6567
#    def __init__(self,name,fluxi,action=None):        
#        super().__init__(name,fluxi)
#        self.type="MuxBgExecution"
#        self.update=update         
#        self.minpause=0.00001
#        self.control=None
#        self.thread=LoopInThread()
#        self.thread.finished.connect(self.stop)
#        self.thread.died.connect(self.died)
#
#    @Slot(object,object)
#    def died(self,exception,exc_info):
#        self.getfluxi().showError(exception)
#        raise exc_info[1], None, exc_info[2]
#            
#    def start(self):
#        if not self.running:
#            self.running=True               
#            if self.control:
#                self.control.vv=True
#            self.thread.start()      
#         
#    def stop(self):
#        if self.running:
#            self.running=False
#            if self.control:
#                self.control.vv=False   
#    @property
#    def running(self):
#        return self.thread.running
#    @running.setter
#    def running(self,v):
#        self.thread.running=v
##    @property
##    def pause(self):
##        return self.thread.pause        
#    @property
#    def a(self):
#        return self.action
#    @a.setter
#    def a(self, action):
#        self.thread.action=action
#        self.action=action  
#
#    def __del__(self):
#        self.stop()
#        if self.control:
#            self.control.p.sigValueChanged.disconnect(self._on_control_change)
#
#    def getTiming(self):
#        return np.nanmean(self.timings)
#        
#    @property
#    def c(self):
#        return self.control
#    @c.setter
#    def c(self, control):
#        if self.control:
#            self.control.p.sigValueChanged.disconnect(self._on_control_change)
#        self.control=control  
#        self.control.p.sigValueChanged.connect(self._on_control_change)
#        if self.control.v:
#            self.start()
#        else:
#            self.stop()
#        
#    def _on_control_change(self,p,v):
#        #print "och"
#        if v:
#            self.start()
#        else:
#            self.stop()
#            
#    @property
#    def c_pause(self):
#        return self.control_pause
#    @c_pause.setter
#    def c_pause(self, control):
#        if self.control_pause:
#            self.control_pause.p.sigValueChanged.disconnect(self._on_control_pause_change)
#        self.control_pause=control  
#        control.p.sigValueChanged.connect(self._on_control_pause_change)
#        self.thread.pause=control.v      
#    def _on_control_pause_change(self,p,v):
#        #print "och"
#        self.thread.pause=v
#    def every_nth(self,n):
#        return self.passes%n==0     
             
             
#%%
class ExecInThread(QtCore.QThread):
    #GIL and threads: http://stackoverflow.com/questions/1595649/threading-in-a-pyqt-application-use-qt-threads-or-python-threads
    guineedsupdate = QtCore.pyqtSignal(object)
    ended = QtCore.pyqtSignal(object)
    died= QtCore.pyqtSignal(object,object)
    def __init__(self,action):
        QtCore.QThread.__init__(self)
        self.running=True
        self._timer=time.clock#default_timer#perf_counter
        self.action=action
        self.start()
    def run(self):        
        print("starting in thread")
        t0=self._timer()
        try:
            if self.action!=None:
                self.action(self)
        except Exception as e:
            print("except")
            self.died.emit(e, sys.exc_info())
            self.exit()
            raise
        finally:
            self.running=False
        self.timing=self._timer()-t0
        self.exit()
    def exit(self,error=False):
        self.ended.emit(error)
        print("exited")
    def __del__(self):    
        self.exit()
        self.wait()        
##%%
#def test(thr):
#    fl._callInMainThread("test",11,12,x=13)
#%%
#thr=ExecInThread(action=test)