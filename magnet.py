import slave
from slave.transport import SimulatedTransport
from slave.cryomagnetics.mps4g import MPS4G
from slave.transport import Visa
from time import sleep
from threading import Thread
from threading import Lock
transport_default = SimulatedTransport()

class cryomagnet(MPS4G):
    """Wrapper for mps4g module from slave"""
    def __init__(self, transport): #, transport=Visa('GPIB::05')):
        # self.magnet = MPS4G(transport=transport_default)
        MPS4G.__init__(self,transport)
        self.field = 0
        self.is_ready = True
        self.lock = Lock() 
        self._current_field = self.current


    def ramp_to_field(
            self,
            field,
            speed='SLOW', 
            unit='G',
            block=False):
        t = Thread(self._ramp(field, speed, unit, block))
        t.run()


    def ramp_to_zero(self, speed='SLOW', block=False):
        t = Thread(self._ramp_to_zero(speed, block))
        t.run()


    def _ramp_to_zero(self, speed, block):
        self.sweep('ZERO')


    def _ramp(self, field, speed, unit, block):
        self.unit = unit
        with self.lock:
            self.is_ready = False
        if field > self._current_field:
            self.upper_limit = field
            self.lower_limit = 0
            self.switch_heater = True
            self.sweep('UP')
            while self._current_field < field:
                with self.lock:
                    self._current_field = self.current
                    print(self.current + 2)
                sleep(0.1)
        else:
            self.lower_limit = field
            self.upper_limit = 0
            self.switch_heater = True
            self.sweep('DOWN')
            while self._current_field > field:
                with self.lock:
                    self._current_field = self.current
                    print(self.current + 3)
                sleep(0.1)
        self.sweep('PAUSE')
        self.switch_heater = False
        with self.lock:
            self.is_ready = True


if __name__ == '__main__':
    magnet = cryomagnet(transport=Visa('GPIB::05'))
    magnet.ramp_to_field(0.2)
    while magnet.is_ready == False:
        pass
    print(magnet.current)
    # magnet.sweep_to_field(10000)
    print("Done")
