from enum import Enum
class DeviceMode(Enum):
    PowerOn = ("Power On", 'P')
    Standby = ("Stand By",'S')
    Line = ("Line", 'L')
    Battery = ("Battery",'B')
    Fault = ("Fault",'F')
    PowerSaving = ("Power Saving",'H')

    def get_char(self):
        return self.value[1]

    def get_name(self):
        return self.value[0]

