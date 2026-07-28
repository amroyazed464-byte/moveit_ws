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

EXPECTED_JOINTS = [
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
]
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
        self.assertEqual(EXPECTED_JOINTS, active_joints)
        self.assertIn("base_link", self.urdf_links)
        self.assertIn("tool_link", self.urdf_links)
        self.assertEqual("revolute", self.urdf_joints["joint6"].attrib["type"])

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
                set(EXPECTED_JOINTS),
                set(values),
                f"{state.attrib['name']} must define every learning-arm joint",
            )
            actual_poses[state.attrib["name"]] = [
                values[name] for name in EXPECTED_JOINTS
            ]

        self.assertEqual(EXPECTED_POSES, actual_poses)

        for pose_name, values in actual_poses.items():
            for joint_name, value in zip(EXPECTED_JOINTS, values):
                limit = self.urdf_joints[joint_name].find("limit")
                lower = float(limit.attrib["lower"])
                upper = float(limit.attrib["upper"])
                self.assertGreaterEqual(
                    value, lower, f"{pose_name}/{joint_name} below limit"
                )
                self.assertLessEqual(
                    value, upper, f"{pose_name}/{joint_name} above limit"
                )

        for disabled_pair in srdf_root.findall("disable_collisions"):
            self.assertIn(disabled_pair.attrib["link1"], self.urdf_links)
            self.assertIn(disabled_pair.attrib["link2"], self.urdf_links)

    def test_controller_joint_order_and_interfaces_match(self):
        moveit = load_yaml(CONFIG_DIR / "moveit_controllers.yaml")
        moveit_manager = moveit["moveit_simple_controller_manager"]
        self.assertEqual(["arm_controller"], moveit_manager["controller_names"])
        self.assertEqual(
            EXPECTED_JOINTS,
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
        self.assertEqual(EXPECTED_JOINTS, arm["joints"])
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
        self.assertEqual(EXPECTED_JOINTS, controlled_joints)
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
            {joint: 0 for joint in EXPECTED_JOINTS},
            initial["initial_positions"],
        )

        limits = load_yaml(CONFIG_DIR / "joint_limits.yaml")
        self.assertEqual(0.1, limits["default_velocity_scaling_factor"])
        self.assertEqual(0.1, limits["default_acceleration_scaling_factor"])
        self.assertEqual(
            set(EXPECTED_JOINTS),
            set(limits["joint_limits"]),
        )
        for joint_name in EXPECTED_JOINTS:
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
