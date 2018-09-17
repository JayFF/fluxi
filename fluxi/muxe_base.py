# -*- coding: utf-8 -*-
"""
Created on Thu Jan 08 12:30:53 2015

@author: H240
"""
from __future__ import absolute_import, division, print_function, unicode_literals
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtCore import Qt
except ImportError:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtCore import Qt    
import weakref, queue

class MuxBase(object):   
    def __init__(self,id,fluxi):
        super().__init__()    
        self._hasbeenset=False
        self.id=id        
        self.type,self.name,self.pathstr=fluxi.parseId(id)
        self.getfluxi=weakref.ref(fluxi)
        self.opvals={}        
        self._action=None
        self.mutex = QtCore.QMutex()

        self._guiQueue=queue.Queue()
        
        self.options={
            #"Limits/Min":{"type":"float","value":float("-inf")},
            #"Limits/Max":{"type":"float","value":float("+inf")},
            #"Limits/Step":{"type":"float","value":0},
            #"Appearance/Color":{"type":"color","value":0},
            #"Limits/Color":{"type":"color","value":0}
            "Info/Tags":{"type":"str","value":""},
            "Info/Help":{"type":"str","value":""},
            "Save/Save Value":{"type":"bool","value":True},            
            "Default/Ask if unset":{"type":"bool","value":True},          
        }
        
        
    def addSelectionHandler(self):
        #TODO:remove?
        #self.p.itemActivated.connect(self.show_properties)
        pass
        
    @property
    def v(self):
        return self.get()
        
    @v.setter
    def v(self, value):
        self.set(value)
    
    def get(self):
        return self.value
        
    def set(self,value):
        self.value=value
        self._hasbeenset=True
        self._requestRedraw()
        return self
        
    def action(self,function):#:Callable
        if not callable(function):
            raise ValueError("can't set action: not a callable (function)")
#TODO:
#        if self.action and not noaction:
#            import inspect
#            num_args=len(inspect.getfullargspec(self.action).args)+len(inspect.getfullargspec(self.kwonlyargs).args)
#            if num_args==0:
#                self.action()
#            elif num_args==1:
#                self.action(self.value)
#            else: 
#                self.action(self,self.value)
        self._action=function
        return self

        
    def emitChanged(self,*args):      
        if self._action:
            try:
                self._action(self, self.value)
            except Exception:
                import sys
                self._errinfo=sys.exc_info()
                self.requestDrawAction(self.showError)
                raise
        return self
        
    def showError(self):
        import traceback
        eT, eV, eTB = self._errinfo
        tbs=traceback.extract_tb(eTB)[1:]
        try:
                
            win=self.getfluxi().openPopup("%s in %s" % (eT.__name__,self.name),"",self)
            
            t=QtGui.QLabel()
            t.setText("%s"%eV)
            win.layout.addWidget(t)        
            
            t=QtGui.QTreeWidget()
            t.setStyleSheet("background: transparent;")# border: 1px solid #000000;border-radius:0;")
            t.setHeaderHidden(True)
            t.setRootIsDecorated(False)
            t.setColumnCount(2)
            t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            #wid.setAlternatingRowColors(True)
    
            win.layout.addWidget(t)
            win.layout.addStretch()
            fnt=QtGui.QFont("MonospaceFont",7);
            fnt.setStyleHint(QtGui.QFont.TypeWriter)
            for fname,lnum,func,source in tbs:
                if fname[0]=="<":
                    fname=r"input"
                item = QtGui.QTreeWidgetItem(t.invisibleRootItem())
                item.setExpanded(True)                        
                w=QtGui.QLabel()
                w.setText("<pre>%s</pre>"%source)
                #w.setStyleSheet("color:rgba(0,0,0,100)")
                w.setCursor(Qt.PointingHandCursor)
                w.setToolTip("<pre>%s</pre>"%source)
                t.setItemWidget(item,0,w)       
                
                item = QtGui.QTreeWidgetItem(item)
                w=QtGui.QLabel()
                w.setText("<pre>in %s@%s(%d)</pre>"%(func,fname[fname.rfind("/")+1:],lnum))
                w.setToolTip("<pre>in %s@%s(%d)</pre>"%(func,fname,lnum))
                w.setStyleSheet("color:rgba(0,0,0,100)")
                w.setCursor(Qt.PointingHandCursor)
                t.setItemWidget(item,0,w)           
    
            #%%
            
    
            #t.resizeColumnToContents(0)
            #t.resizeColumnToContents(1)
            
            #%%
            
            height=t.sizeHintForRow(0) * t.invisibleRootItem().childCount()*2 + 2 * t.frameWidth()
            t.setMinimumHeight(height )
            #%%
            win.resize(200,height+70)            
            #self.getfluxi().openPopup("%s in %s" % (eT.__name__,self.name),"<style>b{color:#0000ff};*{font-size:20px}</style><p>%s</p><ul>%s</ul>"%(eV,est),self)
        except: 
            pass
        
    def _isGuiThread(self):
        return QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        #http://qt-project.org/doc/qt-4.8/threads-qobject.html
        
    def _requestRedraw(self):
        """ tell the fluxi that we want to redraw this widget """
        self.getfluxi().request_redraw(self)
      
    def remove(self):
        self.delete()
        self.getfluxi().removeElement(self.id)
    def delete(self):
        pass
    def __del__(self):
        self.delete()

    @property
    def a(self):
        return self.function
    @a.setter
    def a(self, function):
        self.action(function)
        
    def _is_in_main_thread(self):
        """ Check if called from main thread"""
        if not self._isGuiThread():
            raise Exception("Call this method only from main thread. Not from e.g. a Background loop")      
    def __repr__(self):
        #return "%s(%r)" % (self.__class__, self.__dict__)
        return "%s(%s)" % (self.__class__, self.name)
        
    def __str__(self):
        return "%s (%s) = %s" % (self.id, self.type, str(self.v))
        
    def _do_draw_actions(self):
        try:
            while True:
                func,args,kwargs=self._guiQueue.get_nowait()          
                func(*args,**kwargs)
        except queue.Empty:
            pass
            
        
    def requestDrawAction(self,action, *args,**kwargs):
        """ execute function 'action' with *args and **kwargs in the GUI thread (before drawing operations)"""
        self._guiQueue.put((action,args,kwargs))
        self._requestRedraw()
        return self
        
    def default(self,defaultValue):
        if not self._hasbeenset:
            self.set(defaultValue)
            self._hasbeenset=True
        return self
       
    ########### options

    def set_opt(self,name,value):
        try:
            return getattr(self,"set_opt_%s"%name.replace("/","_"))(value)
        except AttributeError:
            self.opvals[name]=value
        return self

    def set_opts(self,opts):
        #print("set opts",self.id, opts)
        #o={n:self.options[n]["value"] for n in self.options}
        #o.update(self.opvals)        
        #o.update(opts)
        for n in opts:
            self.set_opt(n,opts[n])
        return self
        
    def get_opt(self,name):
        try:
            return getattr(self,"get_opt_%s"%name.replace("/","_"))()
        except AttributeError:
            try:
                return self.opvals[name]
            except:
                return self.options[name]["value"]
        
    def get_opts(self):
        vals={}
        for n in self.options:
            if self.options[n]["value"]!=self.get_opt(n):
                vals[n]=self.get_opt(n)
        return vals
        
    def _gui_opt_changed(self,param,value):
        name=param.id
        try:
            getattr(self,"_gui_opt_changed_%s"%name.replace("/","_"))()
        except AttributeError:    
            self.set_opt(name,value)
        
    def display_dialog(self,*args):
        #TODO
        try:
            opgui=self.getfluxi().opgui
        except AttributeError:
            from fluxi import Fluxi
            opgui=self.getfluxi().opgui=Fluxi("Settings",type_="dialog")
        
        opgui.win.show()
        for n in self.options:        
            param=opgui.BasicParam(n,type=self.options[n]["type"])
            param.v=self.opvals[n]
            param.a=self._gui_opt_changed
    
    def draw(self):
        pass
#    def opt_changed_Limits_Min(self,value):
#        print("it was changed to ",value, ", dude")
    def __eq__(self,other):
        """ warn when we want to compare this method, most of the time someone forgot .v """
        if not isinstance(other,MuxBase):
            raise ValueError("Trying to compare Mux with something that is not a Mux. You probably wanted to compare the value (.v)")
                    