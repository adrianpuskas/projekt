from enum import Enum

class Params(Enum):
    GRID_RATING_VOLTAGE = ('Grid rating voltage', 'V', None, 60)
    GRID_RATING_FREQUENCY = ('Grid rating frequency', 'Hz', None, 61)
    AC_OUTPUT_VOLTAGE = ('AC output voltage', "V", 97, 62)
    AC_OUTPUT_FREQUENCY = ('AC output frequency', "Hz", 98, 63)
    AC_OUTPUT_APPARENT_POWER = ('AC output apparent power', "VA", None,64)
    AC_OUTPUT_ACTIVE_POWER = ('AC output active power', "W", None, 65)
    BATTERY_RECHARGE_VOLTAGE = ('Battery re-charge voltage', 'V', 86, None)
    BATTERY_UNDER_VOLTAGE = ('Battery under voltage', 'V', 87, None)
    BATTERY_BULK_VOLTAGE = ('Battery bulk voltage', 'V', 88, None)
    BATTERY_FLOAT_VOLTAGE = ('Battery float voltage', 'V', 89, None)
    BATTERY_TYPE = ('Battery type', '', 90, None)
    CURRENT_MAX_AC_CHARGING_CURRENT = ('Current max AC charging current', 'A', 91, None)
    CURRENT_MAX_CHARGING_CURRENT = ('Current max charging current', 'A', 92, None)
    INPUT_VOLTAGE_RANGE = ('Input voltage range', '', 93, None)
    OUTPUT_SOURCE_PRIORITY = ('Output source priority', '', 94, None)
    CHARGER_SOURCE_PRIORITY = ('Charger source priority', '', 95, None)
    BATTERY_RE_DISCHARGE_VOLTAGE = ('Battery re-discharge voltage', 'V', 96, None)
    OUTPUT_LOAD_PERCENT = ('Output load percent', '%', None, 66)
    BUS_VOLTAGE = ('BUS voltage', 'V', None, 67)
    BATTERY_VOLTAGE = ('Battery voltage', 'V', None, 68)
    BATTERY_CURRENT = ('Battery current', 'A', None, 69)
    BATTERY_CAPACITY = ('Battery capacity', '%', None, 70)
    INVERTER_HEAT_SINK_TEMPERATURE = ('Inverter heat sink temperature', '℃', None, 71)
    PV_INPUT_CURRENT_BATTERY = ('PV Input current for battery', 'A', None, 72)
    PV_INPUT_VOLTAGE = ('PV Input voltage', 'V', None, 73)
    ### PV2 ###
    PV2_INPUT_CURRENT_BATTERY = ('PV2 Input current for battery', 'A', None, 25)
    PV2_INPUT_VOLTAGE = ('PV2 Input voltage', 'V', None, 26)
    PV2_INPUT_POWER = ('PV2 input power', 'W', None, 27)
    ###  ###
    BATTERY_VOLTAGE_SCC = ('Battery voltage from SCC', 'V', None, 74)
    BATTERY_POWER = ('Battery power', 'W', None, 75)
    PV_INPUT_POWER = ('PV input power', 'W', None, 76)

    def get_name(self):
        return self.value[0]

    def get_unit(self):
        return self.value[1]

    def get_pin_set_value(self):
        return self.value[2]

    def get_pin_actual_value(self):
        return self.value[3]