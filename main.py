import sys
from config_manager import ConfigManager, AppConfig
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QStandardItemModel, QColor
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon, QTableWidgetItem, QHeaderView, QWidget
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QSplitter, QVBoxLayout
from qfluentwidgets import FluentIcon as FIF, TableWidget, Theme, setTheme, SwitchButton, AvatarWidget, BodyLabel, \
    CaptionLabel, HyperlinkButton, isDarkTheme, FluentIcon, Action
from qfluentwidgets import InfoLevel, setThemeColor
from qfluentwidgets import (NavigationItemPosition, MessageBox, FluentWindow,
                            NavigationAvatarWidget, SubtitleLabel, setFont)
from qfluentwidgets.components.material import AcrylicMenu

from BMSDataType import *
from FluentQtTest import Ui_Form
from HDL_CAN import CANDev
from REG1K0100A2 import *
from chart_widget import RealtimeChart
from manual_widget import ManualWidget




class MainWindow(QFrame, Ui_Form):
    def __init__(self, config: AppConfig = None, parent=None):
        super().__init__(parent=parent)

        self.setupUi(self)
        self._config = config or AppConfig()

        setThemeColor('#28afe9')

        # self.setTitleBar(SplitTitleBar(self))
        # self.titleBar.raise_()
        # self.windowEffect.setMicaEffect(self.winId(), isDarkMode=False)
        #
        # self.setWindowTitle('充电控制器上位机')
        # self.setWindowIcon(QIcon('./img/star.png'))

        # 添加一个退出菜单项
        exitAction = QAction(QIcon('./img/sp-exit.png'), 'Exit', self)
        exitAction.triggered.connect(self.close)

        # 创建托盘菜单
        trayMenu = QMenu(self)
        trayMenu.addAction(exitAction)

        # 创建系统托盘图标
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(QIcon('./img/star.png'))
        self.trayIcon.setContextMenu(trayMenu)
        self.trayIcon.show()

        self.can_device = CANDev()  # Create an instance of your CAN device
        self.canController_info = CANControllerInfo()

        # ── 实时曲线图：插入到"充电器状态"标题+表格的左侧 ────────
        pwr_max = self._config.voltage_max * self._config.current_max
        self.realtimeChart = RealtimeChart(
            volt_max=self._config.voltage_max,
            curr_max=self._config.current_max,
            pwr_max=pwr_max,
            parent=self,
        )
        # 把 TitleLabel_3 和 TableWidget_Charger 从 verticalLayout_2 移出，
        # 放入右侧容器，与图表一起装进水平 Splitter
        _right = QWidget(self)
        _right_vl = QVBoxLayout(_right)
        _right_vl.setContentsMargins(0, 0, 0, 0)
        _right_vl.setSpacing(4)
        _right_vl.addWidget(self.TitleLabel_3)
        _right_vl.addWidget(self.TableWidget_Charger)

        _splitter = QSplitter(Qt.Horizontal, self)
        _splitter.setChildrenCollapsible(False)
        _splitter.addWidget(self.realtimeChart)
        _splitter.addWidget(_right)
        _splitter.setSizes([480, 260])

        # verticalLayout_2 现已为空，加入 Splitter
        self.verticalLayout_2.addWidget(_splitter)

        # enable border
        self.TableWidget_Charger.setBorderVisible(True)
        self.TableWidget_Charger.setBorderRadius(8)
        self.TableWidget_Charger.setWordWrap(False)
        self.TableWidget_Charger.setColumnCount(3)
        # 禁止编辑
        self.TableWidget_Charger.setEditTriggers(TableWidget.NoEditTriggers)
        self.TableWidget_Charger.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.DoubleSpinBox_Volt.setRange(self._config.voltage_min, self._config.voltage_max)
        self.DoubleSpinBox_Volt.setValue(min(320, self._config.voltage_max))
        self.DoubleSpinBox_Curr.setRange(self._config.current_min, self._config.current_max)
        self.DoubleSpinBox_Curr.setValue(min(10, self._config.current_max))

        # Connect signals with slots
        self.ToggleButtonCAN.clicked.connect(self.toggleCAN)
        self.PushButton_SetVoltCurr.clicked.connect(self.printVoltCurrValues)
        self.PushButton_OpenDCOutput.clicked.connect(lambda: self.printChargerState(True))
        self.PushButton_CloseDCOutput.clicked.connect(lambda: self.printChargerState(False))

        REGx_Init(self.can_device)

        # Start timer for checking data
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkForData)
        self.timer.start(90)  # Check for data every second

        self.timerCANHeart = QTimer(self)
        self.timerCANHeart.timeout.connect(self.CANHeartBeat)
        self.timerCANHeart.start(1000)  # Send CAN heart beat every second

        self.timerUpdateTableWiget = QTimer(self)
        self.timerUpdateTableWiget.timeout.connect(self.updateTableWiget)
        self.timerUpdateTableWiget.start(150)  # Send CAN heart beat every second

        self.IconInfoBadge_CAN1.setLevel(InfoLevel.INFOAMTION)
        self.IconInfoBadge_CAN2.setLevel(InfoLevel.INFOAMTION)
        self.timerCheckCAN1Connection = QTimer(self)
        self.timerCheckCAN1Connection.timeout.connect(lambda: self.IconInfoBadge_CAN1.setLevel(InfoLevel.INFOAMTION))
        self.timerCheckCAN1Connection.start(500)  # Send CAN heart beat every second
        self.timerCheckCAN2Connection = QTimer(self)
        self.timerCheckCAN2Connection.timeout.connect(lambda: self.IconInfoBadge_CAN2.setLevel(InfoLevel.INFOAMTION))
        self.timerCheckCAN2Connection.start(500)

        self.currentSet = 1
        self.voltageSet = 100
        self.voltageSet = self.DoubleSpinBox_Volt.value()
        self.currentSet = self.DoubleSpinBox_Curr.value()

    def toggleCAN(self):
        if self.ToggleButtonCAN.isChecked():
            if self.can_device.open_device():
                self.ToggleButtonCAN.setText('关闭CAN')
            else:
                self.ToggleButtonCAN.setChecked(False)
        else:
            self.can_device.close_device()
            self.ToggleButtonCAN.setText('打开CAN')

    def CANHeartBeat(self):
        ...
        # self.can_device.send_data_ch1(0x1AB01103, bytes([0, 0, 0, 0, 0, 0, 0, 0]))

    def updateTableWiget(self):
        self.update_BodyLabel_Charger()
        if self.canController_info.ChargerState == 0:
            self.SwitchButton_Charger.setChecked(False)
        else:
            self.SwitchButton_Charger.setChecked(True)
        self.realtimeChart.push(
            self.canController_info.DC_Output_Volt,
            self.canController_info.DC_Output_Curr,
            self.canController_info.DC_Output_Power,
        )


    def checkForData(self):
        if self.can_device.isCanOpen:
            can_msg_list1, ret1 = self.can_device.read_ch1()
            can_msg_list2, ret2 = self.can_device.read_ch2()

            if ret1 < 0:
                self.ToggleButtonCAN.setChecked(False)
                self.toggleCAN()
            elif ret1 > 0:
                self.IconInfoBadge_CAN1.setLevel(InfoLevel.SUCCESS)
                # 重置定时器避免触发超时事件
                self.timerCheckCAN1Connection.start(500)

            if ret2 < 0:
                self.ToggleButtonCAN.setChecked(False)
                self.toggleCAN()
            elif ret2 > 0:
                self.IconInfoBadge_CAN2.setLevel(InfoLevel.SUCCESS)
                # 重置定时器避免触发超时事件
                self.timerCheckCAN2Connection.start(500)
            REGx_Poll(can_msg_list1,self.canController_info)

        # can_msg_list1 = []
        # REGx_Poll(can_msg_list1,self.canController_info)


    def printChargerState(self, checked):
        def sendCommand():
            if checked:
                print("SwitchButton_Charger is ON")
                for _ in range(3):
                    REGx_SetOutput(0x00, self.voltageSet, self.currentSet)
                    REGx_Launch(0x00)
                    time.sleep(0.02)
            else:
                print("SwitchButton_Charger is OFF")
                for _ in range(3):
                    REGx_SetOutput(0x00, self.voltageSet, self.currentSet)
                    REGx_CloseOutput(0x00)
                    time.sleep(0.02)

        self.timerUpdateTableWiget.stop()
        msg_box = MessageBox("确认执行", "是否确认发送这条命令?", self)
        msg_box.yesSignal.connect(lambda: sendCommand())
        msg_box.cancelSignal.connect(lambda: print(f"Action canceled."))
        msg_box.exec()
        self.timerUpdateTableWiget.start(150)

    def printVoltCurrValues(self):
        self.voltageSet = self.DoubleSpinBox_Volt.value()
        self.currentSet = self.DoubleSpinBox_Curr.value()
        print(f"Voltage: {self.voltageSet}, Current: {self.currentSet}")
        REGx_SetOutput(0x00, self.voltageSet, self.currentSet)

    def closeEvent(self, event):
        self.can_device.close_device()  # Close CAN device before exiting
        event.accept()

    def update_BodyLabel_Charger(self):

        ACTotalPower_static = self.canController_info.ACTotalPower - 711 if self.canController_info.ACTotalPower > 711 else 0

        tableViewData = [
            ["充电器直流输出"],
            ["直流输出电压", f"{self.canController_info.DC_Output_Volt:<10.2f}", "V"],
            ["直流输出电流", f"{self.canController_info.DC_Output_Curr:<10.2f}", "A"],
            ["直流输出功率", f"{self.canController_info.DC_Output_Power:<10.2f}", "W"],
            ["AB线电压"],
            ["电压", f"{self.canController_info.AC_AB_Volt:<10.2f}", "V"],
            # ["电流", f"{self.canController_info.AC1Curr:<10.2f}", "A"],
            # ["功率", f"{self.canController_info.AC1Power:<10.2f}", "W"],
            ["BC线电压"],
            ["电压", f"{self.canController_info.AC_BC_Volt:<10.2f}", "V"],
            ["CA线电压"],
            ["电压", f"{self.canController_info.AC_CA_Volt:<10.2f}", "V"],
            # ["电流", f"{self.canController_info.AC2Curr:<10.2f}", "A"],
            # ["功率", f"{self.canController_info.AC2Power:<10.2f}", "W"],
            # ["三相交流输入总功率"],
            # ["功率", f"{self.canController_info.ACTotalPower:<10.2f}", "W"],
            # ["三相交流输入总功率减去静态功耗"],
            # ["功率", f"{ACTotalPower_static:<10.2f}", "W"],
            # ["充电状态码", f"{self.canController_info.ChargerState}"],
            # ["设置的输出电压", f"{self.canController_info.ChargerVolt:<10.2f}", "V"],
            # ["设置的输出电流", f"{self.canController_info.ChargerCurr:<10.2f}", "A"],
            ["充电器温度", f"{self.canController_info.Temperature}", "℃"],
            # ["最大充电电流", f"{self.canController_info.MaxChargerCurr:<10.2f}", "A"],
            # ["最大充电电压", f"{self.canController_info.MaxChargerVolt:<10.2f}", "V"],
            # ["最大充电功率", f"{self.canController_info.MaxChargePower:<10.2f}", "W"]
        ]

        self.TableWidget_Charger.setRowCount(len(tableViewData))

        for i, row in enumerate(tableViewData):
            for j in range(len(row)):
                item = QTableWidgetItem(row[j])
                if len(row) == 1:
                    # 设置合并单元格
                    self.TableWidget_Charger.setSpan(i, 0, 1, 3)
                    # item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(QFont("Arial", 10, QFont.Bold))
                else:
                    item.setFont(QFont("Arial", 10, QFont.Normal))

                self.TableWidget_Charger.setItem(i, j, item)

        self.TableWidget_Charger.verticalHeader().hide()
        self.TableWidget_Charger.setHorizontalHeaderLabels(['属性', '值', '单位'])
        # 设置自适应父容器宽度
        self.TableWidget_Charger.resizeColumnsToContents()
        self.TableWidget_Charger.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))


class SettingWidget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        # self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)
        self.switchButton = SwitchButton(self)
        self.switchButton.setOnText('Dark')
        self.switchButton.setOffText('Light')

        self.switchButton.checkedChanged.connect(
            lambda: setTheme(Theme.DARK if self.switchButton.isChecked() else Theme.LIGHT))

        setFont(self.switchButton, 24)
        # self.switchButton.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.switchButton, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))


class ProfileCard(QWidget):
    """ Profile card """

    def __init__(self, avatarPath: str, name: str, email: str, parent=None):
        super().__init__(parent=parent)
        self.avatar = AvatarWidget(avatarPath, self)
        self.nameLabel = BodyLabel(name, self)
        self.emailLabel = CaptionLabel(email, self)
        self.logoutButton = HyperlinkButton(
            'https://github.com/MisakaMikoto128', '注销', self)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)
        self.emailLabel.setStyleSheet('QLabel{color: ' + color.name() + '}')

        color = QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0)
        self.nameLabel.setStyleSheet('QLabel{color: ' + color.name() + '}')
        setFont(self.logoutButton, 13)

        self.setFixedSize(307, 82)
        self.avatar.setRadius(24)
        self.avatar.move(2, 6)
        self.nameLabel.move(64, 13)
        self.emailLabel.move(64, 32)
        self.logoutButton.move(52, 48)


class Window(FluentWindow):

    def __init__(self):
        super().__init__()

        self._config = ConfigManager().load()

        # create sub interface
        self.homeInterface = MainWindow(config=self._config, parent=self)
        self.manualInterface = ManualWidget(
            can_device=self.homeInterface.can_device,
            canController_info=self.homeInterface.canController_info,
            config=self._config,
            parent=self,
        )
        # self.musicInterface = Widget('Music Interface', self)
        # self.videoInterface = Widget('Video Interface', self)
        # self.folderInterface = Widget('Folder Interface', self)
        self.settingInterface = SettingWidget('Setting Interface', self)
        # self.albumInterface = Widget('Album Interface', self)
        # self.albumInterface1 = Widget('Album Interface 1', self)
        # self.albumInterface2 = Widget('Album Interface 2', self)
        # self.albumInterface1_1 = Widget('Album Interface 1-1', self)
        # 最大化
        self.setWindowState(Qt.WindowMaximized)
        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主页')
        self.addSubInterface(self.manualInterface, FIF.EDIT, '手动操作')
        # self.addSubInterface(self.musicInterface, FIF.MUSIC, 'Music library')
        # self.addSubInterface(self.videoInterface, FIF.VIDEO, 'Video library')

        # Theme切换按钮

        self.navigationInterface.addSeparator()

        # self.addSubInterface(self.albumInterface, FIF.ALBUM, 'Albums', NavigationItemPosition.SCROLL)
        # self.addSubInterface(self.albumInterface1, FIF.ALBUM, 'Album 1', parent=self.albumInterface)
        # self.addSubInterface(self.albumInterface1_1, FIF.ALBUM, 'Album 1.1', parent=self.albumInterface1)
        # self.addSubInterface(self.albumInterface2, FIF.ALBUM, 'Album 2', parent=self.albumInterface)
        # self.addSubInterface(self.folderInterface, FIF.FOLDER, 'Folder library', NavigationItemPosition.SCROLL)

        # add custom widget to bottom
        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=NavigationAvatarWidget('Yuanlin-Liu', 'resource/shoko.png'),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM,
        )

        self.addSubInterface(self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        # add badge to navigation item
        # item = self.navigationInterface.widget(self.videoInterface.objectName())
        # InfoBadge.attension(
        #     text=9,
        #     parent=item.parent(),
        #     target=item,
        #     position=InfoBadgePosition.NAVIGATION_ITEM
        # )

        # NOTE: enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

    def initWindow(self):
        self.resize(900, 700)
        # self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        # self.setWindowTitle('PyQt-Fluent-Widgets')

        self.setWindowTitle(self._config.device_name)
        self.setWindowIcon(QIcon('./img/star.png'))

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        # set the minimum window width that allows the navigation panel to be expanded
        # self.navigationInterface.setMinimumExpandWidth(900)
        # self.navigationInterface.expand(useAni=False)

    def showMessageBox(self):

        self.homeInterface.timerUpdateTableWiget.stop()

        w = MessageBox(
            '支持作者',
            '🥤🥤🚀',
            self
        )
        w.yesButton.setText('🥤')
        w.cancelButton.setText('🚀')
        w.exec()
        self.homeInterface.timerUpdateTableWiget.start(150)

    def contextMenuEvent(self, e) -> None:
        menu = AcrylicMenu(parent=self)

        # add custom widget
        card = ProfileCard('resource/shoko.png', '刘沅林', 'liuyuanlins@outlook.com', menu)
        menu.addWidget(card, selectable=False)
        # menu.addWidget(card, selectable=True, onClick=lambda: print('666'))

        menu.addSeparator()
        menu.addActions([
            Action(FluentIcon.PEOPLE, '管理账户和设置'),
            Action(FluentIcon.SHOPPING_CART, '支付方式'),
            Action(FluentIcon.CODE, '兑换代码和礼品卡'),
        ])
        menu.addSeparator()
        menu.addAction(Action(FluentIcon.SETTING, '设置'))
        menu.exec(e.globalPos())


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # setTheme(Theme.DARK)

    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()
