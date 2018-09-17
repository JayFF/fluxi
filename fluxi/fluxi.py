# -*- coding: utf-8 -*-
"""
fluxi - creating scientific measurment software in seconds
https://github.com/fluxiresearch/fluxi
"""
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtCore import pyqtSlot as Slot,pyqtSignal as Signal,Qt
except ImportError: 
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtCore import pyqtSlot as Slot,pyqtSignal as Signal,Qt
from pyqtgraph.dockarea import Dock, DockArea
import time,re,sys
import fluxi.helper,fluxi.muxe,fluxi.muxe_misc,fluxi.muxe_base,fluxi.ptree
import json,weakref
from base64 import b64encode,b64decode
from fluxi.helper import dict_update
import fluxi.hotfixes
#%%
    
def creator(func):
    """ A decorator to check if the thing exists and to execute the creation in the main thread"""
    def new_func(self,name,value=None,action=None,values=None,*args, **kwargs):
        try:        
            m=self.muxe[name]
            if values!=None:
                m.setValues(values)#TODO:this should not be here
            if value!=None:
                m.v=value        
            if action!=None:
                m.a=action
            return m
        except KeyError:
            #print func.__name__
            if value!=None:
                kwargs["value"]=value                      
            if values!=None:
                kwargs["values"]=values
            if action!=None:
                kwargs["action"]=action                
            if self._isGuiThread():
                self.muxe[name]=func(self,name,*args,**kwargs)                
            else:
                args=(name,)+args
                self.muxe[name]=self._callInMainThread(func.__name__,*args, **kwargs)
                #print "in main thr",self.muxe[name]
            return self.muxe[name]
    new_func.__name__ = func.__name__
    return new_func      

class Fluxi(QtCore.QObject):
    """ 
    The main Fluxi object
    
    Hosting a window with flexible docks, Charts, Parameters and so on...
    
    Create a window with title ``title``
    
    Parameters
    ----------
    title : title of the window
        Also used for the default name of the config file


    Examples
    --------
    
    Create a window and add a Parameter and a chart:
    
    >>> fl=Fluxi("Window name")
    >>> fl.P("A Parameter")
    >>> fl.C("I'm a chart")   
    """      
    _fluxis=weakref.WeakValueDictionary()
    app=None
    def __init__(self,title,parentfluxi=None,type_="main",win=None,show=True):  
        """ Create a window with title ``title`` """

        super().__init__()
        self.r_find_groups=re.compile("(.*)/(.*)")
        self.r_find_type=re.compile("([^:]*):(.*)")
        
        self._startapp()
        if win==None:
            if type_=="dialog":
                win=BaseDialog(title=title)
            else:
                win=BaseWindow(title=title)
        self._parentfluxi=parentfluxi
        self.namespace=title
        self._fluxis[title]=self
        self.win=win
        win.sigClose.connect(self._onclose)
        self._errmsgs={}
        self.muxe={}
        self.redraw_list={}
        self.cfg={}
        self._lastlogmsg=None
        
        self.load_cfg()
        self.B("Fluxi/Save on close").v
        me=weakref.ref(self)
        self.A("Fluxi/Save Config").a=lambda p, v: me().save_cfg()
        self.B("Fluxi/window always on top").default(True).a=lambda p, v: me()._set_always_on_top(self.B("Fluxi/window always on top").v)
        self._set_always_on_top(self.B("Fluxi/window always on top").v, show = show)
        
        
        self.drawtimer=QtCore.QTimer(timeout=self._redraw)
        self.drawtimer.start(1./30*1000)
        
        if show:
            self.win.show()

    @classmethod
    def _startapp(self):
        """ start the app in the console main loop (interactive mode is preserverd) or in its own when not available"""
        if not self.app:
            import pyqtgraph as pg
            fluxi.helper.tweak_ipython()
            
            pg.setConfigOption('background', 'w')
            pg.setConfigOption('foreground', 'k')
            pg.setConfigOption('leftButtonPan',False)
            #pg.setConfigOption('antialias',True)
            
            self.app = QtCore.QCoreApplication.instance()
            if self.app is None:
                self.app = QtGui.QApplication([])
            QtCore.QTimer.singleShot(0,prepare_excepthook)    
            #set Windows taskbar group
            #http://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105
            import ctypes
            #myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
            myappid = 'fluxiresearch.fluxi'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            #TODO: move somewhere else            
            self.app.setStyleSheet("""
            QPushButton  {
                border: 1px solid #000;
                padding:2px 5px;
                background:rgb(240,240,240);
                border-radius: 3px; margin:1px 5px;
            }
            QPushButton:pressed {
                background-color: rgb(200, 200, 200);
            }            
            """)            
    
    def _onclose(self):
        if self.B("Fluxi/Save on close").v:
            self.save_cfg()    
            
    def _set_always_on_top(self,ontop,show=True):
        if ontop:
            self.win.setWindowFlags(self.win.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.win.setWindowFlags(self.win.windowFlags() ^ QtCore.Qt.WindowStaysOnTopHint)
        if show:
            self.win.show() #window is closed, reshow it
    
    def g(self,name):
        """gets or creates an element"""
        try:        
            return self.muxe[name]
        except KeyError:
            return self._createMux(name)
            
    def __getitem__(self, id):
        return self.g(id)
    def __len__(self):
        return len(self.muxe)

    def __iter__(self):
       for n in self.muxe:
          yield n

    def parseId(self,id): 
        #print("searching:",id)
        r=self.r_find_type.match(id)
        try:
            type_=r.group(1)
        except:
            print("error creating",id)
            raise
        name=r.group(2)            
        try:        
            r=self.r_find_groups.match(name)
            path=r.group(1)
            name=r.group(2)
        except AttributeError:
            path=""
            pass
        return type_,name,path
    mapping={
        "f":fluxi.muxe.MuxBaseParam,
        "tree":fluxi.ptree.MuxTree,
        "loop":fluxi.muxe_misc.MuxBgLoop,
        "slowloop":fluxi.muxe_misc.MuxSlowLoop,
        "table":fluxi.muxe.MuxTable,
        "im":fluxi.muxe.MuxImg,
        "save":fluxi.muxe.MuxDump,
        "g":fluxi.muxe.MuxG,
        "c":fluxi.muxe.MuxC,
        "list":fluxi.muxe.MuxList,
        "crosshair":fluxi.muxe_misc.MuxCrosshair,
    }
    @creator    
    def _createMux(self,id):
        type_,name,path=self.parseId(id)
        #print("creating",type_,"with name",name,"under",path)
        if type_ in self.mapping:
            self.muxe[id]=self.mapping[type_](id,fluxi=self)
        else:
            self.muxe[id]=fluxi.muxe.MuxBaseParam(id,fluxi=self)
        return self.muxe[id]
        
    def F(self,name):
        """ create a Floating Point Number Input Parameter """
        return self.g("f:"+name) 
    def P(self,name):
        """legacy alias for F"""
        return self.g("f:"+name)          
    def D(self,name):
        return self.g("d:"+name)  
    def Int(self,name):
        return self.g("i:"+name)            
    def B(self,name,**kwargs):
        return self.g("b:"+name)
    def S(self,name,**kwargs):
        return self.g("s:"+name)           
    def A(self,name):
        return self.g("a:"+name)
    def Choose(self,name):
        return self.g("l:"+name)     
    def A2(self,name):
        return self.g("a:"+name)
    def C(self,name):
        return self.g("c:"+name)
    def Tree(self,name):
        return self.g("tree:"+name)
    def List(self,name):
        return self.g("list:"+name)
    def G(self,name):
        return self.g("g:"+name)
    def Dump(self,name):
        return self.g("save:"+name)
    def Im(self,name):
        return self.g("im:"+name)
    def Table(self,name):
        return self.g("table:"+name)

        
    #route=Signal(object,object)
    _route_return=None
    _route_mutex = QtCore.QMutex()
    def _callInMainThread(self,funcname,*args,**kwargs):
        if not self._isGuiThread():
            #print "routing it"
            self._route_mutex.lock();
            QtCore.QMetaObject.invokeMethod(self, "_remoteCall", QtCore.Qt.BlockingQueuedConnection,#AutoConnection,DirectConnection
                QtCore.Q_ARG(str, funcname),
                QtCore.Q_ARG(object, args),
                QtCore.Q_ARG(object, kwargs),
            )
            rv=self._route_return       
            self._route_mutex.unlock()
            return rv
        else:
            return getattr(self, str(funcname))(*args,**kwargs)
        
    @Slot(str,object,object)
    def _remoteCall(self,name,args,kwargs):
        #self.retvals[rid]=getattr(self, name)(*args,**kwargs)
#        print name,args,kwargs
#        print type(args)
        self._route_return=getattr(self, str(name))(*args,**kwargs)
        #print self._route_return   

    def get_values(self):
        vals={}
        for n in self.muxe:
            try:
                if self.muxe[n].get_opt("Save/Save Value"):
                    vals[n]=self.muxe[n].v        
            except:
                pass
        return vals
            
    def get_cfg(self):
        opts={}
        for n in self.muxe:
            #print(n)
            opts[n]=self.muxe[n].get_opts()
        from . import __version__
        cfg={"muxe":opts,"fileversion":__version__,"docks":self.win.area.saveState(),"win":b64encode(self.win.saveGeometry().data()).decode('ascii')}
        return cfg
                   
    def save_cfg(self,filename=None,prefix="",postfix=".cfg.json"):
        """ 
        Save values of all parameters and the layout of the gui.
        
        The values and layout is automatically restored on the next start of the GUI.
        
        By default the file ``fluxiname.values.json`` in the current
        working directory will host the values of all parameters.
        The file ``fluxiname.cfg.json`` in the current working directory 
        saves the window layout and configuration of all parameters.
        """
        if filename==None:
            filename=prefix+self.namespace+postfix        
        fluxi.helper.save_json(self.get_cfg(), filename)
        self.save_values()

    def load_cfg(self,filename=None,prefix="",postfix=".cfg.json"):
        if filename==None:
            filename=prefix+self.namespace+postfix    
        try:
            with open(filename, 'r') as f:                
                cfg=json.load(f)
                self.cfg=cfg
                self._restoreWindow()
                self._restoreDocks()                  
                if cfg["fileversion"]=="0.93":
                    self.__load_legacy(filename,prefix,postfix)
                else:                    
                    for id in cfg["muxe"]:
                        if "loop:" not in id:
                            self.g(id).set_opts(cfg["muxe"][id])
                    self.load_values()                  
        except IOError:
             self.cfg={}
             
    def save_values(self,filename=None,prefix="",postfix=".values.json"):
        if filename==None:
            filename=prefix+self.namespace+postfix          
        from . import __version__
        cfg={"fileversion":__version__,"values":self.get_values()}
        fluxi.helper.save_json(cfg, filename)             
             
    def load_values(self,filename=None,prefix="",postfix=".values.json"):
        if filename==None:
            filename=prefix+self.namespace+postfix            
        try:
            with open(filename, 'r') as f:                
                cfg=json.load(f)
                #print(cfg)
                for id in cfg["values"]:
                    if "loop:" not in id:
                        self.g(id).v=cfg["values"][id]
        except IOError:
             pass
             
    def __load_legacy(self,filename=None,prefix="",postfix=".cfg.json"):
        if filename==None:
            filename=prefix+self.namespace+postfix    
        try:
            with open(filename, 'r') as f:
                cfg=json.load(f)
        except IOError:
             cfg={}
        loadtypes= {"int":"i","bool":"b","float":"f","str":"s","list":"l"}
        if "muxe" in cfg:
            for name in cfg["muxe"]:
                odic=cfg["muxe"][name]
                if "type" in odic and odic["type"] in loadtypes:
                    self.g("%s:%s"%(loadtypes[odic["type"]],name)).v=odic["value"]
        self.cfg=cfg
            
    def set_cfg(self,newcfg):
        cfg=self.get_cfg()
        try:
            dict_update(cfg,newcfg)
        except KeyError:            
            pass
        if "muxe" in cfg:
            for n in cfg["muxe"]:
                odic=cfg["muxe"][n]
                if "type" in odic and odic["type"] in ["int","bool","float","str","list"]:
                    self.BasicParam(n,**odic)
        
    @classmethod
    def get_values_all(self,prefix=None):
        """ get the configuration of all fluxis """
        return {n:self._fluxis[n].get_values() for n in self._fluxis}
    
    def log(self,msg,type="debug"):
        print("logging",msg)
        #TODO: improve
#        lo=self.List("Log")
#        #log.moveCursor(QtGui.QTextCursor.End) 
#        if not hasattr(lo,"_lastmsg") or lo._lastmsg!=msg:
#            lo.addParent([msg,1,time.strftime("%d. %H:%M:%S")])
#        else:
#            label=QtGui.QLabel(msg)
#            label.setWordWrap(True)            
#            lo.addChild([msg,None,time.strftime("%d. %H:%M:%S")],widgets={0:label})
#        lo._lastmsg=msg
        #sb = log.verticalScrollBar()
        #sb.setValue(sb.maximum())       
            
#    @staticmethod
#    def exit_program(self):
#        """ exits the app, but you cannot restart afterwards. Then the ipython loop hangs"""
#        #TODO: does not work
#        self.app.aboutToQuit.connect(self.app.deleteLater)
#        self.app.quit()
#        sys.exit(0)

    def _restoreWindow(self):
        if "win" in self.cfg:         
            self.win.restoreGeometry(b64decode(self.cfg["win"]))
            #TODO: movetosecond screen  
            
    def _restoreDocks(self):
        if "docks" not in self.cfg:
            return
        self.__docks=[]
        def get_docks(e):    
            """ get all docks from a serialized pyqtgraph saved docks object """
            global docks
            if type(e)==dict:
                docks=get_docks(e['main'])
                for i in e['float']:
                    get_docks(i[0])
                return
            if e[0]=='dock':
                self.__docks+=[e[1]]     
                return
            for c in e[1]:
                get_docks(c)
            return 
        
        get_docks(self.cfg["docks"])    
        for d in self.__docks:
            self._createDockIfNA(d)
        try:
            self.win.area.restoreState(self.cfg["docks"])
        except:
            self.log("could not restore docks")
            raise
        
    def _isGuiThread(self):
        return QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        
    def _createDockIfNA(self, name,**kwargs):
        """ Create the Dock with the specified name if it is not there yet """    
        containers, docks = self.win.area.findAll()
        if name in docks:
            return docks[name]
        else:
            dock=Dock(name, closable=True,**kwargs)
            #self.dock.addWidget(widget)
            self.win.area.addDock(dock, **kwargs)#pos,relativeTo)  
            return dock     
    
    def logError(self,msg=None,details=None):
        pass
        #TODO: implement again
#        lo=self.List("Log")     
        #log.moveCursor(QtGui.QTextCursor.End) 
#        self.dbg("lastError",msg)
#        self.dbg("lastErrorTb",details)        
#        timest=time.strftime("%d. %H:%M:%S")
#        if not msg in self._errmsgs:
#            it=lo.addParent([msg,"",timest])
#            it.setForeground(0,QtCore.Qt.red)
#            it.setData(1,QtCore.Qt.DisplayRole,1)
#            lo.addChild([details,"",40])
#            self._errmsgs[msg]=it
#        else:
#            p=self._errmsgs[msg]
#            try:
#                num=p.data(1,QtCore.Qt.DisplayRole).toPyObject()  
#            except:
#                num=p.data(1,QtCore.Qt.DisplayRole)#this is enough in newer pyqt versions?
#            c=num+1                
#            p.setData(1,QtCore.Qt.DisplayRole,c)
#            p.setData(2,QtCore.Qt.DisplayRole,timest)
#            if c<100:
#                lo.addChild(["","",timest],parent=p)
        
        
    def removeElement(self,name):
        """ remove a Mux """
        self.muxe[name].delete()        
        del self.muxe[name]

    def request_redraw(self,mux):
        self.redraw_list[mux.id]=mux
        
    def _redraw(self):
        """redraw all elements that have requested this in the last period"""       
        for n in self.redraw_list.copy():
            ob=self.redraw_list[n]
            if ob is not None:
                self.redraw_list[n]=None
                try:
                    ob._do_draw_actions()
                    ob.draw()                        
                except:
                    self.log("there was an error drawing %s" %n)
                    #self.wait(0.3)
                    raise
    
    def wait(self,seconds):
        QtGui.QApplication.processEvents()
        time.sleep(seconds)
        QtGui.QApplication.processEvents()
            
    def __del__(self):
        #print("closing Fluxi")
        self._deinit()
        
    def _deinit(self):
        self.drawtimer.stop()
        #wait for last draws to happen
        self.wait(0.1)#TODO: a bit hacky, improve
        li=self.muxe.copy()
        #print("deiniting",li)
        for n in li:
            if li[n].type in ["Loop","SlowLoop"]:
                #print("delete", n)                
                li[n].delete()
                self.removeElement(n)
        time.sleep(0.1)
        li=self.muxe.copy()
        for n in li:
#            print("delete", n)
            self.removeElement(n)
        del self._fluxis[self.namespace]
        
    _mutexes={}
    def create_mutex(self,name):
        mutex=QtCore.QMutex()
        self._mutexes[name]=mutex
        return mutex            
        
    def show_dialog(self,title,yes_t='Yes',no_t='No'):
        
        mb=QtGui.QMessageBox()
        mb.setWindowTitle(title)
        mb.setText(title)
        #mb.setInformativeText('aaa')
        yo = mb.addButton(yes_t, QtGui.QMessageBox.YesRole)
        mb.addButton(no_t, QtGui.QMessageBox.NoRole)#no=
        mb.setIcon(QtGui.QMessageBox.Question)
        mb.show()
        mb.raise_()
        mb.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        mb.exec_()
        return mb.clickedButton()==yo

    def inputDialog(self,title,yes_t='Yes',no_t='No'):
#        win=BaseDialog(title)
#        mb=BaseDialog(parent=self.win,title=title)
#        mb=QtGui.QMessageBox()
#        mb.setWindowTitle(title)
#        mb.setText(title)
#        #mb.setInformativeText('aaa')
#        yo = mb.addButton(yes_t, QtGui.QMessageBox.YesRole)
#        mb.addButton(no_t, QtGui.QMessageBox.NoRole)#no=
#        mb.setIcon(QtGui.QMessageBox.Question)
#        mb.show()
#        mb.raise_()
#        mb.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
#        mb.exec_()
#        return mb.clickedButton()==yo      
        pass


    def openPopup(self,title,text,mux):
        widget=mux.p.widget
        wr=widget.rect()
        point=QtCore.QPoint(wr.center().x()-20,wr.bottom()-5)
        #point = widget.rect().bottomRight()
        point = widget.mapToGlobal(point)
        popup = Popup(widget.window(), point,title,text)
        popup.show()
        return popup
             
class Popup(QtGui.QWidget):
    def __init__(self,parent,point,title,text=""):
        QtGui.QWidget.__init__(self, parent)
        self._close = QtGui.QPushButton("✕")
        self._close.clicked.connect(self.closePopup)
        
        _title=QtGui.QLabel()
        _title.setText(title)  

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(_title)
        hbox.addStretch(1)        
        hbox.addWidget(self._close)

        vbox = QtGui.QVBoxLayout()
        #vbox.addStretch(1)
        vbox.addLayout(hbox)
        if text!="":
            self.content=QtGui.QLabel()
            self.content.setText(text)
            vbox.addWidget(self.content)
        
        self.layout=vbox   
        self.setStyleSheet("""
        QWidget {
            border: none;
            border-radius: 10px;
            
            margin: 2 2;
            color:#000
            }
        .QPushButton {
            border: none;
            margin: -4 -2;
            background:transparent;
            }
        """)
        vbox.setContentsMargins(0,10,0,0)

        self.setLayout(vbox)
        self.setMinimumSize(130, 30)
        self.adjustSize()
        
        #self.setWindowFlags(Qt.Popup)
        self.setWindowFlags(Qt.Popup | Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.move(point)
        
    def closePopup(self):
        self.deleteLater()
        
    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setPen(Qt.NoPen)
        #qp.setPen(QtGui.QColor(200, 200, 200, 255))
        qp.setBrush(QtGui.QColor(255, 100, 100, 255))
        qp.drawRect(0, 9, 1000, 1000)
        points = QtGui.QPolygon([
            QtCore.QPoint(5+5, 0),
            QtCore.QPoint(0+5, 10),
            QtCore.QPoint(10+5, 10)
        ])
        
        qp.drawPolygon(points) 
        
        qp.end()
            
     
#%% exceptions handling

class Messenger(QtCore.QObject):    
    throw = Signal(object)    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.throw.connect(self.show_error)
    @Slot(object)
    def show_error(self,err):          
        msg,tb=printErrorToConsole(err)#,add=" somewhere in Qt")
        for f in Fluxi._fluxis.values():
           f.logError(msg=msg,details=tb) 


import fluxi.traceback
import traceback
er=None
def printErrorToConsole(err,add=""):   #ex_type, ex, tb
    global er
    er=err        
    print("-----\nAn error occured%s:"%add)
    try:      
        msg="%s:%s"%(err[0],err[1])    
        tb="".join(traceback.format_tb(err[2]))     
        print(tb,"\n",msg,"\n-----")
    except Exception as e:
        try:
            msg=fluxi.traceback.get_error(err)
            tb=fluxi.traceback.get_formatted_tb(err)
            print(tb,"\n",msg,"\n-----")
        except Exception as e:
            print("Could not print error",err[0],err[1],"\nformatting error: %s"%e)
            msg=""
            tb=""
    #traceback.format_exception
    
    sys.stdout.flush()
    return msg,tb
    

msg=Messenger()
def handle_excep(etype,evalue,tb):
    err=(etype,evalue,tb)
    msg.throw.emit(err)
    
#%% register an excepthook for qt. 
def prepare_excepthook():
    sys.excepthook = handle_excep  

class Evfilter(QtCore.QObject):
    #delkeyPressed = QtCore.pyqtSignal()
    # if (event.type() == QtCore.QEvent.MouseMove and source is self.label):
    def __init__(self,item,func):
        QtCore.QObject.__init__(self)
        self.item=item
        self.func=func
    def eventFilter(self,  obj,  event):
        global ev
        ev=event
        if ev.type()==QtCore.QEvent.MouseButtonPress:
            print("press", self.item, obj)
            self.func(obj,self.item,event)            
        #print "x"
        return False
        
def registerEvent(qobject,item,function):
    qobject.evfilter = Evfilter(item,function)
    qobject.installEventFilter(qobject.evfilter)        
def removeEvent(qobject):
    qobject.removeEventFilter(qobject.evfilter)
    
class BaseWindow(QtGui.QMainWindow):
    sigClose = QtCore.pyqtSignal()
    def __init__(self, parent=None,title="fluxi window"):
        QtGui.QMainWindow.__init__(self,parent)
        self.setWindowTitle(title)     
        self.area =area= DockArea()
        self.setCentralWidget(area)
        def close_function():
            pass
        self.close_function = close_function
        
    def closeEvent(self, event):
        msg = "Are you sure to quit? This will terminate all background loops."
        reply=QtGui.QMessageBox.question(self, 'Message', msg, 
                                         QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply==QtGui.QMessageBox.Yes:
            event.accept()
            self.close_function()
            self.sigClose.emit()
        else:
            event.ignore()   
           
    def bringToFront(self):
        # this will remove minimized status 
        # and restore window with keeping maximized/normal state
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)        
        # this will activate the window        
        self.activateWindow()      


class BaseDialog(QtGui.QDialog):
    sigClose = QtCore.pyqtSignal()
    def __init__(self, parent=None, title="fluxi window", content=None):
        QtGui.QDialog.__init__(self,parent)
        self.setWindowTitle(title)   
        self.area =area= DockArea()
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(area)

        layout.setContentsMargins(0,0,0,0)
        
        if not content is None:
            self.content = QtGui.QLabel()
            self.content.setText(content)
            self.content.setWordWrap(True)
            self.content.setMinimumSize(self.content.sizeHint())
            layout.addWidget(self.content)
        
        self.buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        layout.addWidget(self.buttons)
        
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        