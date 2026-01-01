from enum import Enum

class Option(Enum):
    SILENCE_BUZZER = ("SilenceBuzzer", 'A', 83)
    OVERLOAD_BYPASS = ("OverloadBypass",'B', 77)
    #POWER_SAVING = ("PowerSaving", 'J', 84)
    #LCD_DISPLAY_TIMEOUT = ("LCDDisplayTimeout",'K', 78)
    OVERLOAD_RESTART = ("OverloadRestart",'U', 79)
    OVER_TEMPERATURE_RESTART = ("OverTemperatureRestart", 'V', 80)
    BACKLIGHT = ("Backlight",'X', 81)
    ALARM_ON_PRIMARY_INTERRUPT = ("AlarmOnPrimaryInterrupt", 'Y', 85)
    #FAULT_CODE_RECORD = ("FaultCodeRecord", 'Z', 82)


    def get_name(self):
        return self.value[0]

    def get_code(self):
        return self.value[1]

    def get_pin(self):
        return self.value[2]