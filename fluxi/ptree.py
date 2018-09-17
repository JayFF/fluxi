# -*- coding: utf-8 -*-
"""
"""
from __future__ import absolute_import, division, print_function, unicode_literals
try:
    from PyQt4 import QtCore,QtGui
    from PyQt4.QtCore import Qt
except ImportError:
    from PyQt5 import QtCore,QtGui
    from PyQt5.QtCore import Qt

#from PyQt4.QtCore import pyqtSlot as Slot
#import numpy as np
#import pyqtgraph as pg
#import time,sys
from fluxi.muxe import MuxDocked#,only_from_main_thread
from pyqtgraph.python2_3 import asUnicode  

class MyTree(QtGui.QTreeWidget):
    def __init__(self):
        QtGui.QTreeWidget.__init__(self)
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.setRootIsDecorated(False)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.setHorizontalScrollMode(self.ScrollPerPixel) 
        self.setAlternatingRowColors(True)
        self.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)        
    def contextMenuEvent(self, ev):
        item = self.currentItem()
        if hasattr(item.getparam(), 'contextMenuEvent'):
            item.getparam().contextMenuEvent(ev)
            
   
class MuxTree(MuxDocked):
    """ A (collapsable) list """
    def __init__(self,id,fluxi):
        super().__init__(id,fluxi)   
        self.mainwidget=mw= MyTree()
        self.createDock(self.mainwidget)
        self.root=mw.invisibleRootItem()
        mw.itemChanged.connect(self._handleChanged)
        mw.itemCollapsed.connect(self._handleExpanded)
        mw.itemExpanded.connect(self._handleExpanded)
        mw.setSortingEnabled(False)
        #mw.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
    def _handleExpanded(self, item):                
        item.getparam().expanded=item.isExpanded()
        
    def _handleChanged(self, item, column):
        pass
#        if item.checkState(column) == QtCore.Qt.Checked:
#            print "checked", item, item.text(column)
#        if item.checkState(column) == QtCore.Qt.Unchecked:
#            print "unchecked", item, item.text(column)
    
#tree.invisibleRootItem()
import weakref
class Param(QtCore.QObject):
    sigValueChanged=QtCore.pyqtSignal(object,object)
    sigContextMenu=QtCore.pyqtSignal(object)    
    def __init__(self,parent,title,digits=3):
        super().__init__()
        self.blockScroll=True        
        self.sig=None
        self.widget=None
        self.digits=digits
        self.title=title
        #parent.addChild(self)
        self.createTitle(title)
        self.createWidget()
        if self.sig:
            self.sig.connect(self._action)
        if self.widget:
            self.widget.installEventFilter(self)

        self.attachToTree(parent)
        
    def attachToTree(self,parent):
        #print(parent)
        self.treeitem=QtGui.QTreeWidgetItem(parent)
        self.treeitem.getparam=weakref.ref(self)
        #self.treeitem.treeWidget().setItemWidget(self.treeitem, 0, self.label)
        self.treeitem.setText(0, self.title)
        self.treeitem.setFlags(self.treeitem.flags() ^ Qt.ItemIsDropEnabled)
        self.treeitem.treeWidget().setItemWidget(self.treeitem, 1, self.widget)
        
        
    def getTitle(self):
        return self.title
        
    def setValue(self,value):
        if self.sig:
            self.sig.disconnect(self._action)
#        print ("setting Value")
#        self.widget.blockSignals(True)
        try:
            self._setValue(value)
        finally:
#            self.widget.blockSignals(False)
            if self.sig:
                self.sig.connect(self._action)
        
    def _setValue(self,value):
        self.widget.setValue(value)
    def getValue(self):
        return self._getValue()
        
    def _getValue(self):
        return self.widget.value()  
    
    @QtCore.pyqtSlot()
    def _action(self):
        #print (self.title,"changed to",self.getValue())
        self.sigValueChanged.emit(self, self.getValue())
    def createTitle(self,title):
#        self.labelwid=QtGui.QLabel(title)
#        self.labelwid.setSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Minimum);
#
#        self.layout = QtGui.QHBoxLayout()        
#        self.layout.addStretch()
#        self.layout.addSpacing(0)
#        self.layout.addWidget(self.labelwid)
#        
#        self.label = QtGui.QWidget()
#        self.label.setLayout(self.layout)        
        pass
        
         
    def createWidget(self):
        pass
    def contextMenuEvent(self,ev):      
        self.sigContextMenu.emit(ev)
        
    def remove(self):
        del self.treeitem.getparam
        #self.treeitem.takeChild(i)
        try:
            par=self.treeitem.parent()
            if not par:
                par=self.treeitem.treeWidget().invisibleRootItem()
            par.removeChild(self.treeitem)
        except:
            pass
        del self.treeitem
        
    def eventFilter(self,  obj,  event):
        if self.blockScroll and event.type()==QtCore.QEvent.Wheel:# and isinstance
            #print("event blocked")
            return True           
        return False 

from  fluxi.widgets.SpinBox import SpinBox
class ParamFloat(Param):

    def createWidget(self):        
        self.widget=SpinBox(decimals=6)    
        #self.widget.setFocusPolicy(QtCore.Qt.StrongFocus)
        #registerEvent(self.widget)
        self.sig=self.widget.sigValueChanged
        
        self.widget.setStyleSheet("""
        SpinBox {
            border: 0px none black;
            border-radius: 0px;
            background-color: transparent;
            }
            
        
        SpinBox:focus {
            background-color: #fff;
        }
        """)        

        
        
#class ParamTuple(Param):  
#
#        
#    def attachToTree(self,parent):
#        self.treeitem=QtGui.QTreeWidgetItem(parent)
#        self.treeitem.getparam=self#weakref.ref(self)
#        #self.treeitem.treeWidget().setItemWidget(self.treeitem, 0, self.label)
#        self.treeitem.setText(0, self.title)
#        self.treeitem.treeWidget().setItemWidget(self.treeitem, 1, self.widget)
#        if self.sig:
#            self.sig.connect(self._action)
#        self.attachToTree(parent)
#        
#        for t in self.title:
#            
#    def createWidget(self):        
#        self.widget=SpinBox()        
#        self.sig=self.widget.sigValueChanged        
#    def setValue(self,value):
#        self.widget.blockSignals(True)
#        try:
#            self._setValue(value)
#        finally:
#            self.widget.blockSignals(False)        
#    def _getValue(self):
#        return self.widget.value()  
    

class ParamAction(Param):
#    def createTitle(self,title):
#        pass     
    def createWidget(self):
        self.layoutWidget = QtGui.QWidget()
        self.layout = QtGui.QHBoxLayout()
        
        self.layoutWidget.setLayout(self.layout)
        self.widget = QtGui.QPushButton(self.title)
        #self.layout.addSpacing(100)
        self.layout.setContentsMargins(0,0,0,0)#(left,top,right,bottom) 
        self.layout.addWidget(self.widget)
        self.layout.addStretch()
        self.sig=self.widget.clicked
        
    def attachToTree(self,parent):
        self.treeitem=QtGui.QTreeWidgetItem(parent)
        self.treeitem.getparam=weakref.ref(self)
        self.treeitem.setText(0, '')
        self.treeitem.treeWidget().setFirstItemColumnSpanned(self.treeitem, True)
        self.treeitem.treeWidget().setItemWidget(self.treeitem, 0, self.layoutWidget)
        
    def setValue(self,value):
        pass
    def getValue(self):
        pass
    


class ParamInt(Param):     
    def createWidget(self):        
        self.widget=SpinBox(dec=False,minStep=1.0,step=1.0,decimals=6)
        self.sig=self.widget.sigValueChanged

        self.widget.setStyleSheet("""
        SpinBox {
            border: 0px none black;
            border-radius: 0px;
            background-color: transparent;
            }
            
        
        SpinBox:focus {
            background-color: #fff;
        }
        """)
        
    def _setValue(self,value):
        self.widget.setValue(int(value))
    def _getValue(self):
        return int(self.widget.value())
        
class ParamDisplay(Param):     
    def attachToTree(self,parent):
        self.treeitem=QtGui.QTreeWidgetItem(parent)
        self.treeitem.getparam=weakref.ref(self)
        self.treeitem.setText(0, self.title)
    def setValue(self,value):
        #TODO:
#        if isinstance(value,float):
#            self.treeitem.setText(1, ("%."+self.digits+"f") %value)
#        else:
#            self.treeitem.setText(1, str(value))
        self.treeitem.setText(1, str(value))
    def getValue(self):
        return self.treeitem.text(1)                  
        
class ParamBool(Param):     
    def createWidget(self):
        self.widget=QtGui.QCheckBox()        
        self.sig=self.widget.toggled
    def _setValue(self,value):
        self.widget.setChecked(value)
    def _getValue(self):
        return self.widget.isChecked()      

class ParamStr(Param):     
    def createWidget(self):
        self.widget=QtGui.QLineEdit()        
        self.sig=self.widget.editingFinished
    def _setValue(self,value):
        self.widget.setText(asUnicode(value))
    def _getValue(self):
        return asUnicode(self.widget.text())



from pyqtgraph.widgets.ComboBox import ComboBox

class ParamList(Param):     
    def createWidget(self):
        self.widget=ComboBox()       
        self.widget.setMaximumHeight(20)  ## set to match height of spin box and line edit
        self.sig=self.widget.currentIndexChanged
        self.targetValue=None

    
    def _getValue(self):
        return self.widget.value()
    
    def _setValue(self, val):
        try:
            self.widget.setValue(val)
        except ValueError:
            self.widget.addItems([val])
            self.widget.setValue(val)
            

    def setOptions(self,options):
        if self.sig:
            self.sig.disconnect(self._action)
        try:
            self.widget.setItems(options)
        finally:
            if self.sig:
                self.sig.connect(self._action)          
            
class ParamDir(Param):
        pass
#    def getDir(self):
##        dialog = QtGui.QFileDialog()
##        dialog.setFileMode(QtGui.QFileDialog.Directory)
##        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
##        directory = dialog.getExistingDirectory(self, 'Choose Directory', os.path.curdir)
        
class ParamGroup(Param):     
    def createTitle(self,title):
        self.label=QtGui.QLabel(self.title)
 
    
    def attachToTree(self,parent):
        self.treeitem=QtGui.QTreeWidgetItem(parent)
        self.treeitem.getparam=weakref.ref(self)
        self.treeitem.treeWidget().setFirstItemColumnSpanned(self.treeitem, True)
        self.treeitem.setFlags(self.treeitem.flags() | Qt.ItemIsDropEnabled)
        #self.treeitem.treeWidget().setItemWidget(self.treeitem, 0, self.label) 
        self.treeitem.setText(0,self.title)
        self.treeitem.setExpanded(True)
        self.expanded=True
   
        for c in [0,1]:
            self.treeitem.setBackground(c, QtGui.QBrush(QtGui.QColor(220,220,220)))
            #self.treeitem.setForeground(c, QtGui.QBrush(QtGui.QColor(220,220,255)))
            font = self.treeitem.font(c)
            font.setBold(True)
            font.setPointSize(font.pointSize()+1)
            self.treeitem.setFont(c, font)
            self.treeitem.setSizeHint(0, QtCore.QSize(0, 25))   
            
    def createWidget(self):
        self.widget=self.label
   
    def _setValue(self,value):
        self.widget.setText(asUnicode(value))
    def _getValue(self):
        return asUnicode(self.widget.text())
    def __del__(self):
        print("del")
        
               
def getChildGroup(parent, title):
    for i in range(0,parent.childCount()):
        c=parent.child(i)
        #print(type(c.getparam)==ParamGroup, c.getparam.getTitle()==title,type(c.getparam),c.getparam.getTitle())
        if type(c.getparam())==ParamGroup and c.getparam().getTitle()==title:
            return c
    return None
        
        
mappedNames={
    "float":ParamFloat,
    "action":ParamAction,
    "bool":ParamBool,
    "int":ParamInt,
    "str":ParamStr,
    "list":ParamList,
    "group":ParamGroup,
    "display":ParamDisplay,
    
    "f":ParamFloat,
    "a":ParamAction,
    "b":ParamBool,
    "i":ParamInt,
    "s":ParamStr,
    "l":ParamList,
    "g":ParamGroup,
    "d":ParamDisplay    
}

class Evfilter(QtCore.QObject):
    def __init__(self,func):
        QtCore.QObject.__init__(self)
        self.func=func
    def eventFilter(self,  obj,  event):
        if event.type()==QtCore.QEvent.Wheel:# and isinstance
            #event blocked
            return True           
        return False
        
def registerEvent(qobject,function=None):
    qobject.evfilter = Evfilter(function)
    qobject.installEventFilter(qobject.evfilter)        
def removeEvent(qobject):
    qobject.removeEventFilter(qobject.evfilter)



#elif t == 'color':
#    w = ColorButton()
#    w.sigChanged = w.sigColorChanged
#    w.sigChanging = w.sigColorChanging
#    w.value = w.color
#    w.setValue = w.setColor
#    self.hideWidget = False
#    w.setFlat(True)
#    w.setEnabled(not opts.get('readonly', False))            
#elif t == 'colormap':
#    from ..widgets.GradientWidget import GradientWidget ## need this here to avoid import loop
#    w = GradientWidget(orientation='bottom')
#    w.sigChanged = w.sigGradientChangeFinished
#    w.sigChanging = w.sigGradientChanged
#    w.value = w.colorMap
#    w.setValue = w.setColorMap
#    self.hideWidget = False