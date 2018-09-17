# -*- coding: utf-8 -*-
"""
Created on Thu Oct 30 18:16:01 2014

"Muxe": "Magic User eXperience Elements"

"""
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import str
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtCore import Qt
except ImportError:
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtCore import Qt
import numpy as np
import time
import pyqtgraph as pg
from fluxi.muxe_base import MuxBase




class MuxBaseParam(MuxBase):    
    def __init__(self,id,fluxi):        
        super().__init__(id,fluxi)
        from fluxi.ptree import mappedNames#,getChildGroup,ParamGroup                
        parent=self.getfluxi().g("tree:Parameters").mainwidget.invisibleRootItem()
        if len(self.pathstr)>0:
            parent=fluxi["group:%s"%self.pathstr].p.treeitem
        elif self.type!="group":
            parent=fluxi["group:General"].p.treeitem
        
        self.p=mappedNames[self.type].__call__(parent,self.name)#,digits=digits)
        self.p.sigValueChanged.connect(self._ui_element_changed)  
        self.p.sigContextMenu.connect(self._ui_context_menu_opened)  
        if self.type!="l":
            self.set(self.p.getValue())#TODO:
        self._hasbeenset=False
        self.contextMenu = QtGui.QMenu()
        ac=self.contextMenu.addAction("Remove Parameter")
        ac.triggered.connect(self._remove_action)
        
        ac=self.contextMenu.addAction("Properties")
        ac.triggered.connect(self.display_dialog)
        
        if self.type=="a":
            self.options.update({
                "Save/Save Value":{"type":"bool","value":False},
            })
        if self.type=="group":
            self.options.update({"Expanded":{"type":"bool","value":True}})            
        
    def _ui_context_menu_opened(self,ev):        
        self.contextMenu.popup(ev.globalPos())
        
    def _ui_element_changed(self,param,value,noaction=False):
        self.value=value
#        if self.type=="l":
#            print("_ui_element_changed",self.value)
        if self.type=="a":
            self.value=True
        if not noaction:
            self.emitChanged()
                
    def _remove_action(self,*args):    
        self.remove()
        
    def get(self):   
        #move this in a derived class later
        if self.type=="a" and self.value==True:#Latch button behaviour
            self.value=False
            return True
        return self.value
            
    def set(self, value):
        if self.type=="f":
            self.value=float(value)
        elif self.type=="s":        
            self.value=str(value)
        elif self.type=="i":
            self.value=int(value)        
        elif self.type=="l":
#            print ("val",self.type,value)
            self.value=str(value)                
        elif self.type=="b":
            if not isinstance(value, int):#bool is subclass of int
                raise ValueError("This needs to be an boolean (or an integer)")
            self.value=value
        else:
#            print ("valx",self.type,value)
            self.value=value
        self._hasbeenset=True
        self._requestRedraw()
        return self
        
    def draw(self):
        self.mutex.lock()
#        if self.id:
#            print (self.id,self.name,repr(self.value))
#        if self.type=="l":
#            print("draw_setvalue",self.value)
        self.p.setValue(self.value)     
        self.mutex.unlock()
        
    def setValues(self,values):
        self.values=[str(v) for v in values]
        self.requestDrawAction(self.draw_setvalues)
        if not hasattr(self,"value"):
            self.value=self.values[0]
        self.set(self.value)
        return self
        
    def draw_setvalues(self):   
#        print("draw_setvalues",self.values)
        self.p.setOptions(self.values)        
        
    def delete(self):
        if hasattr(self,"p"):
            self.p.remove()
            del self.p

    def addSelectionHandler(self):
        self.p.itemActivated.connect(self.show_properties)
           
    def get_opt_Expanded(self):
        return self.p.expanded
    def set_opt_Expanded(self,value):
        #print("set_opt_Expanded",value)
        self.p.expanded=value
        self.requestDrawAction(self.draw_expanded)
    def draw_expanded(self):   
        #print("draw_expanded",self.p.expanded)
        self.p.treeitem.setExpanded(self.p.expanded)      


class MuxDocked(MuxBase): 
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
    
    def createDock(self, widget,**kwargs):
        #super().__init__(name,fluxi)
        self.dock=self.getfluxi()._createDockIfNA(self.name,**kwargs)
        self.dock.addWidget(widget)
    def delete(self):
        #print("deleting dock et al")
        #layout.removeWidget(self.widget_name)
        if hasattr(self,"dock") and self.dock:
            self.dock.deleteLater()
            del self.dock        
        if hasattr(self,"mainwidget") and self.mainwidget:
            self.mainwidget.deleteLater()
            del self.mainwidget
        if hasattr(self,"plot") and self.plot:
            self.plot.deleteLater()
            del self.plot
          
class MuxC(MuxDocked):
    """ A running waveform chart like in Labview"""
    def __init__(self,name,fluxi,value=None,length=200,trim=15,**kwargs):
        super().__init__(name,fluxi)
        self.plot = pg.PlotWidget()       
        self.createDock(self.plot,**kwargs)
        self.curves={}
        self.trim=trim
        self.trim=False
        self.pad=50 # padding in %
        self.setLength(length)
        self.name=name
        self.mainwidget=self.plot
        self.type="Chart"
        self.addSelectionHandler()
        self.styles=[{"pen":pg.mkPen((0,0,0), width=1)},{"pen":(27,64,94)},{"pen":(94,2,2)},{"pen":(28,94,55)},{"pen":(85,23,71)}]
        self.arrpos=0
        self.roll=True
        
        self.options.update({
            "Save/Save Value":{"type":"bool","value":False},        
        })
        
#    def addCurve():
#        self.curves[]    
    def setLength(self,length):
        if int(length)<=0:
            raise ValueError("A length smaller than 1 was specified")
        self.length=int(length)
        self.arrs=np.full((1,self.length),np.nan)
    
    def fill(self,curvenum1,curvenum2,brush=(50,0,0,50)):        
        for i in range(max(curvenum1,curvenum2)):
            try:
                self.curves[i]                
            except:                
                self.curves[i]=self.plot.plot(**self.styles[min(i,len(self.styles)-1)])         
        fill=pg.FillBetweenItem(self.curves[curvenum1], self.curves[curvenum2], brush)
        self.plot.addItem(fill)
        
    def add(self,values):              
        try:
            L=len(values)
        except:
            values=[values]
            L=1
        if L>20:
            raise ValueError("More than 20 Lines")
        values=np.array(values)        
        #if more or less values than curves
        s=self.arrs.shape
        if s[0]<L:
            self.arrs=np.append(self.arrs, np.full([L-s[0], s[1]],np.nan),axis=0)
        if s[0]>L:
            values=np.append(values, np.full((s[0]-L,),np.nan))
        #if length to show was changed  
        s=self.arrs.shape  
        if s[1]!=self.length:
            if s[1]<self.length:
                self.arrs=np.append(np.full([s[0], self.length-s[1]],np.nan),self.arrs,axis=1)
            elif s[1]>self.length:
                self.arrs=self.arrs[:,-self.length:]          
        self.arrs[:len(values),self.arrpos]=values#TODO: move also the values that have not been set
        self.arrpos=(self.arrpos+1)%self.length
        self._requestRedraw()
        
    @property
    def v(self):
        return np.roll(self.arrs, -self.arrpos,axis=1)
    @v.setter
    def v(self, value):
        self.arrs=np.array(value)
        self.arrpos=0
        self._requestRedraw()
        
    def draw(self):
        if self.roll:
            arrs=self.v
        else:
            arrs=self.arrs
        for i in range(self.arrs.shape[0]):
            try:
                self.curves[i]                
            except:                
                self.curves[i]=self.plot.plot(**self.styles[min(i,len(self.styles)-1)])
            
            self.curves[i].setData(arrs[i])            

#        if self.trim:
#            x=np.array(self.arrs[0])
#            minv=np.percentile(x, self.trim)
#            maxv=np.percentile(x, 100-self.trim)
#            pad=abs(minv-maxv)*self.pad/100
#            self.curves[0].parentItem().parentItem().setYRange(minv-pad, maxv+pad)
    def mean(self):
        return np.nanmean(self.arrs,1)
        
    def draw_clear(self):
        self.plot.clear()
        self._requestRedraw()        
        
    def clear(self):
        self.setLength(self.length)        
        self.curves={}
        self.requestDrawAction(self.draw_clear)
        return self

        
class MuxG(MuxDocked):
    """ A graph"""
    def __init__(self,name,fluxi,trim=15,**kwargs):
        super().__init__(name,fluxi)
        self.plot = pg.PlotWidget()       
        self.createDock(self.plot,**kwargs)
        self.dock.addWidget(self.plot)
        self.curves={}
        self.trim=trim
        self.trim=False
        self.pad=50 # padding in %
        self.name=name
        self.mainwidget=self.plot  
        self.plot.addLegend()
        self.type="Graph"
        self.styles=[{"pen":(0,0,0)},{"pen":(152,214,160)},{"pen":(94,2,2)},{"pen":(28,94,55)}]
        self.datas={}
        #self.curve=self.plot.plot(name=curveName)
        #viewbox.setMouseMode(viewbox.RectMode)
        #    def mouseClickEvent(self, ev):
        #        if ev.button() == Qt.RightButton:
        #            self.autoRange()   

        self.options.update({
            "Save/Save Value":{"type":"bool","value":False},        
        })  
           
    def setMult(self,xs,ys=None):
        if ys is None:
            ys=xs
            xs=[None]*len(ys)
        for i in range(len(ys)):
            self.set(xs[i],ys[i],i=i)
    def set(self,xs,ys=None,i=0,dots=False):
        kwargs=self.styles[min(i,len(self.styles)-1)]
        if dots:
            kwargs={"pen":None, "symbolBrush":(255,0,0), "symbolPen":'w'}  
        if ys is None and xs is None:
            return
        if ys is None:
            ys=xs
            xs=np.arange(len(ys))
        if xs is None and not ys is None:
            xs=np.arange(len(ys))           
        #self.redraw_list[i]=True
        self.datas[i]={"xs":xs,"ys":ys,"kwargs":kwargs}
        self._requestRedraw()    
    @property
    def v(self):
        return self.datas
    @v.setter
    def v(self, value):
        self.datas=value
        self._requestRedraw()        
        
    def draw(self):  
        for n in self.datas:
            try:
                self.curves[n]
            except:
                self.curves[n]=self.plot.plot()
            v=self.datas[n]
            self.curves[n].setData(v["xs"],v["ys"],**v["kwargs"])
            
    def draw_clear(self):
        self.curves={}
        self.plot.clear()
        
    def clear(self):
        self.datas={}
        self.requestDrawAction(self.draw_clear)
        return self

class MuxDump(MuxBase):
    """ Dump some variables and they can be saved an displayed etc """
    def __init__(self,name,fluxi,value=None):
        self.name=name
        self.value=value
    @property
    def v(self):
        return self.value
    @v.setter
    def v(self, value):
        self.value=value
#%%
class MuxImg(MuxDocked):
    """ An Image"""
    def __init__(self,name,fluxi,trim=15,value=None,**kwargs): 
        super().__init__(name,fluxi)
        self.view=pg.PlotItem()
        self.plot = pg.ImageView(view=self.view)    
        self.createDock(self.plot,**kwargs)        
        self.mainwidget=self.plot
        self.type="Image"
        self.pos=None
        self.scale=None
        self.data=np.array([[]])
        self._lastdraw=0
        self.maxredraw_rate=10.
        self.autoLevels,self.autoHistogramRange,self.autoRange=False,False,False
        self.autoAll=True
        
        self.options.update({
            "Save/Save Value":{"type":"bool","value":False},        
        }) 
                
    
    def setTitles(self):
        #TODO
#        plt = pg.PlotItem(labels={'bottom': ('x axis title', 'm'), 'left': ('y axis title', 'm')})
#        view = pg.ImageView(view=plt)
#        plt.setAspectLocked(False)
        pass
    
    def setImage(self,data, pos=None,scale=None,autoRange=None):
        if autoRange is not None:
            self.autoRange=autoRange     
        if pos is not None:
            self.pos=pos
        if scale is not None:
            self.scale=scale
        
        if not isinstance(data, np.ndarray):
            raise TypeError("Must be a numpy array")
        self.data=data        
        self._requestRedraw()



    @property
    def v(self):
        return self.data
    @v.setter
    def v(self, value):
        self.setImage(value)
    
    def draw(self):
        #limit the redraws per seocond. Otherwise pyqtgraph will hang
        t=time.time()
        if t-self._lastdraw<1./self.maxredraw_rate:
            self._requestRedraw()
            return
        self._lastdraw=t
        scale=self.scale
        if not self.scale:
            scale=[1,1]
        if isinstance(self.data, np.ndarray):
            data=self.data
        else:
            return
        if self.autoAll:
            self.plot.setImage(data,autoRange=True,pos=self.pos, scale=scale,autoLevels=True,autoHistogramRange=True)             
            self.autoAll=False
        else:
            self.plot.setImage(data,autoRange=False,pos=self.pos, scale=scale,autoLevels=self.autoLevels,autoHistogramRange=self.autoHistogramRange) 
        if self.autoRange:
            self.plot.getView().autoRange(padding=0)        
        
    def add_region_item(self,minitem,maxitem,horizontal=False):
        if hasattr(self,"ri"):
            self.plot.removeItem(self.ri)
        if horizontal:
            orientation=pg.LinearRegionItem.Horizontal
        else:
            orientation=None
        self.ri=pg.LinearRegionItem(orientation=orientation)    
        self.plot.addItem(self.ri)
        self.ri.setRegion([minitem.v,maxitem.v])
        def regionChanged(*args):
            minitem.v,maxitem.v=self.ri.getRegion()
            minitem.emitChanged()
            maxitem.emitChanged()
        self.ri.sigRegionChanged.connect(regionChanged)
        
    def add_crosshair(self, name=None, pos=None):
        if name is None:
            name="Crosshair"
        try:
            self.ch.remove()
        except:
            pass
        self.ch=self.getfluxi().g("crosshair:%s@%s"%(name,self.name))
        self.ch.attach(self)
        if self.pos is not None:
            self.ch.v=pos
        
        
#%%
#from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget
##%%
#class MuxMPL(MuxDocked):
#    """ A Matplotlib plot"""
#    type="Matplotlib"
#    def __init__(self,name,fluxi,trim=15,value=None,**kwargs): 
#        super().__init__(name,fluxi)
#        self.widget = MatplotlibWidget()
#        self.createDock(self.widget,**kwargs)
#        
#    def getFig(self):
#        return self.widget.getFigure()
##        subplot = mw..add_subplot(111)
##        subplot.plot(x,y)
##        mw.draw()
    
#%%
class MuxTable(MuxDocked):
    """ An Image"""
    def __init__(self,name,fluxi,value=None,**kwargs):
        super().__init__(name,fluxi)
        self.t=self.mainwidget=MyTableWidget(editable=True,sortable=True)        
        self.createDock(self.t,**kwargs) 
        self.type="table"
        
        self.options.update({
            "Save/Save Value":{"type":"bool","value":False},
        })  
        
        #self.t.setFormat("%f.5")
            
            
    def get_selected_row(self):
        return self.get_row(self.t.currentRow())
    def get_row(self,num):
        return [str(self.t.item(num,i).text()) for i in range(self.t.columnCount())]
      
    def add(self, row):
        a=self.v
        a.append(row)
        self.v=a    
    @property
    def v(self):
        self._is_in_main_thread()
        return [self.get_row(rn) for rn in range(self.t.rowCount())]
    @v.setter
    def v(self, value):
        self._is_in_main_thread()
        self.t.setData(value)    
        
class MyTableWidget(pg.TableWidget):
    def contextMenuEvent(self, event):
        self.menu = QtGui.QMenu(self)
        ad = QtGui.QAction('Delete Selected Rows', self)
        ad.triggered.connect(self.removeSelectedRows)
        self.menu.addAction(ad)
        # add other required actions
        self.menu.popup(QtGui.QCursor.pos())  
    def removeSelectedRows(self):
        rows = self.selectionModel().selectedRows()
        #log("remove")
        #log(rows)
        for r in rows:
            self.removeRow(r.row())
#mt=MuxTable("woot!",value=[[1,2,3],[1,2],[1,2],[1,2]])
            


    
class MuxList(MuxDocked):
    """ A (collapsable) list """
    def __init__(self,name,fluxi,**kwargs):
        super().__init__(name,fluxi)   
        mw=self.mainwidget = QtGui.QTreeWidget()
        self.createDock(self.mainwidget)
        self.name=name
        self.type="List"
        
        self.root=self.mainwidget.invisibleRootItem()
        self.mainwidget.itemChanged.connect (self._handleChanged)
        self.mainwidget.itemSelectionChanged.connect (self._handleSelectionChanged)
        mw.header().setStretchLastSection(False)
        if "headers" in kwargs:
            self.setHeaders(kwargs["headers"],[None,20,40],["stretch","content","content"])
        #self.treeWidget.setHeaderHidden(False)
        mw.setSortingEnabled(True)
        mw.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        mw.setSelectionMode(4)#ContiguousSelection

        #TODO: set properties of columns

    def setHeaders(self,labels=None,sizes=[],resizing=[]):
        self._is_in_main_thread()
        mw=self.mainwidget
        if labels:
            mw.setColumnCount(len(labels))
            mw.setHeaderLabels(labels)
        
        for i, s in enumerate(sizes):
            if s!=None:
                mw.header().resizeSection(1, s)
        qhv=QtGui.QHeaderView
        resizers={"interactive":qhv.Interactive,"stretch":qhv.Stretch,"content":qhv.ResizeToContents,"fixed":qhv.Fixed}
        for i, s in enumerate(resizing):
            if not s:
                s="interactive"
            mw.header().setResizeMode(i, resizers[str(s)])
        return self
    
    def addParent(self, data=None,parent=None,checked=None,widgets={}):
        if not parent:
            parent=self.root        
        item=self.add(data=data,parent=parent,checked=checked,widgets=widgets)        
        item.setFlags(item.flags() | Qt.ItemIsDropEnabled)
        self._lastparent=item
        return item
    
    def addChild(self, data=None,parent=None,checked=None,widgets={}):
        if not parent:
            parent=self._lastparent
        item=self.add(data=data,parent=parent,checked=checked,widgets=widgets)
        item.setFlags(item.flags() ^ Qt.ItemIsDropEnabled)
        return item
        
    def add(self, data=None,parent=None,checked=None,widgets={}):   
        self._is_in_main_thread()         
        item = QtGui.QTreeWidgetItem(parent)
        item.setExpanded(True)
#        print(data)
        for i, d in enumerate(data):
            item.setData(i, Qt.DisplayRole, d)#EditRole
        item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.DontShowIndicatorWhenChildless)
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled)
#        print("checked",checked)
        if checked!=None:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if checked:
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)     
        else:
            #print ("none")
            item.setFlags(item.flags() ^ Qt.ItemIsUserCheckable)
        for pos in widgets:
            self.mainwidget.setItemWidget(item, pos, widgets[pos])
        return item


    @property
    def v(self):
        return self.getDict()#_listChildren()[u"children"]
    @v.setter
    def v(self, value):
        #TODO
        return self

    def _listChildren(self,parent=None):
        if not parent:
            parent=self.root
        children=[]
        for i in range(parent.childCount()):
            c=parent.child(i)
            children.append(self._listChildren(c))
        #.data(columne,role)
        data=[parent.data(i,0) for i in range(parent.columnCount())]
        d={'data':data}
        if parent.flags() & Qt.ItemIsDropEnabled:
            d["isParent"]=True
        if parent.flags() & Qt.ItemIsUserCheckable:
            d["checked"]=(parent.checkState(0)==Qt.Checked)         
        if len(children)>0:
            d["children"]=children
            if parent.isExpanded():
                d["expanded"]=parent.isExpanded()
        return d

    def getSublist(self,name,parent=None):
        child=self.getByName(name,parent)
        return self._listChildren(child)
        
    def getByName(self,name,parent=None):
        #TODO:name.split("/")
        if not parent:
            parent=self.mainwidget.invisibleRootItem()
        child=None
        for i in range(parent.childCount()):
            child=parent.child(i)
            #print(child.data(0,0),name,str(child.data(0,0))==str(name))
            if str(child.data(0,0))==str(name):
                return child
        raise NameError("Element not found")
        
    def getDict(self):
        return self._listChildren()
    def setDict(self,dictionary,item=None):
        d=dictionary
        if not item:
            nitem=self.root
        else:            
            checked=None
            if "checked" in d:
                checked=d["checked"]        
            if "isParent" in d and d["isParent"]:
                nitem=self.addParent(d["data"],item,checked)
            else:
                nitem=self.addChild(d["data"],item,checked)
            if "expanded" in d:
                nitem.setExpanded(d["expanded"])
            else:
                nitem.setExpanded(False)
        if "children" in d:
            for n in d["children"]:
                self.setDict(n,nitem)    
        return self
        
    def clear(self,parent=None):
        if not parent:
            parent=self.root        
        while parent.childCount()>0:
            parent.removeChild(parent.child(0))        
        return self
        
    def removeItem(self,item):
        parent=item.parent()
        if parent is None:
            parent=self.root
        parent.removeChild(item)        
        return self
#    def getSublist(self,name):
#        parent=self.mainwidget.invisibleRootItem()
#        child=None
#        for i in range(parent.childCount()):
#            child=parent.child(i)
#            print(child.data(0,0),name,str(child.data(0,0))==str(name))
#            if str(child.data(0,0))==str(name):
#                return [child.data(i,0) for i in range(child.columnCount())]
#        return None

    def _handleChanged(self, item, column):
        self.emitChanged()
        
    def _handleSelectionChanged(self):        
        self._selectedItems=self.mainwidget.selectedItems()
        self.emitChanged()
#        if item.checkState(column) == Qt.Checked:
#            print "checked", item, item.text(column)
#        if item.checkState(column) == Qt.Unchecked:
#            print "unchecked", item, item.text(column)
    def get_selected_items(self):
        return self._selectedItems
        
    def get_selected_item_data(self):
        #todo: add to fluxi
        item=self.get_selected_items()[0]
        data=[item.data(i,0) for i in range(item.columnCount())]     
        return data    
        
    def remove_selected_items(self):
        items=self.mainwidget.selectedItems()
        #print(items)
        for i in items:
            self.removeItem(i)
