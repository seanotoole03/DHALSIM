from typing import List


class PlcConfig:
    def __init__(self, name: str, sensors: List[str], actuators: List[str], mac: str = None, ip: str = None):
        """
        Initializes a PlcConfig.

        :param name: the name of the PLC
        :param mac: the MAC address of the PLC
        :param sensors: the sensors the PLC can read
        :param actuators: the actuators the PLC can control
        """

        self.name = name

        if type(mac) != str:
            raise TypeError
        self.mac = mac

        if type(sensors) != list:
            raise TypeError
        self.sensors = sensors

        if type(actuators) != list:
            raise TypeError
        self.actuators = actuators
