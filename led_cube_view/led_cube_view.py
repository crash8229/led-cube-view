import json
from math import tan, radians
from pathlib import Path
from types import MappingProxyType
from typing import Union, Tuple, Optional, Sequence

import numpy as np
import pyqtgraph.opengl as gl  # type: ignore
from pyqtgraph import Vector
from stl import mesh


# Globals ##############################################################################################################
RESOURCE_PATH = Path(__file__).resolve().parent

config_list = list(RESOURCE_PATH.joinpath("config").glob("*_cube.json"))
config_list.sort(key=lambda x: int(x.name.split("x")[0]))
CUBE_CONFIGS = MappingProxyType(
    {config.name.split("_")[0]: config for config in config_list}
)


# Helper Functions #####################################################################################################
def rgba_to_rgbaf(
    rgba: Tuple[int, int, int, float]
) -> Tuple[float, float, float, float]:
    return rgba[0] / 255, rgba[1] / 255, rgba[2] / 255, rgba[3]


# Classes ##############################################################################################################
class NoCubeLoaded(Exception):
    pass


class LED(gl.GLMeshItem):
    on_color: Tuple[float, float, float, float] = (1, 1, 1, 1)
    off_color: Tuple[float, float, float, float] = (0, 0, 0, 0)
    off_visible: bool = True

    def __init__(self, **kwargs):
        # Set default values
        defaults = {
            "smooth": True,
            "drawFaces": True,
            "color": LED.off_color,
            "edgeColor": rgba_to_rgbaf((75, 75, 75, 1)),
            "drawEdges": True,
        }
        defaults.update(kwargs)

        super().__init__(**defaults)
        self.__is_on: bool = False

    @property
    def is_on(self) -> bool:
        return self.__is_on

    def set_state(self, state: bool) -> None:
        self.setColor(LED.on_color) if state else self.setColor(LED.off_color)
        self.setVisible(True)
        None if state or LED.off_visible else self.setVisible(False)
        self.__is_on = state


# The LED cube is stored as z, x, y, where z is treated as the layer number
class LEDCubeView(gl.GLViewWidget):
    def __init__(
        self, parent=None, device_pixel_ratio=None, rotation_method="euler"
    ) -> None:
        super().__init__(
            parent=parent,
            devicePixelRatio=device_pixel_ratio,
            rotationMethod=rotation_method,
        )

        a = gl.GLAxisItem()
        a.setSize(3, 3, 3)
        self.addItem(a)

        self.__led_cube: Optional[Tuple[Tuple[Tuple[LED, ...], ...], ...]] = None
        self.__dimensions: Optional[Tuple[int, int, int]] = None

        self.__default_camera_elevation: Union[int, float] = 30
        self.__default_camera_azimuth: Union[int, float] = -135
        self.__default_camera_pos = None
        self.__default_camera_distance = None

        # Load LED mesh
        m = mesh.Mesh.from_file(str(RESOURCE_PATH.joinpath("led.stl")))
        points = m.points.reshape(-1, 3)
        faces = np.arange(points.shape[0]).reshape(-1, 3)
        self.__led_mesh_data = gl.MeshData(vertexes=points, faces=faces)

        self.set_default_camera_position()

    # Properties
    @property
    def default_camera_azimuth(self) -> Union[int, float]:
        return self.__default_camera_azimuth

    @default_camera_azimuth.setter
    def default_camera_azimuth(self, value: Union[int, float]) -> None:
        self.__default_camera_azimuth = value

    @property
    def default_camera_elevation(self) -> Union[int, float]:
        return self.__default_camera_elevation

    @default_camera_elevation.setter
    def default_camera_elevation(self, value: Union[int, float]) -> None:
        self.__default_camera_elevation = value

    @property
    def dimensions(self) -> Optional[Tuple[int, int, int]]:
        return self.__dimensions

    @property
    def on_color(self) -> Tuple[float, float, float, float]:
        return LED.on_color

    @property
    def off_color(self) -> Tuple[float, float, float, float]:
        return LED.off_color

    @property
    def off_led_visible(self) -> bool:
        return LED.off_visible

    @off_led_visible.setter
    def off_led_visible(self, visible: bool) -> None:
        if LED.off_visible == visible:
            return

        LED.off_visible = visible

        if self.__led_cube is None:
            return

        # Cycle through cube applying the new setting
        for z in self.__led_cube:
            for x in z:
                for led in x:
                    None if led.is_on else led.setVisible(visible)

    @property
    def state_matrix(self) -> Tuple[Tuple[Tuple[bool, ...], ...], ...]:
        if self.__led_cube is None:
            raise NoCubeLoaded

        matrix = list()
        for z in self.__led_cube:
            layer = list()
            for x in z:
                axis = list()
                for led in x:
                    axis.append(led.is_on)
                layer.append(tuple(axis))
            matrix.append(tuple(layer))
        return tuple(matrix)

    # Methods
    def set_default_camera_position(self) -> None:
        self.setCameraPosition(
            pos=self.__default_camera_pos,
            distance=self.__default_camera_distance,
            azimuth=self.__default_camera_azimuth,
            elevation=self.__default_camera_elevation,
        )

    def show_cube(self) -> None:
        if self.__led_cube is not None:
            for z in self.__led_cube:
                for x in z:
                    for led in x:
                        led.setVisible(True)

    def hide_cube(self):
        if self.__led_cube is not None:
            for z in self.__led_cube:
                for x in z:
                    for led in x:
                        led.setVisible(False)

    def show_layer(self, layer: int) -> None:
        self.hide_cube()
        if self.__led_cube is not None:
            for x_slice in self.__led_cube[layer]:
                for led in x_slice:
                    led.setVisible(True)

    def set_led(self, x: int, y: int, z: int, state: bool) -> None:
        if self.__led_cube is not None:
            self.__led_cube[z][x][y].set_state(state)

    def set_layer(self, layer: int, states: Sequence[Sequence[bool]]) -> None:
        if self.__led_cube is not None:
            for x_idx in range(len(states)):
                for y_idx in range(len(states[x_idx])):
                    self.set_led(x_idx, y_idx, layer, states[x_idx][y_idx])

    def save_frame(self, filename: str) -> None:
        if not self.grabFramebuffer().save(filename):
            raise IOError(f"Could not save frame: {filename}")

    def destroy_cube(self) -> None:
        if self.__led_cube is not None:
            for z in self.__led_cube:
                for x in z:
                    for led in x:
                        self.removeItem(led)
        self.__led_cube = None
        self.__dimensions = None

    @staticmethod
    def __json_dimension_check(value: Sequence) -> Tuple[int, int, int]:
        if isinstance(value, Sequence) and len(value) == 3 and all([isinstance(dim, int) for dim in value]):
            return tuple(value)  # type: ignore
        raise ValueError("Dimension value type is not Tuple[int, int, int]")

    @staticmethod
    def __json_color_check(value: Sequence) -> Tuple[float, float, float, float]:
        if isinstance(value, Sequence) and len(value) == 4 and all([isinstance(v, (float, int)) for v in value]):
            return tuple([float(v) for v in value])  # type: ignore
        raise ValueError("Color value type is not Tuple[float, float, float, float]")

    def load_cube(self, config: Union[str, Path, dict]) -> None:

        if isinstance(config, (str, Path)):
            config = Path(config)
            if not config.is_file():
                config = str(config)
                if str(config) in CUBE_CONFIGS:
                    config = CUBE_CONFIGS[config]
                else:
                    raise FileExistsError(f"Could not find the config file: {config}")
            with open(config, "r") as f:
                led_config = json.load(f)
        else:
            led_config = config

        axis_spacing = 0
        led_spacing = 5

        self.destroy_cube()
        self.__dimensions = self.__json_dimension_check(led_config["dimension"])
        LED.off_color = self.__json_color_check(led_config["off_color"])
        LED.on_color = self.__json_color_check(led_config["on_color"])

        x_scalar = led_spacing
        x_offset = axis_spacing
        y_scalar = led_spacing
        y_offset = axis_spacing
        z_scalar = led_spacing
        z_offset = 0
        new_cube = list()
        for z in range(self.__dimensions[2]):
            new_layer = list()
            for x in range(self.__dimensions[0]):
                new_axis = list()
                for y in range(self.__dimensions[1]):
                    led = LED(meshdata=self.__led_mesh_data)
                    led.translate(
                        x_scalar * x + x_offset,
                        y_scalar * y + y_offset,
                        z_scalar * z + z_offset,
                    )
                    self.addItem(led)
                    new_axis.append(led)
                new_layer.append(tuple(new_axis))
            new_cube.append(tuple(new_layer))
        self.__led_cube = tuple(new_cube)

        self.__default_camera_distance = (
            (
                (self.__dimensions[0] * led_spacing + axis_spacing) ** 2
                + (self.__dimensions[2] * led_spacing) ** 2
            )
            ** 0.5
            / 2
        ) / tan(radians(30))

        xy_hypo = (
            (led_spacing * (self.__dimensions[0] - 1)) ** 2
            + (led_spacing * (self.__dimensions[1] - 1)) ** 2
        ) ** 0.5
        z_elevation_offset = xy_hypo * tan(radians(self.__default_camera_elevation))
        z_elevation_offset = z_elevation_offset / 2
        self.__default_camera_pos = Vector(
            0, 0, led_spacing * (self.__dimensions[2] - 1) / 2 + z_elevation_offset
        )

        self.set_default_camera_position()
