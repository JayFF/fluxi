# -*- coding: utf-8 -*-
"""
Interface for NI DAQ cards.
"""

from .devices import Device, DeviceQty, decorator_access_control
import PyDAQmx
import numpy
import time


class NiDaqIOError(Exception):
    """
    NI DAQ communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)


class NiDaqRingBuffer():
    """
    A 1D ring buffer using numpy arrays.
    
    Args:
        length (int):
            Number of data slots in the ring buffer.
    """
    def __init__(self, length):
        self._data = numpy.zeros(length, dtype='float')
        self._empty = True
        self._full = False
        self._index = 0
    
    @property
    def empty(self):
        """
        Property that returns *True* if there is no data stored in the ring
        buffer and *False* otherwise.
        
        :type: bool
        """
        return self._empty
    
    @property
    def full(self):
        """
        Property that returns *True* if the ring buffer has been completely
        filled at least once and *False* otherwise
        
        :type: bool
        """
        return self._full
    
    @property
    def index(self):
        """
        Property that returns the index of the most current element in the
        buffer.
        
        :type: int
        """
        return self._index

    def extend(self, x):
        """
        Adds data to the ring buffer.
        
        Args:
            x (numpy.array): Data to be added to the buffer.
        """
        self._empty = False
        if self._index + x.size >= self._data.size:
            self._full = True
        x_index = (self._index + numpy.arange(x.size)) % self._data.size
        if x.size > self._data.size:
            self._data[x_index[-self._data.size:]] = x[-self._data.size:]
        else:
            self._data[x_index] = x
        self._index = x_index[-1] + 1

    def get(self):
        """
        Returns **all** data in the ring buffer in the order in which it was
        submitted.
        
        Returns: numpy.array
        """
        if self._full:
            idx = (self._index + numpy.arange(self._data.size)) % self._data.size
        else:
            idx = numpy.arange(self._index)
        return self._data[idx]
    
    def clear(self):
        """
        Empties the ring buffer.
        """
        self._empty = True
        self._full = False
        self._index = 0


def define_qty_class():
    class NiDaqQty(DeviceQty):
        def __init__(self, parent, *, prio = 0):
            super().__init__(parent, prio = prio)
    
            def make_getter(channel):
                def getter(self):
                    if self.parent._input_buffer[channel].empty:
                        self.parent._fetch()
                    return self.parent._get(channel)
                return property(decorator_access_control(getter))
            
            def make_setter(channel):
                def setter(self, voltage):
                    self.set(channel, voltage)
                return property(None, setter)
            
            if not self.parent._input is None:
                for channel in self.parent._input:
                    setattr(self.__class__, channel, make_getter(channel))
            
            if not self.parent._output is None:
                for channel in self.parent._output:
                    setattr(self.__class__, channel, make_setter(channel))
        
        @decorator_access_control
        def fetch(self):
            self.parent._fetch()
        
        @decorator_access_control
        def get(self, channel):
            return self.parent._get(channel)
        
        @decorator_access_control
        def set(self, channel, voltage):
            self.parent._set(channel, voltage)
    
    return NiDaqQty


class NiDaq(Device):
    def __init__(self, config):
        # Try to get device
        try:
            self._device = config['device']
        except KeyError as e:
            msg = "No device string specified"
            raise NiDaqIOError(msg).with_traceback(e.__traceback__)

        # Store channel information
        if 'input' in config:
            self._input = config['input']
            self._input_task = PyDAQmx.Task()
            self._input_buffer = dict()
        else:
            self._input = None
            self._input_task = None
            self._input_buffer = None
            
        if 'output' in config:
            self._output = config['output']
            self._output_tasks = dict()
            for channel in self._output:
                self._output_tasks[channel] = PyDAQmx.Task()
        else:
            self._output = None
            self._output_tasks = None

        # Is there any task?
        if self._input is None and self._output is None:
            raise NiDaqIOError('Neither input nor output specified.')
            
        # Set config default values
        self.conv_rate = 1000000
        self.max_buffer = 1000000
        self.num_samples = 1000
        self.sampling_rate = 10000
        
        # Get attributes from config
        attrs = {key:config[key] for key in ['conv_rate', \
            'max_buffer', 'num_samples', 'sampling_rate'] \
            if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)
        
        # Open connection to device
        self._NiDaqQty = define_qty_class()
        super().__init__(self._NiDaqQty, NiDaqIOError)

    @property
    def conv_rate(self):
        return self._conv_rate
    
    @conv_rate.setter
    def conv_rate(self, value):
        self._conv_rate = value

    @property
    def max_buffer(self):
        return self._max_buffer
    
    @max_buffer.setter
    def max_buffer(self, value):
        self._max_buffer = value

    @property
    def num_samples(self):
        return self._num_samples
    
    @num_samples.setter
    def num_samples(self, value):
        self._num_samples = value

    @property
    def sampling_rate(self):
        return self._sampling_rate
    
    @sampling_rate.setter
    def sampling_rate(self, value):
        self._sampling_rate = value

    def open(self):
        print('Opening connection to NI DAQ... ', end = '', flush = True)
        
        # Open all input channels
        if not self._input is None:
            count = 0
            for channel, channel_config in self._input.items():
                # Set default values for high and low voltage
                if not 'high' in channel_config:
                    channel_config['high'] = 10
                if not 'low' in channel_config:
                    channel_config['low'] = -10

                # Store number of current channel
                self._input[channel]['index'] = count
                count += 1
                
                # Initialize buffer
                self._input_buffer[channel] = NiDaqRingBuffer(self.max_buffer)
                
                # Open channel
                self._input_task.CreateAIVoltageChan(self._device + '/' + channel, "", \
                    PyDAQmx.DAQmx_Val_Cfg_Default, \
                    float(channel_config['low']), \
                    float(channel_config['high']), \
                    PyDAQmx.DAQmx_Val_Volts, None)
            
            # Configure channels
            self._input_task.CfgSampClkTiming("", float(self.sampling_rate), \
                PyDAQmx.DAQmx_Val_Rising, PyDAQmx.DAQmx_Val_ContSamps, \
                self.num_samples)
            self._input_task.SetReadOverWrite(PyDAQmx.DAQmx_Val_OverwriteUnreadSamps)
            self._input_task.SetReadRelativeTo(PyDAQmx.DAQmx_Val_MostRecentSamp)
            self._input_task.SetReadOffset(-self.num_samples)
            self._input_task.SetAIConvRate(self.conv_rate)

            # Setup variables
            size = self.num_samples * len(self._input)
            self._data = numpy.zeros((size, ), dtype = numpy.float64)            
        
            # Start task
            try:
                self._input_task.StartTask()
            except PyDAQmx.DAQError as e:
                msg = "Could not start input task"
                raise NiDaqIOError(msg).with_traceback(e.__traceback__)
                
        # Open all output channels
        if not self._output is None:
            for channel, channel_config in self._output.items():
                # Set default values for high and low voltage
                if not 'high' in channel_config:
                    channel_config['high'] = 10
                if not 'low' in channel_config:
                    channel_config['low'] = -10
                
                # Open channel
                self._output_tasks[channel].CreateAOVoltageChan(self._device + '/' + channel, "", \
                    float(channel_config['low']), \
                    float(channel_config['high']), \
                    PyDAQmx.DAQmx_Val_Volts, None)
                    
                # Start task
                try:
                    self._output_tasks[channel].StartTask()
                except PyDAQmx.DAQError as e:
                    msg = "Could not start output task for channel {0}".format(channel)
                    raise NiDaqIOError(msg).with_traceback(e.__traceback__)

        # The device is soooo slow.
        time.sleep(5)
        
        super().open()
        print('Success.', flush = True)

    def close(self):
        super().close()
        if not self._input_task is None:
            self._input_task.StopTask()
            self._input_task.ClearTask()
        if not self._output_tasks is None:
            for channel in self._output_tasks:
                self._output_tasks[channel].StopTask()
                self._output_tasks[channel].ClearTask()
        PyDAQmx.DAQmxResetDevice(self._device)
    
    def _fetch(self):
        read = PyDAQmx.int32()
        # Number of samples to read. -1 means reading all available samples
        num = -1
        try:
            self._input_task.ReadAnalogF64(num, 1, PyDAQmx.DAQmx_Val_GroupByChannel, \
                self._data, self.num_samples * len(self._input), \
                PyDAQmx.byref(read),None)
        except PyDAQmx.DAQError as error:
            if error.error==-200277:
                # There are not enough samples available yet.
                # Wait a millisecond and the time to collect to be sure to have
                # filled the buffer up to the offset
                time.sleep(1. / self.sampling_rate * self.num_samples * 1.5 + 0.0001)
                try:
                    self._input_task.ReadAnalogF64(num, 1, PyDAQmx.DAQmx_Val_GroupByChannel, \
                        self._data, self.num_samples * len(self._input), \
                        PyDAQmx.byref(read),None)
                except PyDAQmx.DAQError as e:
                    raise NiDaqIOError().with_traceback(e.__traceback__)
            else:
                raise NiDaqIOError().with_traceback(error.__traceback__)

        # Fill buffers:
        reshaped = self._data.reshape((len(self._input),-1))
        
        for channel in self._input:
            self._input_buffer[channel].extend(reshaped[self._input[channel]['index']])
    
    def _get(self, channel):
        res = self._input_buffer[channel].get()
        self._input_buffer[channel].clear()
        return res

    def _set(self, channel, voltage):
        self._output_tasks[channel].WriteAnalogScalarF64(True, 1, float(voltage), None)

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()