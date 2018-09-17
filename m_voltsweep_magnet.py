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
from magnet import cryomagnet
import time
#%%
ms,s=None,None
#%%
class MeasureVoltSweepMagnet(MeasureBase):
    name="MeasureVoltSweepMagnet"
    def __init__(self,mainmux):
        #super().__init__(mainmux)
        self.mainmux=mainmux
        ms=self.ms=self.gui=Fluxi(self.name,mainmux)
        self.newpoint()
        #self.gui.B("Voltsweeping/on").a=self.set_need_reset
        self.voltage_setter=None
        self.gui.Im("Run").view.setAspectLocked(False)
        self.gui.Im("Last").view.setAspectLocked(False)
        self.run_voltagesweep = self.gui.B("General/Run voltage sweep")
        self.run_voltagesweep.v = False
        self.run_magneticfieldsweep = self.gui.B("General/Run magnetic field sweep")
        self.run_magneticfieldsweep.v = False
        self.scanning = self.gui.B("General/Scanning")
        self.scanning.v = False
        self.run_polarizaton = self.gui.B("General/Run polarization")
        self.run_polarizaton = False
        self.gui.P("Voltage sweep/Stepsize").v=0.1
        self.gui.B("Voltage sweep/Normal order").v=True
        self.gui.P("Voltage sweep/Start voltage").v=0.
        self.gui.P("Voltage sweep/Number of ramps").v=1
        self.gui.P("Voltage sweep/Preramp timesteps").v=1
        self.gui.B("Voltage sweep/Preramp").v=True
        self.gui.P("Magnetic Field Sweep/Field minimum (Tesla)").v=0
        self.gui.P("Magnetic Field Sweep/Field maximum (Tesla)").v=0
        self.gui.P("Magnetic Field Sweep/Field stepsize (Tesla)").v=1
        self.gui.B("Magnetic Field Sweep/Sweep low to high"),v=False
        self.gui.B("Magnetic Field Sweep/Settings locked").v=False
        

    def prepare(self):        
        """Establishes connections to instruments"""
        try:
            self.rd=Reader(int(10000./1),chan="Dev1/ai0",lowV=-10,highV=10,samplespersecond=10000)
            self.rd.addChannel(chan="Dev1/ai2",lowV=-10,highV=10)
        except:
            print("Cannot connect to daq-card")
        try:
            self.winspec=MeasureWinSpec(ms)
            self.winspec.connect()
        except:
            print("Cannot connect to winspec")
        try:
            self.yolo = Yokogawa7651("GPIB1::10")
            self.yolo.apply_voltage(32)
            self.yolo.ramp_to_voltage(0)
            self.yolo.enable_source()
            self.next=0
        except:
            print("Yokogawa not connected")
        try:
            self.magnet = cryomagnet(transport=Visa('GPIB1::05'))
            self.next_field = 0
        except:
            print("Magnet Power Source not connected.")


    def disconnect(self):
        self.yolo.ramp_to_voltage(0.0)        
        self.voltage_setter=None
        del self.rd


    def fastramp(self, program, pause):
        for voltage in program:
            self.yolo.ramp_to_voltage(voltage)
            time.sleep(pause)
            
            
    def chainsaw(self):
        """create saw-like voltage ramp to account for hysteresis"""
        if self.gui.B("Voltage sweep/Normal_Order"):
            voltage_ramp=np.arange(self.startvolt, self.maxim,self.step)
            voltage_ramp=np.append(voltage_ramp,np.arange(self.maxim,self.minim,-self.step))            
            voltage_ramp=np.append(voltage_ramp,np.arange(self.minim,self.startvolt,self.step)) 
        else:
            voltage_ramp=np.arange(self.startvolt, self.minim,-self.step)
            voltage_ramp=np.append(voltage_ramp,np.arange(self.minim,self.maxim,self.step))            
            voltage_ramp=np.append(voltage_ramp,np.arange(self.maxim,self.startvolt,-self.step))
        voltage_ramp=np.tile(voltage_ramp, int(self.number_of_ramps))
        voltage_ramp=np.append(self.ramp, self.startvolt)
        return voltage_ramp, preramp


    def magnetic_ramp(self):
        """creates profile for magnetic field ramp always from low to high field strength"""
        sign = np.sign(self.maxfield-self.minfield)
        if self.minfield * self.maxfield > 0:
            ramp = np.arange(self.minfield, self.maxfield, sign * self.stepfield)
        else:
            ramp = np.arange(0.0, self.maxfield, self.stepfield * sign)
            ramp = np.append(ramp, np.arange(
                0.0 - sign * self.stepfield,
                self.minfield, 
                self.stepfield * sign * (-1)))
        # if self.gui.B("Magnetic field sweep/Magnetic Ramp Low to High"):
        #    ramp = np.flip(ramp, axis=0)
        return ramp
    

    def read_parameters_voltage(self):
        """Reads the gui-inputs"""
        self.maxim=self.gui.P("Voltage sweep/Maximum Voltage").v
        self.minim=self.gui.P("Voltage sweep/Minimum Voltage").v
        self.startvolt=self.gui.P("Voltage sweep/Start Voltage").v
        self.step=self.gui.P("Voltage sweep/Stepsize").v 
        self.number_of_ramps=self.gui.P("Voltage sweep/Number of Ramps").v
        self.preramp_pause=self.gui.P("Voltage sweep/Preramp Timesteps").v


    def read_parameters_magnetic(self):
        self.minfield = self.gui.P("Magnetic field sweep/Magnetic Field Minimum (Tesla)").v
        self.maxfield = self.gui.P("Magnetic field sweep/Magnetic Field Maximum (Tesla)").v
        self.stepfield = np.absolute(self.gui.P("Magnetic field sweep/Magnetic Field Stepsize (Tesla)").v)
            

    def repeat(self):    
        
        self.voltage_ready = True
        self.polarization_ready = True
        self.magnetic_field_done = True

        if self.gui.A("Start Measurement").v:

            if self.run_magneticfieldsweep:
                self.read_parameters_magnetic()
                self.next_field = 0
                self.field_ramp = self.magnetic_ramp()
                self.magnetic_field_done = False
            
            if self.run_voltagesweep:
                self.read_parameters_voltage
                self.voltage_ramp, self.preramp = chainsaw()
                self.voltage_ready = False
                if self.gui.B("Voltage sweep/Preramp").v==True:
                    self.fastramp(self.preramp, self.preramp_pause)
                self.gui.D("Voltage sweep/#").v=len(self.voltage_ramp)
#               self.gui.P("Steps/Current Voltage").v=self.next=self.minim
                self.gui.B("Voltage sweep/Scanning").v=False
                self.yolo.ramp_to_voltage(self.startvolt)
                self.next=0

            self.ac=None
        # Hier noch die Polariastion
            self.scanning.v=True

        if self.scanning.v=True:

            if self.run_magneticfieldsweep and self.voltage_ready and self.polarization_ready:
                self.magnet.ramp_to_field(self.field_ramp[self.next_field])
                self.next_field += 1
                if self.next_field >= len(field_ramp):
                    self.magnetic_field_done=True

            if self.voltage_ready and self.run_polarization.v:
                pass
                # Designed for only two states sigma+/sigma-. More work for sweep or co/cross needed
                # if switch polarization 
                # if polarization not ready: set polarization ready
                # if else: set polarization not ready
                
            # Add polarisation-ready condition
            while self.magnet.is_ready == False:
                pass

            if self.run_voltagesweep:
                if self.voltage_ready:
                    if self.gui.B("Voltage sweep/Preramp").v==True:
                        self.fastramp(self.preramp, self.preramp_pause)
# Hier weitermachen Jonathan
            if self.gui.B("Voltage sweep/Preramp").v==True:
                self.fastramp(self.preramp, self.preramp_pause)
        if self.gui.B("Voltage sweep/Scanning").v:
            if self.next<len(self.ramp):
                self.yolo.ramp_to_voltage(self.voltage_ramp[int(self.next)])
                self.gui.D("Voltage sweep/Current Voltage").v=self.voltage_ramp[int(self.next)]
                self.next+=1
                do_repeat=True

            else:
                do_repeat=False
                self.gui.B("Voltage sweep/Scanning").v=False
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