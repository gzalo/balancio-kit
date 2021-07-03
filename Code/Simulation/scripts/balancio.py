""" Balancio: Pybullet self-balancing robot"""

import numpy as np
import motor
import os


URDF_PATH = os.path.join('/', *os.getcwd().split('/')[:-1], 'urdf', 'balancio_v1.urdf')

class Balancio:

    def __init__(self, bullet_client, urdf_root_path='', time_step=0.01, backlash=True):
        self.urdf_root_path = urdf_root_path  # Usar para mnodificar el path del URDF a uno relativo (?)
        self.time_step = time_step  # Intentar dejarlo en el estandar (240hz)
        self._p = bullet_client

        self.robotUniqueId = None
        self.backlash = backlash
        self.motors_num = 2
        self.joint_name2idx = {'left_gearbox': 0,
                               'left_wheel': 1,
                               'right_gearbox': 2,
                               'right_wheel': 3}
        self.motors = motor.MotorModel()
        self.reset()

    def reset(self):
        # Randomize initial orientation.
        orientation_init = self._p.getQuaternionFromEuler([0, np.random.uniform(-0.1, 0.1), 0])
        robot = self._p.loadURDF(URDF_PATH,
                                 [0, 0, 0.42],
                                 orientation_init,
                                 useFixedBase=False)
        self.robotUniqueId = robot

        # Disable default velocity control (Necessary for torque control)
        self._p.setJointMotorControlArray(bodyUniqueId=self.robotUniqueId,
                                          jointIndices=[self.joint_name2idx['left_gearbox'],
                                                        self.joint_name2idx['right_gearbox']],
                                          controlMode=self._p.VELOCITY_CONTROL,
                                          forces=[0, 0])
        if self.backlash:
            # Loose contact between gear and wheel
            self._p.setJointMotorControlArray(bodyUniqueId=self.robotUniqueId,
                                              jointIndices=[self.joint_name2idx['left_wheel'],
                                                            self.joint_name2idx['right_wheel']],
                                              controlMode=self._p.VELOCITY_CONTROL,
                                              targetVelocities=[0, 0],
                                              forces=[0, 0])  # Here you can add additional backlash friction.

    def get_action_dimension(self):
        return self.motors_num

    def get_observation_dimension(self):
        return len(self.get_observation())

    def get_observation(self):
        observation = []
        pos, orn = self._p.getBasePositionAndOrientation(self.robotUniqueId)

        orn_euler = self._p.getEulerFromQuaternion(orn)  # Pitch
        observation.extend([orn_euler[1]])

        return observation

    def apply_action(self, motor_commands):
        """Args:
            motor_commands: List containing pwm signal for each motor.
                            PWM range --> [-1, 1]"""

        state = self._p.getJointStates(bodyUniqueId=self.robotUniqueId,
                                       jointIndices=[self.joint_name2idx['left_gearbox'], self.joint_name2idx['right_gearbox']])

        torque, static_friction = self.motors.convert_to_torque(np.array(motor_commands), np.array([state[0][1], state[1][1]]))

        # Set static friction (set to 0 when dynamic friction starts acting).
        self._p.setJointMotorControlArray(bodyUniqueId=self.robotUniqueId,
                                          jointIndices=[self.joint_name2idx['left_gearbox'],
                                                        self.joint_name2idx['right_gearbox']],
                                          controlMode=self._p.VELOCITY_CONTROL,
                                          targetVelocities=[0, 0],
                                          forces=[static_friction[0], static_friction[1]])
        # Set torque
        self._p.setJointMotorControlArray(bodyUniqueId=self.robotUniqueId,
                                          jointIndices=[self.joint_name2idx['left_gearbox'], self.joint_name2idx['right_gearbox']],
                                          controlMode=self._p.TORQUE_CONTROL,
                                          forces=[torque[0], torque[1]])
