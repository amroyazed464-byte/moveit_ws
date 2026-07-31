from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SRC = PACKAGE_ROOT.parent
DESCRIPTION_XACRO = (
    WORKSPACE_SRC / "my_robot_description" / "urdf" / "arm.xacro"
)
DESCRIPTION_PACKAGE = WORKSPACE_SRC / "my_robot_description"
CONFIG_DIR = PACKAGE_ROOT / "config"

EXPECTED_ARM_JOINTS = [
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
]
GRIPPER_COMMAND_JOINT = "gripper_finger_left_joint"
GRIPPER_MIMIC_JOINT = "gripper_finger_right_joint"
EXPECTED_ACTIVE_JOINTS = EXPECTED_ARM_JOINTS + [
    GRIPPER_COMMAND_JOINT,
    GRIPPER_MIMIC_JOINT,
]
EXPECTED_LINKS = [
    "base_link",
    "shoulder_link",
    "arm_link",
    "elbow_link",
    "forearm_link",
    "wrist_link",
    "hand_link",
    "gripper_base",
    "gripper_finger_left",
    "gripper_finger_right",
    "tool_link",
]
EXPECTED_LINK_GEOMETRY = {
    "base_link": ("box", {"size": "0.4 0.4 0.1"}, "0 0 0.05"),
    "shoulder_link": (
        "cylinder",
        {"length": "0.5", "radius": "0.1"},
        "0 0 0.25",
    ),
    "arm_link": (
        "cylinder",
        {"length": "0.6", "radius": "0.05"},
        "0 0 0.3",
    ),
    "elbow_link": (
        "cylinder",
        {"length": "0.1", "radius": "0.05"},
        "0 0 0.05",
    ),
    "forearm_link": (
        "cylinder",
        {"length": "0.5", "radius": "0.05"},
        "0 0 0.25",
    ),
    "wrist_link": ("box", {"size": "0.1 0.1 0.05"}, "0 0 0.025"),
    "hand_link": ("box", {"size": "0.1 0.1 0.02"}, "0 0 0.01"),
    "gripper_base": ("box", {"size": "0.12 0.08 0.04"}, "0 0 0.02"),
    "gripper_finger_left": (
        "box",
        {"size": "0.02 0.04 0.12"},
        "0 0 0.06",
    ),
    "gripper_finger_right": (
        "box",
        {"size": "0.02 0.04 0.12"},
        "0 0 0.06",
    ),
}
EXPECTED_JOINT_LAYOUT = {
    "joint1": ("base_link", "shoulder_link", "revolute", "0 0 0.1", "0 0 1"),
    "joint2": ("shoulder_link", "arm_link", "revolute", "0 0 0.5", "0 1 0"),
    "joint3": ("arm_link", "elbow_link", "revolute", "0 0 0.6", "0 1 0"),
    "joint4": ("elbow_link", "forearm_link", "revolute", "0 0 0.1", "0 0 1"),
    "joint5": ("forearm_link", "wrist_link", "revolute", "0 0 0.5", "0 1 0"),
    "joint6": ("wrist_link", "hand_link", "revolute", "0 0 0.05", "0 0 1"),
    "gripper_base_joint": (
        "hand_link",
        "gripper_base",
        "fixed",
        "0 0 0.02",
        None,
    ),
    "gripper_finger_left_joint": (
        "gripper_base",
        "gripper_finger_left",
        "prismatic",
        "0.01 0 0.04",
        "1 0 0",
    ),
    "gripper_finger_right_joint": (
        "gripper_base",
        "gripper_finger_right",
        "prismatic",
        "-0.01 0 0.04",
        "1 0 0",
    ),
    "tool_joint": ("gripper_base", "tool_link", "fixed", "0 0 0.10", None),
}
EXPECTED_POSES = {
    "home": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "pose_1": [1.1705, 1.1686, 0.9172, 1.2449, 0.9940, 1.0596],
    "pose_2": [1.5421, 1.57, 0.5030, 0.2787, 1.3285, 1.7659],
}
MATURE_MODEL_JOINTS = {
    "base_yaw_joint",
    "shoulder_roll_joint",
    "elbow_roll_joint",
    "wrist_yaw_joint",
    "wrist_roll_joint",
    "tool_yaw_joint",
}
XACRO_NS = "http://www.ros.org/wiki/xacro"


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(
                f"duplicate YAML key {key!r} at line "
                f"{key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


class MoveItConfigContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.urdf_root = ET.parse(DESCRIPTION_XACRO).getroot()
        cls.urdf_joints = {
            joint.attrib["name"]: joint
            for joint in cls.urdf_root.findall("joint")
        }
        cls.urdf_links = {
            link.attrib["name"] for link in cls.urdf_root.findall("link")
        }

    def test_learning_urdf_has_expected_arm_chain(self):
        active_joints = [
            name
            for name, joint in self.urdf_joints.items()
            if joint.attrib["type"] != "fixed"
        ]
        self.assertEqual(EXPECTED_ACTIVE_JOINTS, active_joints)
        self.assertEqual(set(EXPECTED_LINKS), self.urdf_links)
        self.assertEqual("revolute", self.urdf_joints["joint6"].attrib["type"])

    def test_gripper_joint_limits_and_mimic_contract(self):
        left = self.urdf_joints[GRIPPER_COMMAND_JOINT]
        left_limit = left.find("limit")
        self.assertEqual("0", left_limit.attrib["lower"])
        self.assertEqual("0.034", left_limit.attrib["upper"])
        self.assertEqual("20", left_limit.attrib["effort"])
        self.assertEqual("0.1", left_limit.attrib["velocity"])

        right = self.urdf_joints[GRIPPER_MIMIC_JOINT]
        right_limit = right.find("limit")
        self.assertEqual("-0.034", right_limit.attrib["lower"])
        self.assertEqual("0", right_limit.attrib["upper"])
        mimic = right.find("mimic")
        self.assertEqual(GRIPPER_COMMAND_JOINT, mimic.attrib["joint"])
        self.assertEqual("-1.0", mimic.attrib["multiplier"])

    def test_learning_urdf_link_geometry_and_collisions_match(self):
        for link_name, (
            shape_name,
            expected_attributes,
            expected_origin,
        ) in EXPECTED_LINK_GEOMETRY.items():
            link = next(
                link
                for link in self.urdf_root.findall("link")
                if link.attrib["name"] == link_name
            )
            for element_name in ("visual", "collision"):
                with self.subTest(link=link_name, element=element_name):
                    element = link.find(element_name)
                    self.assertIsNotNone(element)
                    origin = element.find("origin")
                    self.assertEqual(expected_origin, origin.attrib["xyz"])
                    self.assertEqual("0 0 0", origin.attrib.get("rpy", "0 0 0"))
                    shape = element.find(f"geometry/{shape_name}")
                    self.assertIsNotNone(shape)
                    self.assertEqual(expected_attributes, shape.attrib)

        tool_link = next(
            link
            for link in self.urdf_root.findall("link")
            if link.attrib["name"] == "tool_link"
        )
        self.assertIsNone(tool_link.find("collision"))

    def test_tool_link_has_visual_marker_required_for_rviz_trail(self):
        tool_link = next(
            link
            for link in self.urdf_root.findall("link")
            if link.attrib["name"] == "tool_link"
        )
        visual = tool_link.find("visual")
        self.assertIsNotNone(
            visual,
            "RViz cannot render Show Trail for a link without visual geometry",
        )
        self.assertEqual("0 0 0", visual.find("origin").attrib["xyz"])
        self.assertEqual(
            {"radius": "0.015"},
            visual.find("geometry/sphere").attrib,
        )
        self.assertIsNone(tool_link.find("collision"))

    def test_learning_urdf_joint_layout_matches_physical_stack(self):
        self.assertEqual(set(EXPECTED_JOINT_LAYOUT), set(self.urdf_joints))
        for joint_name, (
            expected_parent,
            expected_child,
            expected_type,
            expected_origin,
            expected_axis,
        ) in EXPECTED_JOINT_LAYOUT.items():
            with self.subTest(joint=joint_name):
                joint = self.urdf_joints[joint_name]
                self.assertEqual(expected_type, joint.attrib["type"])
                self.assertEqual(
                    expected_parent, joint.find("parent").attrib["link"]
                )
                self.assertEqual(
                    expected_child, joint.find("child").attrib["link"]
                )
                origin = joint.find("origin")
                self.assertEqual(expected_origin, origin.attrib["xyz"])
                self.assertEqual("0 0 0", origin.attrib.get("rpy", "0 0 0"))
                axis = joint.find("axis")
                if expected_axis is None:
                    self.assertIsNone(axis)
                else:
                    self.assertEqual(expected_axis, axis.attrib["xyz"])

    def test_learning_description_package_installs_existing_resources(self):
        cmake_text = (DESCRIPTION_PACKAGE / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        install_match = re.search(
            r"install\(\s*DIRECTORY(?P<directories>.*?)DESTINATION",
            cmake_text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(install_match)
        installed_directories = install_match.group("directories").split()
        self.assertTrue(installed_directories)
        for directory in installed_directories:
            self.assertTrue(
                (DESCRIPTION_PACKAGE / directory).is_dir(),
                f"CMake installs missing directory {directory}",
            )

        manifest = ET.parse(DESCRIPTION_PACKAGE / "package.xml").getroot()
        runtime_dependencies = {
            element.text.strip()
            for tag in ("depend", "exec_depend")
            for element in manifest.findall(tag)
        }
        for dependency in {
            "ament_index_python",
            "joint_state_publisher_gui",
            "robot_state_publisher",
            "rviz2",
            "xacro",
        }:
            self.assertIn(dependency, runtime_dependencies)

    def test_srdf_uses_learning_chain_and_valid_named_poses(self):
        srdf_root = ET.parse(CONFIG_DIR / "my_robot.srdf").getroot()
        arm_group = next(
            group
            for group in srdf_root.findall("group")
            if group.attrib["name"] == "arm"
        )
        chain = arm_group.find("chain")
        self.assertEqual("base_link", chain.attrib["base_link"])
        self.assertEqual("tool_link", chain.attrib["tip_link"])

        actual_poses = {}
        for state in srdf_root.findall("group_state"):
            if state.attrib["group"] != "arm":
                continue
            values = {
                joint.attrib["name"]: float(joint.attrib["value"])
                for joint in state.findall("joint")
            }
            self.assertEqual(
                set(EXPECTED_ARM_JOINTS),
                set(values),
                f"{state.attrib['name']} must define every learning-arm joint",
            )
            actual_poses[state.attrib["name"]] = [
                values[name] for name in EXPECTED_ARM_JOINTS
            ]

        self.assertEqual(EXPECTED_POSES, actual_poses)

        for pose_name, values in actual_poses.items():
            for joint_name, value in zip(EXPECTED_ARM_JOINTS, values):
                limit = self.urdf_joints[joint_name].find("limit")
                lower = float(limit.attrib["lower"])
                upper = float(limit.attrib["upper"])
                self.assertGreaterEqual(
                    value, lower, f"{pose_name}/{joint_name} below limit"
                )
                self.assertLessEqual(
                    value, upper, f"{pose_name}/{joint_name} above limit"
                )

        disabled_pairs = srdf_root.findall("disable_collisions")
        self.assertGreater(
            len(disabled_pairs),
            7,
            "self-collision matrix must include sampled non-adjacent pairs",
        )
        self.assertIn(
            "Never",
            {pair.attrib["reason"] for pair in disabled_pairs},
            "self-collision matrix must contain Setup Assistant samples",
        )
        for disabled_pair in disabled_pairs:
            self.assertIn(disabled_pair.attrib["link1"], self.urdf_links)
            self.assertIn(disabled_pair.attrib["link2"], self.urdf_links)

    def test_controller_joint_order_and_interfaces_match(self):
        moveit = load_yaml(CONFIG_DIR / "moveit_controllers.yaml")
        moveit_manager = moveit["moveit_simple_controller_manager"]
        self.assertEqual(["arm_controller"], moveit_manager["controller_names"])
        self.assertEqual(
            EXPECTED_ARM_JOINTS,
            moveit_manager["arm_controller"]["joints"],
        )
        self.assertEqual(
            "FollowJointTrajectory",
            moveit_manager["arm_controller"]["type"],
        )
        self.assertEqual(
            "follow_joint_trajectory",
            moveit_manager["arm_controller"]["action_ns"],
        )

        ros2 = load_yaml(CONFIG_DIR / "ros2_controllers.yaml")
        arm = ros2["arm_controller"]["ros__parameters"]
        self.assertEqual(EXPECTED_ARM_JOINTS, arm["joints"])
        self.assertEqual(["position"], arm["command_interfaces"])
        self.assertEqual(["position", "velocity"], arm["state_interfaces"])
        self.assertFalse(arm["allow_nonzero_velocity_at_trajectory_end"])

    def test_fake_hardware_is_defined_exactly_once(self):
        wrapper_root = ET.parse(CONFIG_DIR / "my_robot.urdf.xacro").getroot()
        includes = [
            element.attrib["filename"]
            for element in wrapper_root.findall(f"{{{XACRO_NS}}}include")
        ]
        self.assertIn(
            "$(find my_robot_description)/urdf/arm.xacro",
            includes,
        )
        self.assertNotIn(
            "$(find robot_description)/urdf/my_robot.xacro",
            includes,
        )

        macro_root = ET.parse(
            CONFIG_DIR / "my_robot.ros2_control.xacro"
        ).getroot()
        control_blocks = macro_root.findall(
            f".//ros2_control"
        )
        self.assertEqual(1, len(control_blocks))
        controlled_joints = [
            joint.attrib["name"]
            for joint in control_blocks[0].findall("joint")
        ]
        self.assertEqual(EXPECTED_ARM_JOINTS, controlled_joints)
        for joint in control_blocks[0].findall("joint"):
            self.assertEqual(
                ["position"],
                [
                    interface.attrib["name"]
                    for interface in joint.findall("command_interface")
                ],
            )
            self.assertEqual(
                ["position", "velocity"],
                [
                    interface.attrib["name"]
                    for interface in joint.findall("state_interface")
                ],
            )

        self.assertEqual([], self.urdf_root.findall(".//ros2_control"))

    def test_initial_positions_and_joint_limits_cover_all_joints(self):
        initial = load_yaml(CONFIG_DIR / "initial_positions.yaml")
        self.assertEqual(
            {joint: 0 for joint in EXPECTED_ARM_JOINTS},
            initial["initial_positions"],
        )

        limits = load_yaml(CONFIG_DIR / "joint_limits.yaml")
        self.assertEqual(0.1, limits["default_velocity_scaling_factor"])
        self.assertEqual(0.1, limits["default_acceleration_scaling_factor"])
        self.assertEqual(
            set(EXPECTED_ARM_JOINTS),
            set(limits["joint_limits"]),
        )
        for joint_name in EXPECTED_ARM_JOINTS:
            override = limits["joint_limits"][joint_name]
            urdf_limit = self.urdf_joints[joint_name].find("limit")
            self.assertTrue(override["has_velocity_limits"])
            self.assertEqual(
                float(urdf_limit.attrib["velocity"]),
                float(override["max_velocity"]),
            )
            self.assertTrue(override["has_acceleration_limits"])
            self.assertEqual(1.0, float(override["max_acceleration"]))

    def test_setup_assistant_and_package_select_learning_description(self):
        try:
            setup = load_yaml(PACKAGE_ROOT / ".setup_assistant")
        except ValueError as exc:
            self.fail(str(exc))
        config = setup["moveit_setup_assistant_config"]
        self.assertEqual("my_robot_description", config["urdf"]["package"])
        self.assertEqual("urdf/arm.xacro", config["urdf"]["relative_path"])

        manifest = ET.parse(PACKAGE_ROOT / "package.xml").getroot()
        runtime_dependencies = {
            element.text.strip()
            for tag in ("depend", "exec_depend")
            for element in manifest.findall(tag)
        }
        self.assertIn("my_robot_description", runtime_dependencies)
        self.assertNotIn("robot_description", runtime_dependencies)
        self.assertIn("joint_trajectory_controller", runtime_dependencies)
        self.assertIn("joint_state_broadcaster", runtime_dependencies)

    def test_all_yaml_files_have_unique_keys(self):
        for path in sorted(CONFIG_DIR.glob("*.yaml")):
            with self.subTest(path=path.name):
                try:
                    load_yaml(path)
                except ValueError as exc:
                    self.fail(str(exc))
        try:
            load_yaml(PACKAGE_ROOT / ".setup_assistant")
        except ValueError as exc:
            self.fail(str(exc))

    def test_mature_model_joint_names_are_absent(self):
        config_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(CONFIG_DIR.iterdir())
            if path.is_file()
        )
        for joint_name in MATURE_MODEL_JOINTS:
            self.assertNotIn(joint_name, config_text)

    def test_rviz_defaults_match_assignment_recording_requirements(self):
        rviz = load_yaml(CONFIG_DIR / "moveit.rviz")
        displays = rviz["Visualization Manager"]["Displays"]
        motion_planning = next(
            display
            for display in displays
            if display.get("Class") == "moveit_rviz_plugin/MotionPlanning"
        )

        self.assertFalse(motion_planning["Planned Path"]["Loop Animation"])
        self.assertTrue(
            motion_planning["Scene Robot"]["Links"]["tool_link"]["Show Trail"]
        )

if __name__ == "__main__":
    unittest.main()
