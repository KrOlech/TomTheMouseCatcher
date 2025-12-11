#pylint: disable=wildcard-import
#pylint: disable=unused-wildcard-import
#pylint: disable=unused-import
#pylint: disable=duplicate-code
"""
test file for testing basic movement
"""

from cl57t_raspberry_pi_stepper_drive.CL57TStepperDriver import *

print("---")
print("SCRIPT START")
print("---")

# Pinout
# GPIO 26 (pin 37): ALM
# GPIO 19 (pin 35): ENA
# GPIO 13 (pin 33): DIR
# GPIO 6 (pin 31): PUL/STEP
# GPIO 5 (pin 29): HOMING_SENSOR

#-----------------------------------------------------------------------
# initiate the CL57T class
# use your pins for pin_en, pin_step, pin_dir here
#-----------------------------------------------------------------------
stepper = CL57TStepperDriver(
    pin_en=19, # GPIO 19 (pin 35): ENA
    pin_step=6, # GPIO 6 (pin 31): PUL/STEP
    pin_dir=13, # GPIO 13 (pin 33): DIR
    pin_homing_sensor=5, # GPIO 2 (pin 29): HOMING_SENSOR
    microstepping_resolution=1600,
    gearwheel_diameter_mm=56, # HTD 36 5M 09
    loglevel=Loglevel.DEBUG,
)

#-----------------------------------------------------------------------
# set the loglevel of the libary (currently only printed)
# set whether the movement should be relative or absolute
# both optional
#-----------------------------------------------------------------------
stepper.cl57t_logger.set_loglevel(Loglevel.DEBUG)
stepper.set_movement_abs_rel(MovementAbsRel.ABSOLUTE)

print("---\n---")


#-----------------------------------------------------------------------
# activate the motor current output
#-----------------------------------------------------------------------
stepper.set_motor_enabled(True)

stepper.set_acceleration(800)
stepper.set_max_speed(800)
stepper.do_homing()

stepper.set_acceleration(1600 * 10)
stepper.set_max_speed(10000)


stepper.set_homing_position_mm(400)

stepper.run_to_position_mm(1000)

stepper.run_to_position_mm(400)


#-----------------------------------------------------------------------
# move the motor 1 revolution
#-----------------------------------------------------------------------
# stepper.run_to_position_steps(9)                             #move to position 400
# stepper.run_to_position_steps(0)                               #move to position 0
#
#
# stepper.run_to_position_steps(400, MovementAbsRel.RELATIVE)    #move 400 steps forward
# stepper.run_to_position_steps(-400, MovementAbsRel.RELATIVE)   #move 400 steps backward
#
#
# stepper.run_to_position_steps(400)                             #move to position 400
# stepper.run_to_position_steps(0)                               #move to position 0


#-----------------------------------------------------------------------
# deactivate the motor current output
#-----------------------------------------------------------------------
stepper.set_motor_enabled(False)

print("---\n---")


#-----------------------------------------------------------------------
# deinitiate the CL57T class
#-----------------------------------------------------------------------
del stepper

print("---")
print("SCRIPT FINISHED")
print("---")