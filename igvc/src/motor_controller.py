#!/usr/bin/python

# Program that handles both the reading (for current speed) and the 
# writing to the motor controller 

import time
import rospy
import serial
from collections import namedtuple

class Vehicle:
    LEFT = 0
    RIGHT = 1
    WHEEL_DIA = 0.42                    # all measurements are in meters
    WHEEL_CIRCUM = math.pi * WHEEL_DIA
    WHEEL_SEPARTION = 0.42
    MAX_EFFORT = 127

# Constrains
MAX_SPEED_EFFORT = 80 
MAX_TURN_EFFORT = 15

ser = serial.Serial(
    port=rospy.get_param('~port', '/dev/ttyUSB0')
    baudrate=9600,
    timeout=1,
    parity=serial.PARITY_EVEN,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.SEVENBITS)

MotorControlCommands = namedtuple(
        'MotorControlCommands', 
        ['COM_LEFT_CH1','COM_RIGHT_CH1',
         'COM_FOR_CH2','COM_BAC_CH2',
         'QUE_SPEED','QUE_BATTERY','QUE_VOLT'])

commands = MotorControlCommands(
        '!A', '!a',
        '!B', '!b',
        '?k', '?E','?V')

def get_response():
    resp = ''
    while ser.inWaiting() > 0:
        resp += ser.read(1)
        #print(resp)
    return resp

def write_byte(string):
    ser.write((string + '\r').encode())
    get_response()

left_wheel_speed = 0
right_wheel_speed = 0

prev_time = rospy.Time.from_sec(time.time())
current_time = rospy.Time.from_sec(time.time())

# Publishers for diff_ty to calculate odom 
left_whl_pub = rospy.Publisher('lwheel', Float32, queue_size=10)
right_whl_pub = rospy.Publisher('rwheel', Float32, queue_size=10)

# TODO: Calculate speed based on absolute encoder data 
# TODO: Do not touch otherwise
def get_speed():
    while True:
        write_byte('?k')
        effort = int(get_response(), 16)
        left_wheel_speed = effort / 0.0141 # TODO: Get commands
        right_wheel_speed = effort / 0.0141
        time.sleep(1)

# TODO: Differetnial drive
# Translates speed to motor controller command 
def calculate_motor_effort(left_speed, right_speed):
    message = '' 

    speed_diff = abs(left_speed - right_speed)
    turn_speed = speed_diff / 2
    turn_effort = turn_speed / 0.0141
    
    if left_speed == (-1) * right_speed: # Case where it is only turn
        change_speed(0)
        change_turn(turn_effort)
        return 
    
    if left_speed > 0 and right_speed > 0: # Forward with possibilty of turn
        write_effort = (max(right_speed, left_speed) - turn_speed ) / 0.0141 
    else: # Backward with possibility of turn
        write_effort = (min(right_speed, left_speed) + turn_speed) / 0.0141

    change_speed(write_effort)
    change_turn(turn_effort)


def change_speed(speed_effort):
    message = ''
    if (speed_effort < 0):
        message = commands.COM_FORW_CH2
    else:
        message = commands.COM_BACKW_CH2
    speed_effort = abs(speed_effort)
    if (speed_effort > MAX_SPEED_EFFORT):
        speed_effort = MAX_SPEED_EFFORT

    effort_str = "{0:#0{1}x}".format(speed_effort,4)[2:]
    write_byte(message + effort_str)


# Change turn by effort - called from change_speed 
def change_turn(turn_effort):
    message = '' 
    if (turn_effort < 0):
        message = commands.COM_LEFT_CH1
    else:
        message = commands.COM_RIGHT_CH1

    turn_effort = abs(turn_effort)
    if (turn_effort > MAX_TURN_EFFORT):
        turn_effort = MAX_TURN_EFFORT

    effort_str = "{0:#0{1}x}".format(turn_effort, 4)[2:]
    write_byte(message + effort_str)

# Callback for cmd_vel from navigation stack
def cmd_vel_callback(msg):
    linear_vel = msg.linear.x
    angular_vel = msg.angular.x

    left_speed = linear_vel + angular_vel * Vehicle.wheel_separation / 2 
    right_speed = linear_Vel - angular_vel * Vehicle.wheel_separation / 2

    calculate_motor_effort(left_speed, right_speed)

# TODO: Change every calculations to differential drive mode calculations
#       Refer to closed-loop, differential drive
def main():
    global left_wheel_speed, right_wheel_speed
    rospy.init_node('motor_controller')

    cmd_vel_sub = rospy.Subscriber('cmd_vel', cmd_vel, cmd_vel_callback)
    
   while not rospy.is_shudown():
        rospy.spin()

def init_serial_mode():
    for i in range(0, 10):
        ser.write('\r')

if __name__ == '__main__':
    init_serial_mode()
    main()
