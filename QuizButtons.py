import time
import qrc_resources
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QIODevice, QRect
from PyQt5.QtGui import (QStandardItemModel, QStandardItem, QIntValidator,
                         QPainter, QPen, QColor, QBrush, QIcon)
from PyQt5.QtWidgets import (QApplication, QTableView, QWidget, QGridLayout,
                             QHBoxLayout, QPushButton, QComboBox, QMessageBox,
                             QMenu, QHeaderView, QStyledItemDelegate, QAction,
                             QLineEdit, QMainWindow, QStatusBar, QGroupBox,
                             QDialog, QLabel)


class TableViewDelegate(QStyledItemDelegate):
    """
    Delegate for first column
    """

    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)
        self.parent = parent

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setValidator(QIntValidator(1, 100))
        return editor


class ComboBox(QComboBox):
    popupActivate = QtCore.pyqtSignal()

    def showPopup(self):
        self.popupActivate.emit()
        super().showPopup()


class ToggleSwitch(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setMinimumWidth(66)
        self.setMinimumHeight(22)

    def paintEvent(self, event):
        label = "ON" if self.isChecked() else "OFF"
        bg_color = QColor(154, 205, 50) if self.isChecked() else QColor(205, 92, 92)

        radius = 10
        width = 32
        center = self.rect().center()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(center)
        painter.setBrush(bg_color)

        pen = QPen(QColor(152, 152, 152))
        pen.setWidth(1)
        painter.setPen(pen)

        painter.drawRoundedRect(QRect(-width, -radius, 2 * width, 2 * radius), radius, radius)
        painter.setBrush(QColor(240, 240, 240))
        sw_rect = QRect(-radius, -radius, width + radius, 2 * radius)
        if not self.isChecked():
            sw_rect.moveLeft(-width)
        painter.drawRoundedRect(sw_rect, radius, radius)
        painter.setPen(QColor(Qt.black))
        painter.drawText(sw_rect, Qt.AlignCenter, label)


class CentralWidget(QWidget):
    status_COM_signal = QtCore.pyqtSignal(str)
    buttonNumberChanged = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        # -------CONSTATNS----------
        self.PING = b'\xFF\xFF'
        self.ACTIVITY = b'\xFF\x01'
        self.NOT_ACTIVITY = b'\xFF\x02'
        self.CHANGE_BUTTON_NUM = b'\xF0'
        # --------------------------
        self.view = QTableView()
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.tableContextMenuEvent)

        self.btnConnect = QPushButton('Соединить')
        self.btnConnect.clicked.connect(self.connect_COM)
        self.box_COM = ComboBox()
        self.box_COM.setMinimumContentsLength(25)
        self.box_COM.popupActivate.connect(self.updateList_COM)

        self.serial = QSerialPort()
        self.serial.setBaudRate(9600)
        self.serial.readyRead.connect(self.read_COM)
        
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Номер кнопки', 'Название команды'])
        self.maxNumber = 0
        self.model.itemChanged.connect(self.changeMaxNum)

        self.view.setModel(self.model)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.view.horizontalHeader().setMinimumSectionSize(140)
        self.view.horizontalHeader().setSortIndicatorShown(True)
        self.view.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegateForColumn(0, TableViewDelegate(self.view))
        
        self.on_off_switch = ToggleSwitch()
        self.on_off_switch.setChecked(True)
        self.on_off_switch.clicked.connect(self.changeActivationGameButton)

        groupBox1 = QGroupBox("Активация кнопок")
        hBoxLeft = QHBoxLayout()
        hBoxLeft.addWidget(self.on_off_switch)
        groupBox1.setLayout(hBoxLeft)
        groupBox1.setMaximumWidth(126)

        groupBox2 = QGroupBox("COM порт")
        hBoxRight = QHBoxLayout()
        hBoxRight.addWidget(self.box_COM)
        hBoxRight.addWidget(self.btnConnect)
        groupBox2.setLayout(hBoxRight)

        grid = QGridLayout(self)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.addWidget(self.view, 0, 0, 1, 4)
        grid.addWidget(groupBox1, 4, 0, 1, 1)
        grid.addWidget(groupBox2, 4, 3, 1, 1)

    def changeNumberButton(self, number):
        self.sendCommand_COM(self.CHANGE_BUTTON_NUM, data=number)

    def changeActivationGameButton(self):
        if self.on_off_switch.isChecked():
            self.sendCommand_COM(self.ACTIVITY)
        else:
            self.sendCommand_COM(self.NOT_ACTIVITY)

    def getStatus_COM(self):
        error = self.serial.error()
        if error == QSerialPort.OpenError:
            self.status_COM_signal.emit("Устройство уже подключено")
        elif error == QSerialPort.DeviceNotFoundError:
            self.status_COM_signal.emit("Устройство не найдено")
        elif error == QSerialPort.PermissionError:
            self.status_COM_signal.emit("Устройство занято другим приложением")
        else:
            self.status_COM_signal.emit("Код ошибки: {0}".format(str(error)))
        self.serial.clearError()

    def sendCommand_COM(self, command, data=0xFF):
        if self.serial.isOpen():
            sendData = command
            if command == self.CHANGE_BUTTON_NUM:
                sendData += data.to_bytes(1, byteorder='big')
            if self.serial.write(sendData) == -1:
                self.getStatus_COM()
            elif command == self.CHANGE_BUTTON_NUM:
                self.status_COM_signal.emit("Значение отправлено, нажмите на соотвествующую игровую кнопку")

            print("Отправлено: {0}".format(sendData))
        else:
            self.status_COM_signal.emit("Нет подключения к устройству")
            print("Не открыт COM порт")

    def read_COM(self):
        rx = self.serial.readLine()
        print("Принято: {0}".format(rx))
        if rx.count() != 2:
            return
        else:
            data = [int.from_bytes(rx[0], byteorder='big'), int.from_bytes(rx[1], byteorder='big')]
        if data[0] == 1:
            self.on_off_switch.setChecked(False)
            findList = self.model.findItems(str(data[1]))
            if len(findList):
                # Если найдено совпадение
                findCell = findList[0]
                if self.model.item(findCell.row(), 1):
                    # Если для кнопки определено название комады
                    QMessageBox.information(self, "Информация", 'Отвечает команда: "{0}"'.format(self.model.item(findCell.row(), 1).text()))
                    self.sendCommand_COM(self.ACTIVITY)
                    self.on_off_switch.setChecked(True)
                    return
            else:
                # Если в списке нет этой кнопки добавим её
                self.addRow(data[1])
            QMessageBox.information(self, "Информация", "Нажата кнопка №{0}".format(data[1]))
            self.sendCommand_COM(self.ACTIVITY)
            self.on_off_switch.setChecked(True)
        elif data[0] == 3:
            self.buttonNumberChanged.emit()
            self.status_COM_signal.emit("Номер игровой кнопки успешно изменен")

    def connect_COM(self):
        # берем только название самого порта без дескрипшена
        self.serial.setPortName(self.box_COM.currentText().partition(' - ')[0])
        if self.serial.open(QIODevice.ReadWrite):
            self.status_COM_signal.emit("Соединение успешно")
            time.sleep(2)
            self.sendCommand_COM(self.PING)
        else:
            self.getStatus_COM()

    def updateList_COM(self):
        portList = []
        ports = QSerialPortInfo().availablePorts()
        for port in ports:
            portList.append("{0} - {1}".format(port.portName(), port.description()))
        portList.sort()
        self.box_COM.clear()
        self.box_COM.addItems(portList)

    def addRow(self, number):
        row = self.model.rowCount()
        self.model.insertRow(row, QStandardItem(str(number)))

    def tableContextMenuEvent(self, pos):
        mnu = QMenu()
        mnu.addAction('Добавить').setObjectName('add')
        mnu.addAction('Удалить').setObjectName('del')
        ret = mnu.exec_(self.view.mapToGlobal(pos))
        if not ret:
            return
        obj = ret.objectName()
        if obj == 'add':
            self.addRow(self.maxNumber + 1)
        elif obj == 'del':
            idx = self.view.currentIndex()
            self.model.removeRow(idx.row())
        self.view.setCurrentIndex(self.model.index(-1, -1))

    def changeMaxNum(self, item):
        if (item.column() != 0):
            return
        itemNum = int(item.text())
        if (self.maxNumber < itemNum):
            self.maxNumber = itemNum


class SettingsDialog(QDialog):
    numberButton_signal = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.numberButtonLineEdit = QLineEdit(self)
        self.numberButtonLineEdit.setValidator(QIntValidator(1, 100))
        self.numberButtonLineEdit.setMaximumWidth(30)
        numberButtonLabel = QLabel("Новый номер для кнопки: ")
        numberButtonLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.numberButtonSend = QPushButton("Отправить")
        self.numberButtonSend.clicked.connect(self.numberButtonWantChanged)

        groupBox = QGroupBox("Изменение номера кнопки")
        groupBox.setMaximumHeight(100)
        hBox = QHBoxLayout()
        hBox.addStretch()
        hBox.addWidget(self.numberButtonSend)
        grid = QGridLayout()
        grid.setContentsMargins(5, 5, 5, 5)
        grid.addWidget(numberButtonLabel, 0, 1, 1, 1)
        grid.addWidget(self.numberButtonLineEdit, 0, 2, 1, 1)
        grid.addLayout(hBox, 1, 1, 1, 2)
        groupBox.setLayout(grid)

        mainGrid = QGridLayout(self)
        mainGrid.setContentsMargins(10, 10, 10, 10)
        mainGrid.addWidget(groupBox, 0, 0, 1, 1)
        mainGrid.setRowStretch(1, 1)

    def numberButtonWantChanged(self):
        if self.numberButtonLineEdit.isModified():
            self.numberButton_signal.emit(int(self.numberButtonLineEdit.text()))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget(CentralWidget())

        self.settingsAction = QAction("Настройки", self)
        self.menuBar().addAction(self.settingsAction)
        self.settingsAction.triggered.connect(self.settings)

        self.centralWidget().status_COM_signal.connect(self.show_COM_status)
        self.statusBar()

    def show_COM_status(self, message):
        self.statusBar().showMessage(message, msecs=3000)

    def settings(self):
        dialog = SettingsDialog(self)
        dialog.setWindowTitle("Настройки")
        dialog.setMinimumWidth(100)
        dialog.setFixedSize(300, 150)
        dialog.numberButton_signal.connect(self.centralWidget().changeNumberButton)
        self.centralWidget().buttonNumberChanged.connect(dialog.close)
        dialog.exec()
        # На выходе восстанавливаем активность настроенную ранее
        self.centralWidget().changeActivationGameButton()

    def closeEvent(self, event):
        self.centralWidget().serial.close()
        event.accept()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(":main-icon.ico"))
    window = MainWindow()
    window.setWindowTitle("Управление кнопками")
    window.setMinimumWidth(500)
    window.resize(600, 300)
    window.show()
    sys.exit(app.exec_())
