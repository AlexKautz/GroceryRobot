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
import subprocess
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped

from cv_bridge import CvBridge
import cv2

# 6 test positions: (x, y, z) in world frame, all on the table surface
TEST_POSITIONS = [
    (0.35,  0.0,  0.065),   # 1 — center
    (0.3,  0.1,  0.065),   # 2 — left edge
    (0.3, -0.1,  0.065),   # 3 — right edge
    (0.4,  0.1,  0.065),   # 4 — far from arm
    (0.4,  -0.1,  0.065),   # 5 — near-left

]

OUTPUT_DIR = os.path.expanduser("~/Code/ROS/GroceryRobot/apple_detection_test")


class AppleDetectionTester(Node):

    def __init__(self):
        super().__init__("apple_detection_tester")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self.bridge = CvBridge()
        self._latest_image = None
        self._image_updated = False
        self._detection_results = []

        self.create_subscription(
            Image,
            "/overhead_camera/annotated_image",
            self._image_callback,
            10,
        )

        self.get_logger().info(f"Saving images to: {OUTPUT_DIR}")

        

        self.create_subscription(
            PointStamped,
            "/overhead_camera/apple_location",
            self._location_callback,
            10,
        )
        self._latest_location = None

        self._latest_image = None
        self._latest_image_stamp = None

    def _image_callback(self, msg: Image):
        self._latest_image = msg
        self._latest_image_stamp = msg.header.stamp

    

    def _move_apple(self, x, y, z):
        req = f'name: "apple" position: {{x: {x} y: {y} z: {z}}} orientation: {{w: 1.0}}'
        cmd = [
            "gz", "service", "-s", "/world/empty/set_pose/blocking",
            "--reqtype", "gz.msgs.Pose",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "2000",
            "--req", req
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.get_logger().error(f"gz service failed: {result.stderr}")
            return False
        self.get_logger().info(f"Apple moved to ({x}, {y}, {z})")
        return True

    def _wait_for_fresh_image(self, prev_stamp, timeout=5.0):
        deadline = time.time() + timeout

        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

            if self._latest_image_stamp is None:
                continue

            # Wait until we get a strictly newer frame
            if prev_stamp is None or (
                self._latest_image_stamp.sec > prev_stamp.sec or
                (self._latest_image_stamp.sec == prev_stamp.sec and
                self._latest_image_stamp.nanosec > prev_stamp.nanosec)
            ):
                return True

        return False

    def _save_image(self, position_index, x, y, z):
        detected = self._latest_location is not None
        est_x = self._latest_location.point.x if detected else None
        est_y = self._latest_location.point.y if detected else None
        est_z = self._latest_location.point.z if detected else None

        error = None
        if detected:
            error = ((est_x - x)**2 + (est_y - y)**2 + (est_z - z)**2) ** 0.5

        self._detection_results.append({
            'pos': position_index,
            'true': (x, y, z),
            'estimated': (est_x, est_y, est_z),
            'detected': detected,
            'error_m': error,
        })

        if self._latest_image is None:
            return

        cv_img = self.bridge.imgmsg_to_cv2(self._latest_image, "rgb8")
        cv_img_bgr = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)

        label = f"Pos {position_index}: ({x:.2f}, {y:.2f}, {z:.2f})"
        status = f"{'DETECTED' if detected else 'MISSED'}"
        if error is not None:
            status += f"  err={error:.3f}m"

        cv2.putText(cv_img_bgr, label,  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(cv_img_bgr, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if not detected else (0, 255, 0), 2)

        filename = os.path.join(OUTPUT_DIR, f"pos{position_index:02d}_x{x:.2f}_y{y:.2f}.png")
        cv2.imwrite(filename, cv_img_bgr)
        self.get_logger().info(f"Saved: {filename}")

    def run_all_tests(self):
        # Give the localizer time to start up
        self.get_logger().info("Waiting 3s for system to stabilize...")
        time.sleep(3.0)

        for i, (x, y, z) in enumerate(TEST_POSITIONS, start=1):
            self._latest_location = None

            # Capture timestamp before moving
            prev_stamp = self._latest_image_stamp

            self.get_logger().info(
                f"\n=== Test {i}/5: moving apple to ({x}, {y}, {z}) ==="
            )

            moved = self._move_apple(x, y, z)
            if not moved:
                continue

            time.sleep(1.0) 

            got_image = self._wait_for_fresh_image(prev_stamp, timeout=5.0)

            if not got_image:
                self.get_logger().warn(f"No new image after move {i}")

            self._save_image(i, x, y, z)
    def _write_summary(self):
        path = os.path.join(OUTPUT_DIR, "test_summary.txt")
        with open(path, "w") as f:
            f.write("Apple Detection Test Summary\n")
            f.write("=" * 50 + "\n\n")
            detected_count = sum(1 for r in self._detection_results if r['detected'])
            f.write(f"Detection rate: {detected_count}/{len(self._detection_results)}\n\n")

            for r in self._detection_results:
                tx, ty, tz = r['true']
                f.write(f"Position {r['pos']}\n")
                f.write(f"  True world:      ({tx:.3f}, {ty:.3f}, {tz:.3f})\n")
                if r['detected']:
                    ex, ey, ez = r['estimated']
                    f.write(f"  Estimated world: ({ex:.3f}, {ey:.3f}, {ez:.3f})\n")
                    f.write(f"  3D error:        {r['error_m']:.4f} m\n")
                else:
                    f.write(f"  Result:          NOT DETECTED\n")
                f.write("\n")

        self.get_logger().info(f"Summary written to: {path}")

    def _location_callback(self, msg: PointStamped):
        self._latest_location = msg


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