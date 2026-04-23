import struct
import HDL_CAN

REGx_INPUT_AC_VOLT_MAX = 530  # Unit: V
REGx_INPUT_AC_VOLT_MIN = 260  # Unit: V
REGx_INPUT_AC_CURR_MAX = 58  # Unit: A
REGx_INPUT_AC_CURR_MIN = 0  # Unit: A

REGx_OUTPUT_DC_VOLT_MAX = 1000  # Unit: V
REGx_OUTPUT_DC_VOLT_MIN = 150  # Unit: V # Actual the minimum voltage is 150V
REGx_OUTPUT_DC_CURR_MAX = 100  # Unit: A
REGx_OUTPUT_DC_CURR_MIN = 0  # Unit: A

REGx_OUTPUT_POWER_MAX = 30000  # Unit: W

REGx_AUTOSHUTDOWN_NO_CAN_CND_TIMEOUT = 10  # Unit: s

REGx_MASTER_ADDR = 0xF0  # 0xF0~0xF8
REGx_BROADCAST_ADDR = 0x3F


class CANControllerInfo:
    AC_AB_Volt = 0
    AC1Curr = 0
    AC1Power = 0
    AC_BC_Volt = 0
    AC_CA_Volt = 0
    AC2Curr = 0
    AC2Power = 0
    DC_Output_Volt = 0
    DC_Output_Curr = 0
    DC_Output_Power = 0
    ACTotalPower = 0

    ChargerState = 0
    ChargerVolt = 0
    ChargerCurr = 0
    MaxChargerCurr = 0
    MaxChargerVolt = 0
    MaxChargePower = 0

    Temperature = 0

    # 0x01 / 0x08 系统电压电流
    SystemVolt = 0.0
    SystemCurr = 0.0
    # 0x02 模块数量
    ModuleCount = 0
    # 0x03 模块电压电流（浮点）
    ModuleVoltFloat = 0.0
    ModuleCurrFloat = 0.0
    # 0x0A 模块参数
    ParamVoltMax = 0.0
    ParamVoltMin = 0.0
    ParamCurrMax = 0.0
    ParamPower = 0.0
    # 0x0B 条码
    Barcode = ""
    # 0x0C 外部电压/允许电流
    ExternalVolt = 0.0
    AllowedCurr = 0.0


g_candevice = None
g_log_callback = None  # 由 ManualWidget 注册，签名: (direction: str, identifier: int, data: bytes, desc: str)
def REGx_Init(can_device):
    global g_candevice
    g_candevice = can_device
    return 0

def REGx_OUTPUT_DC_VOLT_IS_VALID(volt):
    return REGx_OUTPUT_DC_VOLT_MIN <= volt <= REGx_OUTPUT_DC_VOLT_MAX


def REGx_OUTPUT_DC_CURR_IS_VALID(curr):
    return REGx_OUTPUT_DC_CURR_MIN <= curr <= REGx_OUTPUT_DC_CURR_MAX


def REGx_OUTPUT_POWER_IS_VALID(power):
    return 0 <= power <= REGx_OUTPUT_POWER_MAX


class REGx_ERROR_CODE:
    NORMAL = 0
    NONE = 1
    CMD_ABNORMAL = 2
    DATA_ABNORMAL = 3
    ADDR_INVALID = 4
    LAUNCHING = 7


class REGx_DEVICE_CODE:
    SINGLE = 0x0A
    GROUP = 0x0B


class REGx_Msg_t:
    def __init__(self):
        self.errorCode = REGx_ERROR_CODE.NORMAL
        self.deviceCode = REGx_DEVICE_CODE.SINGLE
        self.cmdCode = 0
        self.dstAddr = 0
        self.srcAddr = 0
        self.data = bytearray(8)

def REGx_MsgSend(msg):
    TxData = bytearray(8)
    Identifier = 0
    Identifier |= (msg.srcAddr & 0xFF)
    Identifier |= (msg.dstAddr & 0xFF) << 8
    Identifier |= (msg.cmdCode & 0x3F) << 16
    Identifier |= (msg.deviceCode & 0x0F) << 22
    Identifier |= (msg.errorCode & 0x07) << 26
    TxData[:] = msg.data[:]
    formatted_identifier = f"({Identifier >> 24:02X} {Identifier >> 16 & 0xFF:02X} {Identifier >> 8 & 0xFF:02X} {Identifier & 0xFF:02X})"
    print(f"==> Identifier: {formatted_identifier} TxData: {TxData}")
    if g_log_callback:
        g_log_callback('TX', Identifier, bytes(TxData), "")
    return g_candevice.send_data_ch1(Identifier, TxData)


def REGx_ReadStateRequest(dstAddr):
    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x04
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR

    request.data = bytearray(8)
    REGx_MsgSend(request)

    return 0


def REGx_ReadInputRequest(dstAddr):
    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x06
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR

    request.data = bytearray(8)
    REGx_MsgSend(request)

    return 0


def REGx_ReadOutputRequest(dstAddr):
    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x09
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR

    request.data = bytearray(8)
    REGx_MsgSend(request)

    return 0



def REGx_ReadOutputSetRequest(dstAddr):
    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x0A
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR

    request.data = bytearray(8)
    REGx_MsgSend(request)

    return 0

def REGx_SetOutput(dstAddr, volt, curr):
    # Clamp voltage and current within their respective bounds
    volt = max(REGx_OUTPUT_DC_VOLT_MIN, min(volt, REGx_OUTPUT_DC_VOLT_MAX))
    curr = max(REGx_OUTPUT_DC_CURR_MIN, min(curr, REGx_OUTPUT_DC_CURR_MAX))

    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x1C
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR

    # Convert voltage and current to uint32_t representation
    voltSetValue = int(volt * 1000)
    currSetValue = int(curr * 1000)

    # Pack the data into big-endian format
    request.data[0] = (voltSetValue >> 24) & 0xFF
    request.data[1] = (voltSetValue >> 16) & 0xFF
    request.data[2] = (voltSetValue >> 8) & 0xFF
    request.data[3] = voltSetValue & 0xFF
    request.data[4] = (currSetValue >> 24) & 0xFF
    request.data[5] = (currSetValue >> 16) & 0xFF
    request.data[6] = (currSetValue >> 8) & 0xFF
    request.data[7] = currSetValue & 0xFF

    REGx_MsgSend(request)

    return 0


def REGx_Launch(dstAddr):
    request = REGx_Msg_t()

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = 0x1A
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data[0] = 0x00  # Set launch command to ON

    REGx_MsgSend(request)

    return 0

def REGx_CloseOutput(dstAddr):
    request = REGx_Msg_t()

    REGx_CMD_CODE_LAUNCH_SET_ON = 0x00
    REGx_CMD_CODE_LAUNCH_SET_OFF = 0x01
    REGx_CMD_CODE_LAUNCH_SET = 0x1A

    request.errorCode = REGx_ERROR_CODE.NORMAL
    request.deviceCode = REGx_DEVICE_CODE.SINGLE
    request.cmdCode = REGx_CMD_CODE_LAUNCH_SET
    request.dstAddr = dstAddr
    request.srcAddr = REGx_MASTER_ADDR
    request.data[0] = REGx_CMD_CODE_LAUNCH_SET_OFF

    ret = REGx_MsgSend(request)

    return 0



import time

last_request_time = 0
request_list = [lambda : REGx_ReadStateRequest(0x00),
                lambda : REGx_ReadInputRequest(0x00),
                lambda : REGx_ReadOutputRequest(0x00)]
request_idx = 0

def REGx_Poll(can_msg_list1, canController_info: CANControllerInfo):
    global last_request_time, request_idx, request_list
    if time.time() - last_request_time > 0.5:
        request_list[request_idx]()
        request_idx = (request_idx + 1) % len(request_list)
        last_request_time = time.time()

    for can_msg in can_msg_list1:
        # print(len(can_msg.data), can_msg.data)
        REGx_CAN_ReceviceCallback(can_msg, canController_info)

def REGx_CAN_ReceviceCallback(can_msg,canController_info:CANControllerInfo):

    RxData = bytearray(8)
    l_response = REGx_Msg_t()
    Identifier = can_msg.can_id
    RxData[:] = can_msg.data
    # Retrieve Rx messages from RX FIFO0
    response = l_response
    # Decode received data
    response.errorCode = (Identifier >> 26) & 0x07
    response.deviceCode = (Identifier >> 22) & 0x0F
    response.cmdCode = (Identifier >> 16) & 0x3F
    response.dstAddr = (Identifier >> 8) & 0xFF
    response.srcAddr = Identifier & 0xFF
    response.data[:] = RxData[:]

    formatted_identifier = f"({Identifier >> 24:02X} {Identifier >> 16 & 0xFF:02X} {Identifier >> 8 & 0xFF:02X} {Identifier & 0xFF:02X})"
    print(f"<== Identifier: {formatted_identifier} TxData: {RxData}")

    if g_log_callback:
        g_log_callback('RX', Identifier, bytes(RxData), "")

    if (response.dstAddr == REGx_MASTER_ADDR or response.dstAddr == REGx_BROADCAST_ADDR):
        if (response.cmdCode == 0x04):
            canController_info.Temperature = response.data[4]
        elif (response.cmdCode == 0x06):
            '''
            交流 AB
            电 压 高
            字节（单
            相 输 入
            电 压 高
            字节） 
            交流 AB
            电压低
            字 节
            （单相
            输入电
            压低字
            节） 
            交流 BC
            电压高
            字节 
            交流 BC
            电压低
            字节 
            交流 CA
            电压高
            字 节
            （直流
            输入电
            压高字
            节） 
            交流 CA
            电压低
            字 节
            （直流
            输入电
            压低字
            节） 
            0 0 

            '''
            canController_info.AC_AB_Volt = (response.data[0] << 8) | response.data[1]
            canController_info.AC_BC_Volt = (response.data[2] << 8) | response.data[3]
            canController_info.AC_CA_Volt = (response.data[4] << 8) | response.data[5]

            canController_info.AC_AB_Volt = canController_info.AC_AB_Volt * 0.1
            canController_info.AC_BC_Volt = canController_info.AC_BC_Volt * 0.1
            canController_info.AC_CA_Volt = canController_info.AC_CA_Volt * 0.1

        elif (response.cmdCode == 0x09):
            '''
            模块 N 电压（mV） 模块 N 电流（mA） 
            MSB MSB MSB MSB
            模块回复： 02 89 F0 00 00 03 0D 40 00 00 13 88——0#模块回复电压 200V，电流 5A
            '''
            canController_info.DC_Output_Volt = (response.data[0] << 24) | (response.data[1] << 16) | (response.data[2] << 8) | response.data[3]
            canController_info.DC_Output_Curr = (response.data[4] << 24) | (response.data[5] << 16) | (response.data[6] << 8) | response.data[7]

            canController_info.DC_Output_Volt = canController_info.DC_Output_Volt / 1000
            canController_info.DC_Output_Curr = canController_info.DC_Output_Curr / 1000
            canController_info.DC_Output_Power = canController_info.DC_Output_Volt * canController_info.DC_Output_Curr

            if canController_info.DC_Output_Volt > 5:
                canController_info.ChargerState = 1
            else:
                canController_info.ChargerState = 0

        else:
            pass
