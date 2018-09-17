# -*- coding: utf-8 -*-
from __future__ import division,absolute_import,print_function
import numpy as np
from fluxi.helper import save_json,save_tsv
from fluxi.fluxi import Fluxi
import scan_globals
from m_base import MeasureBase
from m_winspec import MeasureWinSpec
from pymeasure.instruments.yokogawa import Yokogawa7651
from devices.nidaq import Reader
import time
#%%
ms,s=None,None
#%%
class MeasureVoltSweep(MeasureBase):
    name="MeasureVoltSweep"
    def __init__(self,mainmux):
        #super().__init__(mainmux)
        self.mainmux=mainmux
        ms=self.ms=self.gui=Fluxi(self.name,mainmux)
        self.newpoint()
        #self.gui.B("Voltsweeping/on").a=self.set_need_reset
        self.voltage_setter=None
        self.gui.Im("Run").view.setAspectLocked(False)
        self.gui.Im("Last").view.setAspectLocked(False)
        self.winspec=MeasureWinSpec(ms)
        self.winspec.connect()
        self.gui.P("Steps/Stepsize").v=0.1
        self.gui.B("Steps/Normal_Order").v=True
        self.gui.P("Steps/Start Voltage").v=0.
        self.gui.P("Steps/Number of Ramps").v=1
        self.gui.P("Steps/Preramp Timesteps").v=1
        self.gui.B("Steps/Preramp").v=True
        self.rd=Reader(int(10000./1),chan="Dev1/ai0",lowV=-10,highV=10,samplespersecond=10000)
        self.rd.addChannel(chan="Dev1/ai2",lowV=-10,highV=10)
        
    def prepare(self):        
        self.yolo=Yokogawa7651("GPIB1::10")
        self.yolo.apply_voltage(32)
        self.yolo.ramp_to_voltage(0)
        #self.volt=0.0
        self.yolo.enable_source()
        self.next=0
        

    def disconnect(self):
        self.yolo.ramp_to_voltage(0.0)        
        self.voltage_setter=None
        del self.rd
#  
#    def prepare(self):
#        if self.gui.B("Yoko/on").v and not self.voltage_setter:
#            self.connect_voltagesetter()
#        elif not self.gui.B("Yoko/on").v and self.voltage_setter:
#            self.disconnect_voltagesetter()
#      
    def fastramp(self, program, pause):
        for voltage in program:
            self.yolo.ramp_to_voltage(voltage)
            time.sleep(pause)
            
            
    def chainsaw(self):
        if self.gui.B("Steps/Normal_Order"):
            self.ramp=np.arange(self.startvolt, self.maxim,self.step)
            self.ramp=np.append(self.ramp,np.arange(self.maxim,self.minim,-self.step))            
            self.ramp=np.append(self.ramp,np.arange(self.minim,self.startvolt,self.step)) 
        else:
            self.ramp=np.arange(self.startvolt, self.minim,-self.step)
            self.ramp=np.append(self.ramp,np.arange(self.minim,self.maxim,self.step))            
            self.ramp=np.append(self.ramp,np.arange(self.maxim,self.startvolt,-self.step))
        self.preramp=np.append(self.ramp, self.startvolt)
        self.ramp=np.tile(self.ramp, int(self.number_of_ramps))
        self.ramp=np.append(self.ramp, self.startvolt)
            
    def repeat(self):    
        
        self.maxim=self.gui.P("Steps/Maximum Voltage").v
        self.minim=self.gui.P("Steps/Minimum Voltage").v
        self.startvolt=self.gui.P("Steps/Start Voltage").v
        self.step=self.gui.P("Steps/Stepsize").v 
        self.number_of_ramps=self.gui.P("Steps/Number of Ramps").v
        self.preramp_pause=self.gui.P("Steps/Preramp Timesteps").v
        do_repeat=False
#        
        if self.gui.A("Restart").v:
            self.chainsaw()
            if self.gui.B("Steps/Preramp").v==True:
                self.fastramp(self.preramp, self.preramp_pause)
            self.gui.D("Steps/#").v=len(self.ramp)
#            self.gui.P("Steps/Current Voltage").v=self.next=self.minim
            self.ac=None
            self.gui.B("Steps/Scanning").v=False
            self.yolo.ramp_to_voltage(self.startvolt)
            self.next=0
            self.gui.B("Steps/Scanning").v=True
        if self.gui.B("Steps/Scanning").v:
            if self.next<len(self.ramp):
                self.yolo.ramp_to_voltage(self.ramp[int(self.next)])
                self.gui.D("Steps/Current Voltage").v=self.ramp[int(self.next)]
                self.next+=1
                do_repeat=True

            else:
                do_repeat=False
                self.gui.B("Steps/Scanning").v=False
                #self.gui.D("Steps/Current Voltage").v=self.maxim
                self.gui.Im("Last").setImage(np.array(self.ac).T)
                self.recordpoint()
                
        return do_repeat
        
             
    def q_finished(self):
        """ acquires spectrum and adds to array"""
        if not self.winspec.w().running:
            if self.winspec.q_finished():
                ys=self.winspec.spec
                vl=self.rd.getMean()
                if self.ac is None:
                    self.ic=[vl[0]]
                    self.ir=[vl[1]]
                    self.ac=[ys]
                    self.wlen=self.winspec.xs
                else:
                    self.ac=np.append(self.ac,[ys],0)#hi Jonathan, I changed this line
                    self.ic=np.append(self.ic,[vl[0]],0)
                    self.ir=np.append(self.ir,[vl[1]],0)
                #self.ac_infos=np.append(self.ac_infos,[self.gui.D("Steps/Current Voltage").v],0)
                self.value=self.winspec.value
                self.gui.Im("Run").setImage(np.array(self.ac).T)
                self.gui.C("IC").add(vl[0])
                self.gui.C("IR").add(vl[1])
                return True
                
            else:
                return False
        else:
            return False
            
#        ac=np.append(ac,[ys],0)[-100:]
#        gui.Im("Run").setImage(np.array(ac).T)
#        nimm von self.spec einen wert und füge ihn zu self.ac hinzu
 #      self.ac.append(self.spec.getmeasurementhorstomat)       
        
        
    def curvalue(self):
        """ return a value while measuring """
        return self.value   
        
    def recordpoint(self):
        #super(MeasureSpecStep, self).recordpoint()
        name=self.gui.S("Current Point File").v+scan_globals.gui.S("Scanpoints/Pointname").v
        save_tsv(self.ac,name,add_to_name="Voltage_Sweep")
        save_tsv(self.ramp,name,add_to_name="voltages")
        save_tsv(self.wlen,name,add_to_name="wlen_to_px")
        save_tsv(self.ic,name,add_to_name="IC")
        save_tsv(self.ir,name,add_to_name="IR")
        save_json(self.gui.get_values_all(),name,add_to_name="cfg")
#        """saves the collected data of the PD_readout into own arrays"""
#        scan_data.save_current_data_to_csv(additional_name=".PD_mean",arrayname="PD_mean")
#        scan_data.save_current_data_to_csv(additional_name=".PD_max",arrayname="PD_max")
#        
        
    def newpoint(self):
        self.ac=None
        self.ac_infos=[]