def BMS_20Ah_t_CheckSum(data):
    """
    校检和
    checksum = (Byte0+Byte1 …+ Byte6) XOR 0xFF
    """
    _sum = 0
    for byte in data[:7]:
        _sum += byte
    return (_sum ^ 0xFF) & 0xFF  # To mimic uint8_t behavior in C


class BMS_20Ah_t:
    def __init__(self):
        self.BMS_AllowedPeakChrgPower_Valid = False
        self.BMS_AllowedPeakChrgPower = 0.0
        self.BMS_AllowedPeakDischrgPower_Valid = False
        self.BMS_AllowedPeakDischrgPower = 0.0
        self.BMS_AllowedContinusChrgPower_Valid = False
        self.BMS_AllowedContinusChrgPower = 0.0
        self.BMS_AllowedContinusDischrgPower_Valid = False
        self.BMS_AllowedContinusDischrgPower = 0.0
        self.BMS_20Ah_rollingCounter = 0
        self.BMS_20Ah_CheckSum = 0
        self.RAW_Data = []


def BMS_20Ah_t_Decode(data, bms_20Ah: BMS_20Ah_t):
    bms_20Ah_temp = BMS_20Ah_t()
    if data[7] != BMS_20Ah_t_CheckSum(data):
        return False

    temp = 0

    temp = ((data[0] & 0xFF) << 4) | ((data[1] & 0xF0) >> 4)
    bms_20Ah_temp.BMS_AllowedPeakChrgPower_Valid = temp < 0xFFF
    bms_20Ah_temp.BMS_AllowedPeakChrgPower = float(temp) * 0.05

    temp = ((data[1] & 0x0F) << 8) | (data[2] & 0xFF)
    bms_20Ah_temp.BMS_AllowedPeakDischrgPower_Valid = temp < 0xFFF
    bms_20Ah_temp.BMS_AllowedPeakDischrgPower = float(temp) * 0.05

    temp = ((data[3] & 0xFF) << 4) | ((data[4] & 0xF0) >> 4)
    bms_20Ah_temp.BMS_AllowedContinusChrgPower_Valid = temp < 0xFFF
    bms_20Ah_temp.BMS_AllowedContinusChrgPower = float(temp) * 0.05

    temp = ((data[4] & 0x0F) << 8) | (data[5] & 0xFF)
    bms_20Ah_temp.BMS_AllowedContinusDischrgPower_Valid = temp < 0xFFF
    bms_20Ah_temp.BMS_AllowedContinusDischrgPower = float(temp) * 0.05

    bms_20Ah_temp.BMS_20Ah_rollingCounter = data[6] & 0x0F
    bms_20Ah_temp.BMS_20Ah_CheckSum = data[7]

    bms_20Ah_temp.RAW_Data = data[:]
    bms_20Ah.__dict__ = bms_20Ah_temp.__dict__
    return True


class BMS_210h_t:
    def __init__(self):
        self.BMS_Sys_MinCellV_Valid = False
        self.BMS_Sys_MinCellV = 0.0
        self.BMS_Sys_MaxCellV_Valid = False
        self.BMS_Sys_MaxCellV = 0.0
        self.BMS_Sys_MinCellV_No = 0
        self.BMS_Sys_MaxCellV_No = 0
        self.BMS_PowerLimitRequest = 0
        self.BMS_210h_RollingCounter = 0
        self.BMS_210h_CRC8 = 0
        self.RAW_Data = []


def BMS_210h_t_Decode(data, bms_210h):
    bms_210h_temp = BMS_210h_t()
    temp = 0

    temp = ((data[0] & 0xFF) << 8) | (data[1] & 0xFF)
    bms_210h_temp.BMS_Sys_MinCellV_Valid = temp < 0xFFFF
    bms_210h_temp.BMS_Sys_MinCellV = float(temp) * 0.001
    temp = ((data[2] & 0xFF) << 8) | (data[3] & 0xFF)
    bms_210h_temp.BMS_Sys_MaxCellV_Valid = temp < 0xFFFF
    bms_210h_temp.BMS_Sys_MaxCellV = float(temp) * 0.001
    bms_210h_temp.BMS_Sys_MinCellV_No = data[4]
    bms_210h_temp.BMS_Sys_MaxCellV_No = data[5]
    bms_210h_temp.BMS_PowerLimitRequest = (data[6] >> 4) & 0x03
    bms_210h_temp.BMS_210h_RollingCounter = data[6] & 0x0F
    bms_210h_temp.BMS_210h_CRC8 = data[7]

    bms_210h_temp.RAW_Data = data[:]
    bms_210h.__dict__ = bms_210h_temp.__dict__
    return True


def BMS_212h_t_Decode(data, bms_212h):
    bms_212h_temp = BMS_212h_t()
    temp = 0

    temp = data[0]
    bms_212h_temp.BMS_Sys_MinCellT = float(temp) - 50
    temp = data[1]
    bms_212h_temp.BMS_Sys_MaxCellT = float(temp) - 50
    bms_212h_temp.BMS_Sys_MinCellT_No = data[5]
    bms_212h_temp.BMS_Sys_MaxCellT_No = data[6]
    bms_212h_temp.BMS_FastChrgTemp = float(data[7]) - 50

    bms_212h_temp.BMS_Sys_MaxCellT_Valid = data[0] < 0xFF
    bms_212h_temp.BMS_Sys_MinCellT_Valid = data[1] < 0xFF
    bms_212h_temp.BMS_Sys_MaxCellT_No_Valid = data[5] < 0xFF
    bms_212h_temp.BMS_Sys_MinCellT_No_Valid = data[6] < 0xFF
    bms_212h_temp.BMS_FastChrgTemp_Valid = data[7] < 0xFF

    bms_212h_temp.RAW_Data = data[:]
    bms_212h.__dict__ = bms_212h_temp.__dict__
    return True


def BMS_216h_t_Decode(data, bms_216h):
    bms_216h_temp = BMS_216h_t()
    temp = 0

    temp = ((data[0] & 0xFF) << 8) | (data[1] & 0xFF)
    bms_216h_temp.BMS_PosInsulationResistance_Valid = temp < 0xFFFF
    bms_216h_temp.BMS_PosInsulationResistance = float(temp)

    temp = ((data[2] & 0xFF) << 8) | (data[3] & 0xFF)
    bms_216h_temp.BMS_NegInsulationResistance_Valid = temp < 0xFFFF
    bms_216h_temp.BMS_NegInsulationResistance = float(temp)

    bms_216h_temp.BMS_Sys_SOC = data[4]
    bms_216h_temp.BMS_Sys_SOC_Valid = data[4] < 0xFF

    bms_216h_temp.BMS_Sys_SOH = data[5]
    bms_216h_temp.BMS_Sys_SOH_Valid = data[5] < 0xFF

    temp = ((data[6] & 0x03) << 8) | (data[7] & 0xFF)
    bms_216h_temp.BMS_Sys_SOE_Valid = temp < 0x3FF
    bms_216h_temp.BMS_Sys_SOE = float(temp) * 0.1

    bms_216h_temp.RAW_Data = data[:]
    bms_216h.__dict__ = bms_216h_temp.__dict__
    return True


class BMS_212h_t:
    def __init__(self):
        self.BMS_Sys_MinCellT = 0.0
        self.BMS_Sys_MaxCellT = 0.0
        self.BMS_Sys_MinCellT_No = 0
        self.BMS_Sys_MaxCellT_No = 0
        self.BMS_FastChrgTemp = 0.0
        self.BMS_Sys_MaxCellT_Valid = False
        self.BMS_Sys_MinCellT_Valid = False
        self.BMS_Sys_MaxCellT_No_Valid = False
        self.BMS_Sys_MinCellT_No_Valid = False
        self.BMS_FastChrgTemp_Valid = False
        self.RAW_Data = []


class BMS_216h_t:
    def __init__(self):
        self.BMS_PosInsulationResistance_Valid = False
        self.BMS_PosInsulationResistance = 0.0
        self.BMS_NegInsulationResistance_Valid = False
        self.BMS_NegInsulationResistance = 0.0
        self.BMS_Sys_SOC = 0
        self.BMS_Sys_SOC_Valid = False
        self.BMS_Sys_SOH = 0
        self.BMS_Sys_SOH_Valid = False
        self.BMS_Sys_SOE = 0.0
        self.BMS_Sys_SOE_Valid = False
        self.RAW_Data = []


def BMS_214h_t_Decode(data, bms_214h):
    bms_214h_temp = BMS_214h_t()
    temp = 0

    temp = ((data[0] & 0xFF) << 8) | (data[1] & 0xFF)
    bms_214h_temp.BMS_Chg_RequestSumV = float(temp) * 0.1

    temp = ((data[2] & 0xFF) << 8) | (data[3] & 0xFF)
    bms_214h_temp.BMS_Chg_RequestCur = float(temp) * 0.1

    temp = (data[4] >> 2) & 0x1F
    bms_214h_temp.BMS_ChargingTimeRemain_h_Valid = temp < 0x1F
    bms_214h_temp.BMS_ChargingTimeRemain_h = temp

    bms_214h_temp.BMS_OBC_IVU_Enable = (data[4] & 0x80) >> 7

    temp = ((data[4] & 0x03) << 8) | (data[5] & 0xFF)
    bms_214h_temp.BMS_DCChargerMaxAllowablePower_Valid = temp < 0x3FF
    bms_214h_temp.BMS_DCChargerMaxAllowablePower = float(temp) * 0.1

    temp = (data[6] >> 2) & 0x3F
    bms_214h_temp.BMS_ChargingTimeRemain_min_Valid = temp < 0x3F
    bms_214h_temp.BMS_ChargingTimeRemain_min = temp

    temp = ((data[6] & 0x03) << 8) | (data[7] & 0xFF)
    bms_214h_temp.BMS_ChargingTotalPower_Valid = temp < 0x3FF
    bms_214h_temp.BMS_ChargingTotalPower = float(temp) * 0.1

    bms_214h_temp.RAW_Data = data[:]
    bms_214h.__dict__ = bms_214h_temp.__dict__
    return True


class BMS_214h_t:
    def __init__(self):
        self.BMS_Chg_RequestSumV = 0.0
        self.BMS_Chg_RequestCur = 0.0
        self.BMS_ChargingTimeRemain_h_Valid = False
        self.BMS_ChargingTimeRemain_h = 0
        self.BMS_OBC_IVU_Enable = 0
        self.BMS_DCChargerMaxAllowablePower_Valid = False
        self.BMS_DCChargerMaxAllowablePower = 0.0
        self.BMS_ChargingTimeRemain_min_Valid = False
        self.BMS_ChargingTimeRemain_min = 0
        self.BMS_ChargingTotalPower_Valid = False
        self.BMS_ChargingTotalPower = 0.0
        self.RAW_Data = []


def THREE_OBC_300h_t_Decode(data, obc_300h):
    obc_300h_temp = THREE_OBC_300h_t()
    temp = 0

    temp = ((data[3] & 0xFF) << 8) | (data[4] & 0xFF)
    obc_300h_temp.OBC_ChargerOutputVoltage_Valid = temp < 0xFF
    obc_300h_temp.OBC_ChargerOutputVoltage = float(temp) * 0.1

    temp = ((data[5] & 0xFF) << 2) | (data[6] >> 6)
    obc_300h_temp.OBC_ChargerOutputCurrent_Valid = temp < 0x3FF
    obc_300h_temp.OBC_ChargerOutputCurrent = float(temp) * 0.1

    temp = ((data[6] & 0x3F) << 4) | (data[7] >> 4)
    obc_300h_temp.OBC_ChargerMaxAllowableOutputPower = float(temp) * 0.1
    obc_300h_temp.OBC_ChargerMaxAllowableOutputPower_Valid = temp < 0x3FF

    obc_300h_temp.RAW_Data = data[:]
    obc_300h.__dict__ = obc_300h_temp.__dict__
    return True


class THREE_OBC_300h_t:
    def __init__(self):
        self.OBC_ChargerOutputVoltage_Valid = False
        self.OBC_ChargerOutputVoltage = 0.0
        self.OBC_ChargerOutputCurrent_Valid = False
        self.OBC_ChargerOutputCurrent = 0.0
        self.OBC_ChargerMaxAllowableOutputPower = 0.0
        self.OBC_ChargerMaxAllowableOutputPower_Valid = False
        self.RAW_Data = []



class BMS_200h_t:
    def __init__(self):
        self.BMS_Sys_TotalVoltage = 0.0
        self.BMS_Sys_SumCurrent = 0.0
        self.BMS_battery_outside_Voltage_Valid = False
        self.BMS_battery_outside_Voltage = 0.0
        self.BMS_Sys_SOC2_Valid = False
        self.BMS_Sys_SOC2 = 0.0
        self.RAW_Data = []

def BMS_200h_t_Decode(data, bms_200h):
    bms_200h_temp = BMS_200h_t()
    temp = 0

    temp = ((data[0] & 0xFF) << 8) | (data[1] & 0xFF)
    bms_200h_temp.BMS_Sys_TotalVoltage = float(temp) * 0.1

    temp = ((data[2] & 0xFF) << 8) | (data[3] & 0xFF)
    bms_200h_temp.BMS_Sys_SumCurrent = float(temp) * 0.1 - 3000

    temp = ((data[4] & 0xFF) << 8) | (data[5] & 0xFF)
    bms_200h_temp.BMS_battery_outside_Voltage_Valid = temp < 0xFFFF
    bms_200h_temp.BMS_battery_outside_Voltage = float(temp) * 0.1

    temp = data[6]
    temp = temp << 2
    temp = temp | (data[7] >> 6)
    bms_200h_temp.BMS_Sys_SOC2_Valid = temp < 0x3FF
    bms_200h_temp.BMS_Sys_SOC2 = float(temp) * 0.1

    bms_200h_temp.RAW_Data = data[:]
    bms_200h.__dict__ = bms_200h_temp.__dict__
    return True



    """
    BMS_Err_DischrgAnodeRelay	"Main relay (discharge main connection) fault information
主接触器（放电主接）故障信息"	Motorola LSB	0	0	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Normal正常
0x2:Cake烧结
0x3:Failure错误"
BMS_DischargeAnodeRelay_status	"Main relay State (discharge main connection)
主接触器状态（放电主接）"	Motorola LSB	0	2	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Open
0x2:Connect
0x3:Reserved"
BMS_Boot_Detection	"Boot detection
开机检测"	Motorola LSB	0	4	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:False；
0x1:Pull"
BMS_A	"A+ singnal
A+信号"	Motorola LSB	0	5	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:False；
0x1:Pull"
BMS_BatteryTempKeepStatus	电池包保温状态	Motorola LSB	0	6	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:未开启
0x1:等待中
0x2:保温中
0x3:预留"
BMS_BatteryTempPrecontrolAvailable	电池包在途温控功能可用性	Motorola LSB	1	8	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:Avalilable
0x1:Unavailable"
BMS_BatteryTempPrecontrolSts	电池包在途温控功能状态	Motorola LSB	1	9	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:OFF
0x1:ON"
BMS_ElectronicLockRequest	"ElectronicLockRequest
电子锁请求"	Motorola LSB	1	10	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:Invalid
0x1:lock
0x2:unlock
0x3:Reserved"
BMS_Relay_HEAT	"Relay Status-Heating
继电器状态-加热（预留）"	Motorola LSB	1	10	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:OFF断开；
0x1:ON吸合；
0x2:adhesion粘连；
0x3:reserved保留"
BMS_Err_PrechargeAnodeRelay	"Pre-charging relay fault information
预充接触器故障信息"	Motorola LSB	1	12	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Normal正常
0x2:Cake烧结
0x3:Failure错误"
BMS_Precharge_anode_Relay_status	"Pre-recharge CONTACTOR status
预充接触器状态"	Motorola LSB	1	14	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Open
0x2:Connect
0x3:Reserved"
BMS_Err_DischrgCathodeRelay	"DischrgCathodeRelay Fault Information
负极接触器故障信息"	Motorola LSB	2	16	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Normal正常
0x2:Cake烧结
0x3:Failure错误"
BMS_DischrgCathodeRelay_status	"Cathode contactor Status (reserved)
负极接触器状态"	Motorola LSB	2	18	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Open打
0x2:Connect
0x3:Reserved"
BMS_Err_ChargeRelay 	"Charging contactor Fault Information
快充接触器故障信息"	Motorola LSB	2	20	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Normal正常
0x2:Cake烧结
0x3:Failure错误"
BMS_ChargeRelay_status 	"Charging relay Status
快充接触器状态"	Motorola LSB	2	22	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Open
0x2:Connect
0x3:Reserved"
BMS_ChrgHeatColEnable	"Charging&Heat&cooling enable
充电、加热及冷却使能"	Motorola LSB	3	24	Cycle	3	Unsigned	1	0	0	7	0x0	0x7	0x0	0x0			"0x0:无效
0x1:交流充电允许
0x2:交流加热/冷却允许
0x3:直流充电允许；
0x4:直流加热/冷却允许；
0x5:Reserved
0x6:Reserved
0x7:Reserved"
BMS_Sys_ChgorDisChrgSts	"Battery pack charging and discharging status
电池包充放电状态"	Motorola LSB	3	27	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0	0x0			"0x0:Invalid
0x1:Discharging
0x2:Charging（快充中）
0x3:Charging（慢充中）"
BMS_FastChrgSts	"BMS FastCharge Status
BMS快充充电状态"	Motorola LSB	3	29	Cycle	3	Unsigned	1	0	0	7	0x0	0x7	0x0	0x0			"0x0:Invalid
0x1:Not charged未充电
0x2:充电就绪
0x3:充电中
0x4:充电完成
0x5:充电结束
0x6:故障结束
0x7:Reserved保留"
BMS_SlowChrgSts	"BMS SlowCharge Status
BMS慢充充电状态"	Motorola LSB	4	32	Cycle	3	Unsigned	1	0	0	7	0x0	0x7	0x0	0x0			"0x0:Invalid
0x1:Not charged未充电
0x2:充电就绪
0x3:充电中
0x4:充电完成
0x5:充电结束
0x6:故障结束
0x7:Reserved保留"
BMS_ChrgCouplesSt	"Fast charge connection status
快充连接状态"	Motorola LSB	4	37	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:Disconnected
0x1:Quick_charge_Connect
0x2:Reserved
0x3:Reserved"
BMS_req_ConnectChargeRelay	"Request Connect Charge Relay
请求吸和充电继电器（预留）"	Motorola LSB	5	40	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:no request
0x1:open
0x2:Connect
0x3:Reserved"
BMS_WirelessChrgSts	"Wireless Charging Status
无线充电状态"	Motorola LSB	5	42	Cycle	3	Unsigned	1	0	0	7	0x0	0x7	0x0	0x0			"0x0: Invalid
0x1: Not charged未充电
0x2: 充电就绪
0x3: 充电中
0x4: 充电完成
0x5: 充电结束
0x6: 故障结束
0x7: Reserved保留"
BMS_CC2	"CC2
直充连接信号"	Motorola LSB	6	50	Cycle	3	Unsigned	1	0	0	7	0x0	0x7	0x0				"0x0:disconnected未连接；
0x1:connected连接；"
BMS_AllowedChrgMaxPower	"Max Allowed Charge Power
最大允许充电电量"	Motorola LSB	7	56	Cycle	7	Unsigned	1	0	0	100	0x0	0x64	0x0	0x7F		%	

"""



class BMS_202h_Str_t:
    def __init__(self):
        self.BMS_Err_DischrgAnodeRelay = ""
        self.BMS_DischargeAnodeRelay_status = ""
        self.BMS_Boot_Detection = ""
        self.BMS_A = ""
        self.BMS_BatteryTempKeepStatus = ""
        self.BMS_BatteryTempPrecontrolAvailable = ""
        self.BMS_BatteryTempPrecontrolSts = ""
        self.BMS_ElectronicLockRequest = ""
        self.BMS_Relay_HEAT = ""
        self.BMS_Err_PrechargeAnodeRelay = ""
        self.BMS_Precharge_anode_Relay_status = ""
        self.BMS_Err_DischrgCathodeRelay = ""
        self.BMS_DischrgCathodeRelay_status = ""
        self.BMS_Err_ChargeRelay = ""
        self.BMS_ChargeRelay_status = ""
        self.BMS_ChrgHeatColEnable = ""
        self.BMS_Sys_ChgorDisChrgSts = ""
        self.BMS_FastChrgSts = ""
        self.BMS_SlowChrgSts = ""
        self.BMS_ChrgCouplesSt = ""
        self.BMS_req_ConnectChargeRelay = ""
        self.BMS_WirelessChrgSts = ""
        self.BMS_CC2 = ""
        self.BMS_AllowedChrgMaxPower = ""

        self.BMS_Err_DischrgAnodeRelay_dict = {"0": "Invalid", "1": "正常", "2": "烧结", "3": "错误"}
        self.BMS_DischargeAnodeRelay_status_dict = {"0": "Invalid", "1": "Open", "2": "Connect", "3": "Reserved"}
        self.BMS_Boot_Detection_dict = {"0": "False", "1": "Pull"}
        self.BMS_A_dict = {"0": "False", "1": "Pull"}
        self.BMS_BatteryTempKeepStatus_dict = {"0": "未开启", "1": "等待中", "2": "保温中", "3": "预留"}
        self.BMS_BatteryTempPrecontrolAvailable_dict = {"0": "Avalilable", "1": "Unavailable"}
        self.BMS_BatteryTempPrecontrolSts_dict = {"0": "OFF", "1": "ON"}
        self.BMS_ElectronicLockRequest_dict = {"0": "Invalid", "1": "lock", "2": "unlock", "3": "Reserved"}
        self.BMS_Relay_HEAT_dict = {"0": "OFF断开", "1": "ON吸合", "2": "adhesion粘连", "3": "reserved保留"}
        self.BMS_Err_PrechargeAnodeRelay_dict = {"0": "Invalid", "1": "Normal正常", "2": "Cake烧结", "3": "Failure错误"}
        self.BMS_Precharge_anode_Relay_status_dict = {"0": "Invalid", "1": "Open", "2": "Connect", "3": "Reserved"}
        self.BMS_Err_DischrgCathodeRelay_dict = {"0": "Invalid", "1": "Normal正常", "2": "Cake烧结", "3": "Failure错误"}
        self.BMS_DischrgCathodeRelay_status_dict = {"0": "Invalid", "1": "Open打开", "2": "Connect", "3": "Reserved"}
        self.BMS_Err_ChargeRelay_dict = {"0": "Invalid", "1": "Normal正常", "2": "Cake烧结", "3": "Failure错误"}
        self.BMS_ChargeRelay_status_dict = {"0": "Invalid", "1": "Open", "2": "Connect", "3": "Reserved"}
        self.BMS_ChrgHeatColEnable_dict = {"0": "无效", "1": "交流充电允许", "2": "交流加热/冷却允许", "3": "直流充电允许",
                                           "4": "直流加热/冷却允许", "5": "Reserved", "6": "Reserved", "7": "Reserved"}
        self.BMS_Sys_ChgorDisChrgSts_dict = {"0": "Invalid", "1": "Discharging", "2": "Charging（快充中）", "3": "Charging（慢充中）"}
        self.BMS_FastChrgSts_dict = {"0": "Invalid", "1": "Not charged未充电", "2": "充电就绪", "3": "充电中", "4": "充电完成",
                                     "5": "充电结束", "6": "故障结束", "7": "Reserved保留"}
        self.BMS_SlowChrgSts_dict = {"0": "Invalid", "1": "Not charged未充电", "2": "充电就绪", "3": "充电中", "4": "充电完成",
                                     "5": "充电结束", "6": "故障结束", "7": "Reserved保留"}
        self.BMS_ChrgCouplesSt_dict = {"0": "Disconnected", "1": "Quick_charge_Connect", "2": "Reserved", "3": "Reserved"}
        self.BMS_req_ConnectChargeRelay_dict = {"0": "no request", "1": "open", "2": "Connect", "3": "Reserved"}
        self.BMS_WirelessChrgSts_dict = {"0": "Invalid", "1": "Not charged未充电", "2": "充电就绪", "3": "充电中", "4": "充电完成",
                                            "5": "充电结束", "6": "故障结束", "7": "Reserved保留"}
        self.BMS_CC2_dict = {"0": "disconnected未连接", "1": "connected连接"}


class BMS_202h_t:
    def __init__(self):
        self.BMS_Err_DischrgAnodeRelay = 0
        self.BMS_DischargeAnodeRelay_status = 0
        self.BMS_Boot_Detection = 0
        self.BMS_A = 0
        self.BMS_BatteryTempKeepStatus = 0
        self.BMS_BatteryTempPrecontrolAvailable = 0
        self.BMS_BatteryTempPrecontrolSts = 0
        self.BMS_ElectronicLockRequest = 0
        self.BMS_Relay_HEAT = 0
        self.BMS_Err_PrechargeAnodeRelay = 0
        self.BMS_Precharge_anode_Relay_status = 0
        self.BMS_Err_DischrgCathodeRelay = 0
        self.BMS_DischrgCathodeRelay_status = 0
        self.BMS_Err_ChargeRelay = 0
        self.BMS_ChargeRelay_status = 0
        self.BMS_ChrgHeatColEnable = 0
        self.BMS_Sys_ChgorDisChrgSts = 0
        self.BMS_FastChrgSts = 0
        self.BMS_SlowChrgSts = 0
        self.BMS_ChrgCouplesSt = 0
        self.BMS_req_ConnectChargeRelay = 0
        self.BMS_WirelessChrgSts = 0
        self.BMS_CC2 = 0
        self.BMS_AllowedChrgMaxPower = 0
        self.RAW_Data = []

    def toStrObj(self):
        bms_202h_str = BMS_202h_Str_t()
        bms_202h_str.BMS_Err_DischrgAnodeRelay = bms_202h_str.BMS_Err_DischrgAnodeRelay_dict[str(self.BMS_Err_DischrgAnodeRelay)]
        bms_202h_str.BMS_DischargeAnodeRelay_status = bms_202h_str.BMS_DischargeAnodeRelay_status_dict[str(self.BMS_DischargeAnodeRelay_status)]
        bms_202h_str.BMS_Boot_Detection = bms_202h_str.BMS_Boot_Detection_dict[str(self.BMS_Boot_Detection)]
        bms_202h_str.BMS_A = bms_202h_str.BMS_A_dict[str(self.BMS_A)]
        bms_202h_str.BMS_BatteryTempKeepStatus = bms_202h_str.BMS_BatteryTempKeepStatus_dict[str(self.BMS_BatteryTempKeepStatus)]
        bms_202h_str.BMS_BatteryTempPrecontrolAvailable = bms_202h_str.BMS_BatteryTempPrecontrolAvailable_dict[str(self.BMS_BatteryTempPrecontrolAvailable)]
        bms_202h_str.BMS_BatteryTempPrecontrolSts = bms_202h_str.BMS_BatteryTempPrecontrolSts_dict[str(self.BMS_BatteryTempPrecontrolSts)]
        bms_202h_str.BMS_ElectronicLockRequest = bms_202h_str.BMS_ElectronicLockRequest_dict[str(self.BMS_ElectronicLockRequest)]
        bms_202h_str.BMS_Relay_HEAT = bms_202h_str.BMS_Relay_HEAT_dict[str(self.BMS_Relay_HEAT)]
        bms_202h_str.BMS_Err_PrechargeAnodeRelay = bms_202h_str.BMS_Err_PrechargeAnodeRelay_dict[str(self.BMS_Err_PrechargeAnodeRelay)]
        bms_202h_str.BMS_Precharge_anode_Relay_status = bms_202h_str.BMS_Precharge_anode_Relay_status_dict[str(self.BMS_Precharge_anode_Relay_status)]
        bms_202h_str.BMS_Err_DischrgCathodeRelay = bms_202h_str.BMS_Err_DischrgCathodeRelay_dict[str(self.BMS_Err_DischrgCathodeRelay)]
        bms_202h_str.BMS_DischrgCathodeRelay_status = bms_202h_str.BMS_DischrgCathodeRelay_status_dict[str(self.BMS_DischrgCathodeRelay_status)]
        bms_202h_str.BMS_Err_ChargeRelay = bms_202h_str.BMS_Err_ChargeRelay_dict[str(self.BMS_Err_ChargeRelay)]
        bms_202h_str.BMS_ChargeRelay_status = bms_202h_str.BMS_ChargeRelay_status_dict[str(self.BMS_ChargeRelay_status)]
        bms_202h_str.BMS_ChrgHeatColEnable = bms_202h_str.BMS_ChrgHeatColEnable_dict[str(self.BMS_ChrgHeatColEnable)]
        bms_202h_str.BMS_Sys_ChgorDisChrgSts = bms_202h_str.BMS_Sys_ChgorDisChrgSts_dict[str(self.BMS_Sys_ChgorDisChrgSts)]
        bms_202h_str.BMS_FastChrgSts = bms_202h_str.BMS_FastChrgSts_dict[str(self.BMS_FastChrgSts)]
        bms_202h_str.BMS_SlowChrgSts = bms_202h_str.BMS_SlowChrgSts_dict[str(self.BMS_SlowChrgSts)]
        bms_202h_str.BMS_ChrgCouplesSt = bms_202h_str.BMS_ChrgCouplesSt_dict[str(self.BMS_ChrgCouplesSt)]
        bms_202h_str.BMS_req_ConnectChargeRelay = bms_202h_str.BMS_req_ConnectChargeRelay_dict[str(self.BMS_req_ConnectChargeRelay)]
        bms_202h_str.BMS_WirelessChrgSts = bms_202h_str.BMS_WirelessChrgSts_dict[str(self.BMS_WirelessChrgSts)]
        bms_202h_str.BMS_CC2 = bms_202h_str.BMS_CC2_dict[str(self.BMS_CC2)]
        bms_202h_str.BMS_AllowedChrgMaxPower = str(self.BMS_AllowedChrgMaxPower)
        return bms_202h_str

def BMS_202h_t_Decode(data, bms_202h):
    bms_202h_temp = BMS_202h_t()

    bms_202h_temp.BMS_Err_DischrgAnodeRelay = (data[0] >> 0) & 0x03
    bms_202h_temp.BMS_DischargeAnodeRelay_status = (data[0] >> 2) & 0x03
    bms_202h_temp.BMS_Boot_Detection = (data[0] >> 4) & 0x01
    bms_202h_temp.BMS_A = (data[0] >> 5) & 0x01
    bms_202h_temp.BMS_BatteryTempKeepStatus = (data[0] >> 6) & 0x03
    bms_202h_temp.BMS_BatteryTempPrecontrolAvailable = (data[1] >> 0) & 0x01
    bms_202h_temp.BMS_BatteryTempPrecontrolSts = (data[1] >> 1) & 0x01
    bms_202h_temp.BMS_ElectronicLockRequest = (data[1] >> 2) & 0x03
    bms_202h_temp.BMS_Relay_HEAT = (data[1] >> 2) & 0x03

    bms_202h_temp.BMS_Err_PrechargeAnodeRelay = (data[1] >> 4) & 0x03
    bms_202h_temp.BMS_Precharge_anode_Relay_status = (data[1] >> 6) & 0x03
    bms_202h_temp.BMS_Err_DischrgCathodeRelay = (data[2] >> 0) & 0x03
    bms_202h_temp.BMS_DischrgCathodeRelay_status = (data[2] >> 2) & 0x03
    bms_202h_temp.BMS_Err_ChargeRelay = (data[2] >> 4) & 0x03
    bms_202h_temp.BMS_ChargeRelay_status = (data[2] >> 6) & 0x03
    bms_202h_temp.BMS_ChrgHeatColEnable = (data[3] >> 0) & 0x07
    bms_202h_temp.BMS_Sys_ChgorDisChrgSts = (data[3] >> 3) & 0x03
    bms_202h_temp.BMS_FastChrgSts = (data[3] >> 5) & 0x07
    bms_202h_temp.BMS_SlowChrgSts = (data[4] >> 0) & 0x07
    bms_202h_temp.BMS_ChrgCouplesSt = (data[4] >> 3) & 0x03
    bms_202h_temp.BMS_req_ConnectChargeRelay = (data[5] >> 0) & 0x03
    bms_202h_temp.BMS_WirelessChrgSts = (data[5] >> 2) & 0x07
    bms_202h_temp.BMS_CC2 = (data[6] >> 2) & 0x03
    bms_202h_temp.BMS_AllowedChrgMaxPower = (data[7] >> 0) & 0x7F

    bms_202h_temp.RAW_Data = data[:]
    bms_202h.__dict__ = bms_202h_temp.__dict__
    return True

"""
    BMS_Powertrain_System_fault	"Battery system failure
电池系统故障"	Motorola LSB	0	0	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_cell_Voltage_low	"Battery monomer power down fault
电池单体电压低故障"	Motorola LSB	0	4	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_cell_Voltage_High	"High voltage fault of battery monomer
电池单体电压高故障"	Motorola LSB	0	6	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Battery_LowTemp_warning	"Battery pack Temperature Low fault
电池组温度低故障"	Motorola LSB	1	8	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Battery_HighTemp_warning	"Battery pack Temperature High fault
电池组温度高故障"	Motorola LSB	1	10	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_20ch_RollingCounter	"Rolling counter
循环计数器"	Motorola LSB	1	12	Cycle	4	Unsigned	1	0	0	15	0x0	0xF	0x0
BMS_SOCHigh_Warning	"Soc High Alarm
SOC高报警"	Motorola LSB	2	16	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_SOCLow_Warning	"Soc Low Alarm
SOC低报警"	Motorola LSB	2	18	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Battery_SumVoltage_High	"High total voltage of battery pack failure
电池包总电压高故障"	Motorola LSB	2	20	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Battery_SumVoltage_Low	"Battery pack total power down fault
电池包总电压低故障"	Motorola LSB	2	22	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_HVBatCellDiffFalt	"Battery Monomer Consistency Difference failure
电池单体一致性差故障"	Motorola LSB	3	24	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Err_OverChrging 	"Battery pack overcharge fault
电池包过充故障"	Motorola LSB	3	26	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Charger_Reminding	"Battery pack Charger Reminding
电池包充电提醒"	Motorola LSB	3	28	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:无提醒；
0x1:电量低，请及时充电；"
BMS_SOCJump_Warning	"Soc Jump Alarm
SOC跳变报警"	Motorola LSB	3	30	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_ThermalInvalidFault	"Thermal Invalid Fault
热失效故障"	Motorola LSB	4	32	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0: fault-free无故障；
0x1: fault 故障；
0x2~0x3: Reserved"
BMS_BatNotMatchFlt	"Battery mismatch Alarm
电池不匹配报警"	Motorola LSB	4	38	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:fault 故障；
0x2:Reserved
0x3:Reserved"
BMS_Err_ISO_LOW	"Insulation Low fault
绝缘低故障"	Motorola LSB	5	40	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Err_ChgCurrent_High	"Charging current is too large fault
充电电流过大故障"	Motorola LSB	5	42	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Err_DchCurrent_High	"Too large discharge current failure
放电电流过大故障"	Motorola LSB	5	44	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_Err_DtT_High	"The temperature difference is too big fault
温差过大故障"	Motorola LSB	5	46	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
ThermalManage_System_fault	"Thermal manage system fault
热管理系统故障"	Motorola LSB	6	48	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:无故障；
0x1:一级故障；
0x2:二级故障；
0x3:三级故障"
BMS_Err_comunicacion	"BMS Communication failure
BMS通讯故障"	Motorola LSB	6	50	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:Internal communication failure内部通讯故障；
0x2:External communication failure外部通讯故障；
0x3:内外部通讯故障"
BMS_Err_InterLock	"BMSHV Interlock fault
BMS高压互锁故障"	Motorola LSB	6	52	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:fault-free无故障；
0x1:Interlock faults互锁故障"
BMS_Circuit_Protection	"Short Circuit protection
短路保护"	Motorola LSB	6	53	Cycle	1	Unsigned	1	0	0	1	0x0	0x1	0x0				"0x0:normal正常；
0x1:open短路保护开启"
BMS_FeedFault	"BMS feed fault
蓄电池馈电故障"	Motorola LSB	6	54	Cycle	2	Unsigned	1	0	0	3	0x0	0x3	0x0				"0x0:fault-free无故障；
0x1:First-level faults一级故障；
0x2:Second-degree faults二级故障；
0x3:Level three faults三级故障"
BMS_20ch_CRC8	Byte0-Byte6的CRC8循环冗余检验值	Motorola LSB	7	56	Cycle	8	Unsigned	1	0	0	254	0x0	0xFE	0x0	0xFF

"""

class BMS_20Ch_Str_t:
    def __init__(self):
        self.BMS_Powertrain_System_fault = ""
        self.BMS_cell_Voltage_low = ""
        self.BMS_cell_Voltage_High = ""
        self.BMS_Battery_LowTemp_warning = ""
        self.BMS_Battery_HighTemp_warning = ""
        self.BMS_20ch_RollingCounter = ""
        self.BMS_SOCHigh_Warning = ""
        self.BMS_SOCLow_Warning = ""
        self.BMS_Battery_SumVoltage_High = ""
        self.BMS_Battery_SumVoltage_Low = ""
        self.BMS_HVBatCellDiffFalt = ""
        self.BMS_Err_OverChrging = ""
        self.BMS_Charger_Reminding = ""
        self.BMS_SOCJump_Warning = ""
        self.BMS_ThermalInvalidFault = ""
        self.BMS_BatNotMatchFlt = ""
        self.BMS_Err_ISO_LOW = ""
        self.BMS_Err_ChgCurrent_High = ""
        self.BMS_Err_DchCurrent_High = ""
        self.BMS_Err_DtT_High = ""
        self.ThermalManage_System_fault = ""
        self.BMS_Err_comunicacion = ""
        self.BMS_Err_InterLock = ""
        self.BMS_Circuit_Protection = ""
        self.BMS_FeedFault = ""
        self.BMS_20ch_CRC8 = ""

        self.BMS_Powertrain_System_fault_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_cell_Voltage_low_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_cell_Voltage_High_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Battery_LowTemp_warning_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Battery_HighTemp_warning_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_SOCHigh_Warning_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_SOCLow_Warning_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Battery_SumVoltage_High_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Battery_SumVoltage_Low_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_HVBatCellDiffFalt_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Err_OverChrging_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Charger_Reminding_dict = {"0": "无提醒", "1": "电量低，请及时充电"}
        self.BMS_SOCJump_Warning_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_ThermalInvalidFault_dict = {"0": "fault-free无故障", "1": "fault 故障", "2": "Reserved", "3": "Reserved"}
        self.BMS_BatNotMatchFlt_dict = {"0": "fault-free无故障", "1": "fault 故障", "2": "Reserved", "3": "Reserved"}
        self.BMS_Err_ISO_LOW_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Err_ChgCurrent_High_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Err_DchCurrent_High_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.BMS_Err_DtT_High_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}
        self.ThermalManage_System_fault_dict = {"0": "无故障", "1": "一级故障", "2": "二级故障", "3": "三级故障"}
        self.BMS_Err_comunicacion_dict = {"0": "fault-free无故障", "1": "Internal communication failure内部通讯故障", "2": "External communication failure外部通讯故障", "3": "内外部通讯故障"}
        self.BMS_Err_InterLock_dict = {"0": "fault-free无故障", "1": "Interlock faults互锁故障"}
        self.BMS_Circuit_Protection_dict = {"0": "normal正常", "1": "open短路保护开启"}
        self.BMS_FeedFault_dict = {"0": "fault-free无故障", "1": "First-level faults一级故障", "2": "Second-degree faults二级故障", "3": "Level three faults三级故障"}


class BMS_20Ch_t:
    def __init__(self):
        self.BMS_Powertrain_System_fault = 0
        self.BMS_cell_Voltage_low = 0
        self.BMS_cell_Voltage_High = 0
        self.BMS_Battery_LowTemp_warning = 0
        self.BMS_Battery_HighTemp_warning = 0
        self.BMS_20ch_RollingCounter = 0
        self.BMS_SOCHigh_Warning = 0
        self.BMS_SOCLow_Warning = 0
        self.BMS_Battery_SumVoltage_High = 0
        self.BMS_Battery_SumVoltage_Low = 0
        self.BMS_HVBatCellDiffFalt = 0
        self.BMS_Err_OverChrging = 0
        self.BMS_Charger_Reminding = 0
        self.BMS_SOCJump_Warning = 0
        self.BMS_ThermalInvalidFault = 0
        self.BMS_BatNotMatchFlt = 0
        self.BMS_Err_ISO_LOW = 0
        self.BMS_Err_ChgCurrent_High = 0
        self.BMS_Err_DchCurrent_High = 0
        self.BMS_Err_DtT_High = 0
        self.ThermalManage_System_fault = 0
        self.BMS_Err_comunicacion = 0
        self.BMS_Err_InterLock = 0
        self.BMS_Circuit_Protection = 0
        self.BMS_FeedFault = 0
        self.BMS_20ch_CRC8 = 0
        self.BMS_20ch_CRC8_Valid = False
        self.RAW_Data = [0, 0, 0, 0, 0, 0, 0, 0]

    def toStrObj(self):
        bms_20Ch_str = BMS_20Ch_Str_t()
        bms_20Ch_str.BMS_Powertrain_System_fault = bms_20Ch_str.BMS_Powertrain_System_fault_dict[str(self.BMS_Powertrain_System_fault)]
        bms_20Ch_str.BMS_cell_Voltage_low = bms_20Ch_str.BMS_cell_Voltage_low_dict[str(self.BMS_cell_Voltage_low)]
        bms_20Ch_str.BMS_cell_Voltage_High = bms_20Ch_str.BMS_cell_Voltage_High_dict[str(self.BMS_cell_Voltage_High)]
        bms_20Ch_str.BMS_Battery_LowTemp_warning = bms_20Ch_str.BMS_Battery_LowTemp_warning_dict[str(self.BMS_Battery_LowTemp_warning)]
        bms_20Ch_str.BMS_Battery_HighTemp_warning = bms_20Ch_str.BMS_Battery_HighTemp_warning_dict[str(self.BMS_Battery_HighTemp_warning)]
        bms_20Ch_str.BMS_SOCHigh_Warning = bms_20Ch_str.BMS_SOCHigh_Warning_dict[str(self.BMS_SOCHigh_Warning)]
        bms_20Ch_str.BMS_SOCLow_Warning = bms_20Ch_str.BMS_SOCLow_Warning_dict[str(self.BMS_SOCLow_Warning)]
        bms_20Ch_str.BMS_Battery_SumVoltage_High = bms_20Ch_str.BMS_Battery_SumVoltage_High_dict[str(self.BMS_Battery_SumVoltage_High)]
        bms_20Ch_str.BMS_Battery_SumVoltage_Low = bms_20Ch_str.BMS_Battery_SumVoltage_Low_dict[str(self.BMS_Battery_SumVoltage_Low)]
        bms_20Ch_str.BMS_HVBatCellDiffFalt = bms_20Ch_str.BMS_HVBatCellDiffFalt_dict[str(self.BMS_HVBatCellDiffFalt)]
        bms_20Ch_str.BMS_Err_OverChrging = bms_20Ch_str.BMS_Err_OverChrging_dict[str(self.BMS_Err_OverChrging)]
        bms_20Ch_str.BMS_Charger_Reminding = bms_20Ch_str.BMS_Charger_Reminding_dict[str(self.BMS_Charger_Reminding)]
        bms_20Ch_str.BMS_SOCJump_Warning = bms_20Ch_str.BMS_SOCJump_Warning_dict[str(self.BMS_SOCJump_Warning)]
        bms_20Ch_str.BMS_ThermalInvalidFault = bms_20Ch_str.BMS_ThermalInvalidFault_dict[str(self.BMS_ThermalInvalidFault)]
        bms_20Ch_str.BMS_BatNotMatchFlt = bms_20Ch_str.BMS_BatNotMatchFlt_dict[str(self.BMS_BatNotMatchFlt)]
        bms_20Ch_str.BMS_Err_ISO_LOW = bms_20Ch_str.BMS_Err_ISO_LOW_dict[str(self.BMS_Err_ISO_LOW)]
        bms_20Ch_str.BMS_Err_ChgCurrent_High = bms_20Ch_str.BMS_Err_ChgCurrent_High_dict[str(self.BMS_Err_ChgCurrent_High)]
        bms_20Ch_str.BMS_Err_DchCurrent_High = bms_20Ch_str.BMS_Err_DchCurrent_High_dict[str(self.BMS_Err_DchCurrent_High)]
        bms_20Ch_str.BMS_Err_DtT_High = bms_20Ch_str.BMS_Err_DtT_High_dict[str(self.BMS_Err_DtT_High)]
        bms_20Ch_str.ThermalManage_System_fault = bms_20Ch_str.ThermalManage_System_fault_dict[str(self.ThermalManage_System_fault)]
        bms_20Ch_str.BMS_Err_comunicacion = bms_20Ch_str.BMS_Err_comunicacion_dict[str(self.BMS_Err_comunicacion)]
        bms_20Ch_str.BMS_Err_InterLock = bms_20Ch_str.BMS_Err_InterLock_dict[str(self.BMS_Err_InterLock)]
        bms_20Ch_str.BMS_Circuit_Protection = bms_20Ch_str.BMS_Circuit_Protection_dict[str(self.BMS_Circuit_Protection)]
        bms_20Ch_str.BMS_FeedFault = bms_20Ch_str.BMS_FeedFault_dict[str(self.BMS_FeedFault)]
        bms_20Ch_str.BMS_20ch_CRC8 = str(self.BMS_20ch_CRC8)
        return bms_20Ch_str

def BMS_20Ch_t_Decode(data, bms_20Ch):
    bms_20Ch_temp = BMS_20Ch_t()

    bms_20Ch_temp.BMS_Powertrain_System_fault = (data[0] >> 0) & 0x03
    bms_20Ch_temp.BMS_cell_Voltage_low = (data[0] >> 4) & 0x03
    bms_20Ch_temp.BMS_cell_Voltage_High = (data[0] >> 6) & 0x03

    bms_20Ch_temp.BMS_Battery_LowTemp_warning = (data[1] >> 0) & 0x03
    bms_20Ch_temp.BMS_Battery_HighTemp_warning = (data[1] >> 2) & 0x03
    bms_20Ch_temp.BMS_20ch_RollingCounter = (data[1] >> 4) & 0x0F

    bms_20Ch_temp.BMS_SOCHigh_Warning = (data[2] >> 0) & 0x03
    bms_20Ch_temp.BMS_SOCLow_Warning = (data[2] >> 2) & 0x03
    bms_20Ch_temp.BMS_Battery_SumVoltage_High = (data[2] >> 4) & 0x03
    bms_20Ch_temp.BMS_Battery_SumVoltage_Low = (data[2] >> 6) & 0x03

    bms_20Ch_temp.BMS_HVBatCellDiffFalt = (data[3] >> 0) & 0x03
    bms_20Ch_temp.BMS_Err_OverChrging = (data[3] >> 2) & 0x03
    bms_20Ch_temp.BMS_Charger_Reminding = (data[3] >> 4) & 0x01
    bms_20Ch_temp.BMS_SOCJump_Warning = (data[3] >> 6) & 0x03

    bms_20Ch_temp.BMS_ThermalInvalidFault = (data[4] >> 0) & 0x03
    bms_20Ch_temp.BMS_BatNotMatchFlt = (data[4] >> 6) & 0x03

    bms_20Ch_temp.BMS_Err_ISO_LOW = (data[5] >> 0) & 0x03
    bms_20Ch_temp.BMS_Err_ChgCurrent_High = (data[5] >> 2) & 0x03
    bms_20Ch_temp.BMS_Err_DchCurrent_High = (data[5] >> 4) & 0x03
    bms_20Ch_temp.BMS_Err_DtT_High = (data[5] >> 6) & 0x03

    bms_20Ch_temp.ThermalManage_System_fault = (data[6] >> 0) & 0x03
    bms_20Ch_temp.BMS_Err_comunicacion = (data[6] >> 2) & 0x03
    bms_20Ch_temp.BMS_Err_InterLock = (data[6] >> 4) & 0x01
    bms_20Ch_temp.BMS_Circuit_Protection = (data[6] >> 5) & 0x01
    bms_20Ch_temp.BMS_FeedFault = (data[6] >> 6) & 0x03
    bms_20Ch_temp.BMS_20ch_CRC8 = data[7]

    bms_20Ch_temp.BMS_20ch_CRC8_Valid = bms_20Ch_temp.BMS_20ch_CRC8 < 0xFF

    bms_20Ch_temp.RAW_Data = data[:]
    bms_20Ch.__dict__ = bms_20Ch_temp.__dict__
    return True

