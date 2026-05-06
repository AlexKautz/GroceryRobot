"""
test_apple_detection.py
=======================
Moves the apple to 5 predefined positions in Gazebo, waits for the
overhead localizer to produce an annotated image, and saves each one.

Run AFTER the simulation and overhead_camera_localizer are already up:
    ros2 run <your_pkg> test_apple_detection
"""

import os
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Pose
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState
from cv_bridge import CvBridge
import cv2

# 5 test positions: (x, y, z) in world frame, all on the table surface
TEST_POSITIONS = [
    (0.35,  0.0,  0.065),   # 1 — center
    (0.35,  0.6,  0.065),   # 2 — left edge
    (0.35, -0.6,  0.065),   # 3 — right edge
    (0.55,  0.0,  0.065),   # 4 — far from arm
    (0.20,  0.3,  0.065),   # 5 — near-left
]

OUTPUT_DIR = os.path.expanduser("~/apple_detection_test")


class AppleDetectionTester(Node):

    def __init__(self):
        super().__init__("apple_detection_tester")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self.bridge = CvBridge()
        self._latest_image = None
        self._image_updated = False

        # Subscribe to the annotated image your localizer publishes
        self.create_subscription(
            Image,
            "/overhead_camera/annotated_image",
            self._image_callback,
            10,
        )

        # Service client to teleport the apple in Gazebo
        self._set_state_client = self.create_client(
            SetEntityState, "/set_entity_state"
        )

        self.get_logger().info(f"Saving images to: {OUTPUT_DIR}")

    def _image_callback(self, msg: Image):
        self._latest_image = msg
        self._image_updated = True

    def _move_apple(self, x, y, z):
        """Teleport the apple model to (x, y, z) via Gazebo service."""
        req = SetEntityState.Request()
        req.state = EntityState()
        req.state.name = "apple"
        req.state.pose = Pose()
        req.state.pose.position.x = x
        req.state.pose.position.y = y
        req.state.pose.position.z = z
        req.state.pose.orientation.w = 1.0

        if not self._set_state_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("SetEntityState service not available!")
            return False

        future = self._set_state_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        return future.result() is not None

    def _wait_for_fresh_image(self, timeout=5.0):
        """Block until a new annotated image arrives after the apple moved."""
        self._image_updated = False
        deadline = time.time() + timeout
        while not self._image_updated and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self._image_updated

    def _save_image(self, position_index, x, y, z):
        if self._latest_image is None:
            self.get_logger().warn(f"No image received for position {position_index}")
            return

        cv_img = self.bridge.imgmsg_to_cv2(self._latest_image, "rgb8")
        cv_img_bgr = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)

        # Overlay position label on the image
        label = f"Pos {position_index}: ({x:.2f}, {y:.2f}, {z:.2f})"
        cv2.putText(cv_img_bgr, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        filename = os.path.join(
            OUTPUT_DIR,
            f"pos{position_index:02d}_x{x:.2f}_y{y:.2f}_z{z:.2f}.png"
        )
        cv2.imwrite(filename, cv_img_bgr)
        self.get_logger().info(f"Saved: {filename}")

    def run_all_tests(self):
        # Give the localizer time to start up
        self.get_logger().info("Waiting 3s for system to stabilize...")
        time.sleep(3.0)

        for i, (x, y, z) in enumerate(TEST_POSITIONS, start=1):
            self.get_logger().info(
                f"\n=== Test {i}/5: moving apple to ({x}, {y}, {z}) ==="
            )

            moved = self._move_apple(x, y, z)
            if not moved:
                self.get_logger().error(f"Failed to move apple to position {i}")
                continue

            # Wait for physics to settle + localizer to process new frame
            time.sleep(1.5)

            got_image = self._wait_for_fresh_image(timeout=5.0)
            if not got_image:
                self.get_logger().warn(f"Timed out waiting for image at position {i}")

            self._save_image(i, x, y, z)

        self.get_logger().info(
            f"\nDone! All images saved to: {OUTPUT_DIR}"
        )
        self._write_summary()

    def _write_summary(self):
        """Write a plain-text summary of the test positions."""
        path = os.path.join(OUTPUT_DIR, "test_summary.txt")
        with open(path, "w") as f:
            f.write("Apple Detection Test Summary\n")
            f.write("=" * 40 + "\n\n")
            for i, (x, y, z) in enumerate(TEST_POSITIONS, start=1):
                fname = f"pos{i:02d}_x{x:.2f}_y{y:.2f}_z{z:.2f}.png"
                f.write(f"Position {i}: world ({x:.3f}, {y:.3f}, {z:.3f})  →  {fname}\n")
        self.get_logger().info(f"Summary written to: {path}")


def main(args=None):
    rclpy.init(args=args)
    tester = AppleDetectionTester()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        pass
    finally:
        tester.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()