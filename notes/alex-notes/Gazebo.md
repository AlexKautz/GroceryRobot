* Getting started: https://gazebosim.org/docs/all/getstarted/
   * `gz sim shapes.sdf`
      * Rather basic but it works!
      * `-v 4` gives debugging
      * Can also run headless with `-s`, not that that helps!
   * "SDF is used to specify the contents of simulation. Take a look at the available SDF tutorials to get started."
      * This is relevant to me!
      * https://app.gazebosim.org/fuel - lots of cool objects for Gazebo
* Building the Robot (and world): https://gazebosim.org/docs/ionic/building_robot/
   * `building_robot.sdf`
   * `gz sim building_robot.sdf`
   * Error!

```
gz sim gui: symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0: undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
```

   * This occurs because I am using the VSCode terminal, which can mess with the environment. Switching to the native terminal fixes it!
* Back to the tutorial!
	* 