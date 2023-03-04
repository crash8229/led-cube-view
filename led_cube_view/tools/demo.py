from led_cube_view import LEDCubeView
from led_cube_view.led_cube_view import CUBE_CONFIGS

from math import ceil
from time import sleep
from threading import Thread

from pathlib import Path
from qtpy.QtWidgets import *
from qtpy.QtCore import Signal


# Demo #################################################################################################################
class Demo(QMainWindow):
    all_leds: Signal = Signal(bool, name="all_leds")
    cube_visible: Signal = Signal(bool, name="cube_visible")
    show_layer: Signal = Signal(int, name="show_layer")
    hourglass: Signal = Signal(name="hourglass")
    save_frame: Signal = Signal(str, name="save_frame")
    off_visible: Signal = Signal(bool, name="off_visible")
    __menu_enable: Signal = Signal(bool, name="menu_enable")
    set_led: Signal = Signal(int, int, int, bool, name="set_led")

    def __init__(self):
        super(Demo, self).__init__(parent=None)
        self.setWindowTitle("LED Cube Viewer")
        self.setGeometry(0, 0, 500, 500)

        center_widget = QWidget(self)
        layout = QVBoxLayout()
        center_widget.setLayout(layout)
        self.setCentralWidget(center_widget)
        self.__cube = LEDCubeView(parent=center_widget)
        self.__cube.load_cube(Path("5x5x5"))
        self.__cube.show_cube()
        layout.addWidget(self.__cube)

        load_menu = QComboBox(self)
        for config in CUBE_CONFIGS.keys():
            load_menu.addItem(config)
        load_menu.currentTextChanged.connect(self.__cube.load_cube)
        self.__menu_enable.connect(load_menu.setEnabled)
        layout.addWidget(load_menu)

        demo_button = QPushButton("Demo", center_widget)
        demo_button.clicked.connect(self.demo)
        layout.addWidget(demo_button)

        self.all_leds.connect(self.__all_leds)
        self.cube_visible.connect(self.__cube_visible)
        self.show_layer.connect(self.__cube_layer)
        self.hourglass.connect(self.__hourglass)
        self.save_frame.connect(self.__save_frame)
        self.off_visible.connect(self.__off_visible)
        self.set_led.connect(self.__cube.set_led)

        self.__demo_thread = None

        load_menu.setCurrentText("5x5x5")

    def __all_leds(self, state: bool) -> None:
        dimensions = self.__cube.dimensions
        if dimensions is not None:
            for z in range(dimensions[2]):
                for x in range(dimensions[0]):
                    for y in range(dimensions[1]):
                        self.__cube.set_led(x, y, z, state)

    def __cube_visible(self, state: bool) -> None:
        self.__cube.show_cube() if state else self.__cube.hide_cube()

    def __cube_layer(self, layer: int) -> None:
        self.__cube.show_layer(layer)

    def __hourglass(self) -> None:
        states: list = list()
        x_dim = self.__cube.dimensions[0]
        y_dim = self.__cube.dimensions[1]
        z_dim = self.__cube.dimensions[2]
        for layer in range(ceil(z_dim / 2)):
            states.append(list())
            for x in range(layer):
                states[layer].append([False] * y_dim)
            for x in range(layer, x_dim - layer, 1):
                states[layer].append([False] * y_dim)
                for y in range(layer, y_dim - layer, 1):
                    states[layer][x][y] = True
            for x in range(layer):
                states[layer].append([False] * y_dim)

        mirrored = list()
        for layer in range(
            len(states) - 1 if z_dim % 2 == 0 else len(states) - 2, -1, -1
        ):
            mirrored.append(states[layer])
        states.extend(mirrored)

        for z in range(len(states)):
            self.__cube.set_layer(z, states[z])

    def __save_frame(self, name: str) -> None:
        self.__cube.save_frame(name)  # Save the current view as an image

    def __off_visible(self, visible: bool) -> None:
        self.__cube.off_led_visible = visible

    def __demo(self) -> None:
        if self.__cube.dimensions is None:
            return

        self.__menu_enable.emit(False)

        self.cube_visible.emit(False)
        sleep(1)
        self.cube_visible.emit(True)
        sleep(1)
        self.all_leds.emit(True)
        sleep(1)
        self.all_leds.emit(False)
        sleep(1)

        self.all_leds.emit(True)
        for z in range(self.__cube.dimensions[2] - 1):
            self.show_layer.emit(z)
            sleep(0.1)

        for z in range(self.__cube.dimensions[2] - 1, -1, -1):
            self.show_layer.emit(z)
            sleep(0.1)
        self.all_leds.emit(False)
        self.cube_visible.emit(True)

        self.hourglass.emit()
        sleep(1)
        self.off_visible.emit(False)
        sleep(1)

        self.off_visible.emit(True)
        sleep(1)

        self.all_leds.emit(False)
        sleep(1)

        self.__menu_enable.emit(True)
        self.__demo_thread = None

    def demo(self) -> None:
        if self.__demo_thread is None:
            self.__demo_thread = Thread(target=self.__demo, name="Demo", daemon=True)
            self.__demo_thread.start()


if __name__ == "__main__":
    app = QApplication()
    window = Demo()
    window.show()
    app.exec()
