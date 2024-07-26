# MIT License
#
# Copyright (c) 2022 Ignacio Vizzo, Tiziano Guadagnino, Benedikt Mersch, Cyrill
# Stachniss.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import copy
import importlib
import os
from abc import ABC
from functools import partial
from typing import Callable, List

import numpy as np

CYAN = np.array([0.24, 0.898, 1])
RED = np.array([128, 0, 0]) / 255.0
BLACK = np.array([0, 0, 0]) / 255.0
BLUE = np.array([0.4, 0.5, 0.9])
GRAY = np.array([0.4, 0.4, 0.4])
SPHERE_SIZE = 0.20

BACKGROUND_COLOR = [0.0, 0.0, 0.0]
FRAME_COLOR = [0.1412, 0.4823, 0.6274]
KEYPOINTS_COLOR = [0.8470, 0.0667, 0.3490]
LOCAL_MAP_COLOR = [0.7647, 0.6981, 0.6000]
TRAJECTORY_COLOR = [0.9647, 0.9372, 0.6509]


class StubVisualizer(ABC):
    def __init__(self):
        pass

    def update(self, source, keypoints, target_map, pose):
        pass


class Kissualizer(StubVisualizer):
    # Static GUI Parameters
    polyscope = None
    background_color = BACKGROUND_COLOR
    block_execution = True
    play_mode = False
    toggle_frame = True
    toggle_keypoints = True
    toggle_map = True
    global_view = False
    trajectory = []
    last_pose = np.eye(4)

    # Public Interface ----------------------------------------------------------------------------
    def __init__(self):
        try:
            Kissualizer.polyscope = importlib.import_module("polyscope")
        except ModuleNotFoundError as err:
            print(f'polyscope is not installed on your system, run "pip install polyscope"')
            exit(1)

        # Initialize Visualizer
        Kissualizer.polyscope.set_program_name("KissICP Visualizer")
        Kissualizer.polyscope.init()
        self._initialize_visualizer()

    def update(self, source, keypoints, target_map, pose):
        frame_cloud = Kissualizer.polyscope.register_point_cloud(
            "current_frame",
            source,
            color=FRAME_COLOR,
            point_render_mode="quad",
        )
        frame_cloud.set_radius(0.2, relative=False)
        if Kissualizer.global_view:
            frame_cloud.set_transform(pose)
        else:
            frame_cloud.set_transform(np.eye(4))
        frame_cloud.set_enabled(Kissualizer.toggle_frame)
        keypoints_cloud = Kissualizer.polyscope.register_point_cloud(
            "keypoints", keypoints, color=KEYPOINTS_COLOR, point_render_mode="quad"
        )
        keypoints_cloud.set_radius(0.3, relative=False)
        if Kissualizer.global_view:
            keypoints_cloud.set_transform(pose)
        else:
            keypoints_cloud.set_transform(np.eye(4))
        keypoints_cloud.set_enabled(Kissualizer.toggle_keypoints)
        map_cloud = Kissualizer.polyscope.register_point_cloud(
            "local_map",
            target_map.point_cloud(),
            color=LOCAL_MAP_COLOR,
            point_render_mode="quad",
        )
        map_cloud.set_radius(0.1, relative=False)
        if Kissualizer.global_view:
            map_cloud.set_transform(np.eye(4))
        else:
            map_cloud.set_transform(np.linalg.inv(pose))
        map_cloud.set_enabled(Kissualizer.toggle_map)

        Kissualizer.trajectory.append(pose[:3, 3])
        if Kissualizer.global_view:
            trajectory_cloud = Kissualizer.polyscope.register_point_cloud(
                "trajectory",
                np.asarray(Kissualizer.trajectory),
                color=TRAJECTORY_COLOR,
                point_render_mode="sphere",
            )
        else:
            trajectory_cloud = Kissualizer.polyscope.register_point_cloud(
                "trajectory",
                np.asarray([[0, 0, 0]]),
                color=TRAJECTORY_COLOR,
                point_render_mode="sphere",
            )
        trajectory_cloud.set_radius(0.5, relative=False)

        Kissualizer.last_pose = pose

        # Visualization loop
        self._update_visualizer()

    # Private Interface ---------------------------------------------------------------------------
    def _initialize_visualizer(self):
        Kissualizer.polyscope.set_ground_plane_mode("none")
        Kissualizer.polyscope.set_background_color(BACKGROUND_COLOR)
        Kissualizer.polyscope.set_user_callback(Kissualizer._gui_callback)
        Kissualizer.polyscope.set_build_gui(False)

    def _update_visualizer(self):
        while Kissualizer.block_execution:
            Kissualizer.polyscope.frame_tick()
            if Kissualizer.play_mode:
                break
        Kissualizer.block_execution = not Kissualizer.block_execution

    @staticmethod
    def _gui_callback():
        # START/PAUSE
        if Kissualizer.polyscope.imgui.Button("START/PAUSE"):
            Kissualizer.play_mode = not Kissualizer.play_mode

        # NEXT FRAME
        if not Kissualizer.play_mode:
            Kissualizer.polyscope.imgui.SameLine()
            if Kissualizer.polyscope.imgui.Button("NEXT FRAME"):
                Kissualizer.block_execution = not Kissualizer.block_execution

        # CENTER VIEWPOINT
        Kissualizer.polyscope.imgui.SameLine()
        if Kissualizer.polyscope.imgui.Button("CENTER VIEWPOINT"):
            Kissualizer.polyscope.reset_camera_to_home_view()

        # TOGGLE BUTTONS
        changed, Kissualizer.toggle_frame = Kissualizer.polyscope.imgui.Checkbox(
            "Frame Cloud", Kissualizer.toggle_frame
        )
        if changed:
            Kissualizer.polyscope.get_point_cloud("current_frame").set_enabled(
                Kissualizer.toggle_frame
            )
        changed, Kissualizer.toggle_keypoints = Kissualizer.polyscope.imgui.Checkbox(
            "Keypoints", Kissualizer.toggle_keypoints
        )
        if changed:
            Kissualizer.polyscope.get_point_cloud("keypoints").set_enabled(
                Kissualizer.toggle_keypoints
            )
        changed, Kissualizer.toggle_map = Kissualizer.polyscope.imgui.Checkbox(
            "Local Map", Kissualizer.toggle_map
        )
        if changed:
            Kissualizer.polyscope.get_point_cloud("local_map").set_enabled(Kissualizer.toggle_map)

        # BACKGROUND COLOR
        changed, Kissualizer.background_color = Kissualizer.polyscope.imgui.ColorEdit3(
            "Background Color", Kissualizer.background_color
        )
        if changed:
            Kissualizer.polyscope.set_background_color(Kissualizer.background_color)

        # GLOBAL_VIEW
        if Kissualizer.polyscope.imgui.Button("GLOBAL VIEW"):
            Kissualizer.global_view = not Kissualizer.global_view
            Kissualizer.polyscope.get_point_cloud("trajectory").set_enabled(Kissualizer.global_view)
            if Kissualizer.global_view:
                Kissualizer.polyscope.get_point_cloud("current_frame").set_transform(
                    Kissualizer.last_pose
                )
                Kissualizer.polyscope.get_point_cloud("keypoints").set_transform(
                    Kissualizer.last_pose
                )
                Kissualizer.polyscope.get_point_cloud("local_map").set_transform(np.eye(4))
                Kissualizer.polyscope.reset_camera_to_home_view()
            else:
                Kissualizer.polyscope.get_point_cloud("current_frame").set_transform(np.eye(4))
                Kissualizer.polyscope.get_point_cloud("keypoints").set_transform(np.eye(4))
                Kissualizer.polyscope.get_point_cloud("local_map").set_transform(
                    np.linalg.inv(Kissualizer.last_pose)
                )

                Kissualizer.polyscope.look_at((0.0, 0.0, 300.0), (1.0, 1.0, 1.0))

        # QUIT
        if Kissualizer.polyscope.imgui.Button("QUIT"):
            print("Destroying Visualizer")
            Kissualizer.polyscope.unshow()
            os._exit(0)


class RegistrationVisualizer(StubVisualizer):
    # Public Interface ----------------------------------------------------------------------------
    def __init__(self):
        try:
            self.o3d = importlib.import_module("open3d")
        except ModuleNotFoundError as err:
            print(f'open3d is not installed on your system, run "pip install open3d"')
            exit(1)

        # Initialize GUI controls
        self.block_vis = True
        self.play_crun = False
        self.reset_bounding_box = True

        # Create data
        self.source = self.o3d.geometry.PointCloud()
        self.keypoints = self.o3d.geometry.PointCloud()
        self.target = self.o3d.geometry.PointCloud()
        self.frames = []

        # Initialize visualizer
        self.vis = self.o3d.visualization.VisualizerWithKeyCallback()
        self._register_key_callbacks()
        self._initialize_visualizer()

        # Visualization options
        self.render_map = True
        self.render_source = True
        self.render_keypoints = False
        self.global_view = False
        self.render_trajectory = True
        # Cache the state of the visualizer
        self.state = (
            self.render_map,
            self.render_keypoints,
            self.render_source,
        )

    def update(self, source, keypoints, target_map, pose):
        target = target_map.point_cloud()
        self._update_geometries(source, keypoints, target, pose)
        while self.block_vis:
            self.vis.poll_events()
            self.vis.update_renderer()
            if self.play_crun:
                break
        self.block_vis = not self.block_vis

    # Private Interface ---------------------------------------------------------------------------
    def _initialize_visualizer(self):
        w_name = self.__class__.__name__
        self.vis.create_window(window_name=w_name, width=1920, height=1080)
        self.vis.add_geometry(self.source)
        self.vis.add_geometry(self.keypoints)
        self.vis.add_geometry(self.target)
        self._set_black_background(self.vis)
        self.vis.get_render_option().point_size = 1
        print(
            f"{w_name} initialized. Press:\n"
            "\t[SPACE] to pause/start\n"
            "\t  [ESC] to exit\n"
            "\t    [N] to step\n"
            "\t    [F] to toggle on/off the input cloud to the pipeline\n"
            "\t    [K] to toggle on/off the subsbampled frame\n"
            "\t    [M] to toggle on/off the local map\n"
            "\t    [V] to toggle ego/global viewpoint\n"
            "\t    [T] to toggle the trajectory view(only available in global view)\n"
            "\t    [C] to center the viewpoint\n"
            "\t    [W] to toggle a white background\n"
            "\t    [B] to toggle a black background\n"
        )

    def _register_key_callback(self, keys: List, callback: Callable):
        for key in keys:
            self.vis.register_key_callback(ord(str(key)), partial(callback))

    def _register_key_callbacks(self):
        self._register_key_callback(["Ā", "Q", "\x1b"], self._quit)
        self._register_key_callback([" "], self._start_stop)
        self._register_key_callback(["N"], self._next_frame)
        self._register_key_callback(["V"], self._toggle_view)
        self._register_key_callback(["C"], self._center_viewpoint)
        self._register_key_callback(["F"], self._toggle_source)
        self._register_key_callback(["K"], self._toggle_keypoints)
        self._register_key_callback(["M"], self._toggle_map)
        self._register_key_callback(["T"], self._toggle_trajectory)
        self._register_key_callback(["B"], self._set_black_background)
        self._register_key_callback(["W"], self._set_white_background)

    def _set_black_background(self, vis):
        vis.get_render_option().background_color = [0.0, 0.0, 0.0]

    def _set_white_background(self, vis):
        vis.get_render_option().background_color = [1.0, 1.0, 1.0]

    def _quit(self, vis):
        print("Destroying Visualizer")
        vis.destroy_window()
        os._exit(0)

    def _next_frame(self, vis):
        self.block_vis = not self.block_vis

    def _start_stop(self, vis):
        self.play_crun = not self.play_crun

    def _toggle_source(self, vis):
        if self.render_keypoints:
            self.render_keypoints = False
            self.render_source = True
        else:
            self.render_source = not self.render_source
        return False

    def _toggle_keypoints(self, vis):
        if self.render_source:
            self.render_source = False
            self.render_keypoints = True
        else:
            self.render_keypoints = not self.render_keypoints

        return False

    def _toggle_map(self, vis):
        self.render_map = not self.render_map
        return False

    def _toggle_view(self, vis):
        self.global_view = not self.global_view
        self._trajectory_handle()

    def _center_viewpoint(self, vis):
        vis.reset_view_point(True)

    def _toggle_trajectory(self, vis):
        if not self.global_view:
            return False
        self.render_trajectory = not self.render_trajectory
        self._trajectory_handle()
        return False

    def _trajectory_handle(self):
        if self.render_trajectory and self.global_view:
            for frame in self.frames:
                self.vis.add_geometry(frame, reset_bounding_box=False)
        else:
            for frame in self.frames:
                self.vis.remove_geometry(frame, reset_bounding_box=False)

    def _update_geometries(self, source, keypoints, target, pose):
        # Source hot frame
        if self.render_source:
            self.source.points = self.o3d.utility.Vector3dVector(source)
            self.source.paint_uniform_color(CYAN)
            if self.global_view:
                self.source.transform(pose)
        else:
            self.source.points = self.o3d.utility.Vector3dVector()

        # Keypoints
        if self.render_keypoints:
            self.keypoints.points = self.o3d.utility.Vector3dVector(keypoints)
            self.keypoints.paint_uniform_color(CYAN)
            if self.global_view:
                self.keypoints.transform(pose)
        else:
            self.keypoints.points = self.o3d.utility.Vector3dVector()

        # Target Map
        if self.render_map:
            target = copy.deepcopy(target)
            self.target.points = self.o3d.utility.Vector3dVector(target)
            if self.global_view:
                self.target.paint_uniform_color(GRAY)
            else:
                self.target.transform(np.linalg.inv(pose))
        else:
            self.target.points = self.o3d.utility.Vector3dVector()

        # Update always a list with all the trajectories
        new_frame = self.o3d.geometry.TriangleMesh.create_sphere(SPHERE_SIZE)
        new_frame.paint_uniform_color(BLUE)
        new_frame.compute_vertex_normals()
        new_frame.transform(pose)
        self.frames.append(new_frame)
        # Render trajectory, only if it make sense (global view)
        if self.render_trajectory and self.global_view:
            self.vis.add_geometry(self.frames[-1], reset_bounding_box=False)

        self.vis.update_geometry(self.keypoints)
        self.vis.update_geometry(self.source)
        self.vis.update_geometry(self.target)
        if self.reset_bounding_box:
            self.vis.reset_view_point(True)
            self.reset_bounding_box = False
