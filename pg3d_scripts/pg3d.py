# rendering code was written by FINFET, and heavily modified by me
# (by that I mean I rewrote everything because FINFET didn't implement triangle clipping)

import pygame as pg
import numpy as np
from numba import njit
import random
from .pg3d_model import Model
from .pg3d_model import ModelTransform
from . import pg3d_math as m
from . import pg3d_rendering
from .pg3d_particle import ParticleManager

# just to keep track of things, not actually used in code
version = "0.4.1"

# this is the default sky color, but can be set using setBackgroundColor()
skyColor = np.asarray([1.0,1.0,1.0])

# mouse shennanigans
mouseChange = np.asarray([0.0,0.0]) # the change in the mouse since the last frame
mousePos = np.asarray([0.0,0.0]) # the mouse position, equal to pg.mouse.get_pos()

# an offset applied to the mouse position
# this allows reading the mouse position to go beyond the limits of the screen, good for camera controllers
mouseOffset = np.asarray([0.0,0.0]) 

# the rotate speed of the camera, used in camearaUpdate functions
cameraRotateSpeed = 0.001

# physics
gravityCoefficient = 9.81 # small g, the acceleration of gravity

# clock stuff
clock = pg.time.Clock()
hasClockStarted = False # fixing a weird timing issue that breaks physics
timeSinceLastFrame = 0

# the camera
# position (x,y,z), forward (x,y,z), up (x,y,z) (scale does nothing)
# the right vector is NOT defined/kept track of because it's unecessary, knowing the other two is enough
# why is the right vector the one that's ommited? idk
cameraWorldTransform = None
cameraLocalTransform = None
cameraParent = None

physicsEnabled = False
particlesEnabled = False

sky_texture = None

# joystick stuff ************************
# easier to include here, rather than in another class/script
# for now, the event that handles connecting joysticks is NOT a part of the engine
# you catch the event outside of the engine, and feed the event to connectJoystick() in the engine

# the joysticks that are currently connected to the computer
connectedJoysticks = []

firstPerson_camera_max_dot = 0.5
firstPerson_camera_min_dot = 0.5

# ********      main engine functions:     ********   
def init(w, h, wActual, hActual, ver):
    global clock

    global sky_texture

    global cameraLocalTransform
    global cameraWorldTransform
    global cameraParent

    verticalFOV = ver * np.pi / 180
    horizontalFOV = verticalFOV*w/h

    hA = 0.5*w/ np.tan(horizontalFOV * 0.5)
    vA = 0.5*h/ np.tan(verticalFOV * 0.5)
    
    pg3d_rendering.init(w, h, horizontalFOV, verticalFOV, hA, vA, "texture", "solid color", wActual, hActual)

    sky_texture = np.zeros((pg3d_rendering.renderConfig.screenWidth, pg3d_rendering.renderConfig.screenHeight * 3, 3)).astype('uint8')
    pg.surfarray.surface_to_array(sky_texture, pg.transform.scale(pg.image.load("pg3d_assets/sky_better.png"), (pg3d_rendering.renderConfig.screenWidth, pg3d_rendering.renderConfig.screenHeight * 3)))

    # required for pygame to work properly
    pg.init()

    clock = pg.time.Clock()

    # scale does nothing
    cameraLocalTransform = ModelTransform(np.asarray([0.0, 0.0, 0.0]), np.asarray([0.0, 0.0, 1.0]), np.asarray([0.0, 1.0, 0.0]), np.asarray([0.0, 0.0, 0.0]))
    cameraWorldTransform = ModelTransform(np.asarray([0.0, 0.0, 0.0]), np.asarray([0.0, 0.0, 1.0]), np.asarray([0.0, 1.0, 0.0]), np.asarray([0.0, 0.0, 0.0]))
    cameraParent = None

    pg.display.set_mode((pg3d_rendering.renderConfig.screenWidth_actual, pg3d_rendering.renderConfig.screenHeight_actual),pg.FULLSCREEN)

    pg.mouse.set_visible(0)
    pg.mouse.set_pos(pg3d_rendering.renderConfig.screenWidth/2,pg3d_rendering.renderConfig.screenHeight/2)

def spawnParticleSystem(name, scale, position, use_gravity, texture_path, life_time):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, texture_path, [], 0, False, False, Vector3.ZERO, 0, 0, 0, 0, 0, life_time, life_time)
def spawnAndPlayParticleSystem(name, scale, position, use_gravity, texture_path, life_time):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, texture_path, [], 0, False, False, Vector3.ZERO, 0, 0, 0, 0, 0, life_time, life_time).play()

def spawnParticleSystemWithVelocity(name, scale, position, use_gravity, texture_path, life_time, velocity_direction, max_magnitude, min_magnitude):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, texture_path, [], 0, False, False, velocity_direction, min_magnitude, max_magnitude, 0, 0, 0, life_time, life_time)
def spawnAndPlayParticleSystemWithVelocity(name, scale, position, use_gravity, texture_path, life_time, velocity_direction, max_magnitude, min_magnitude):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, texture_path, [], 0, False, False, velocity_direction, min_magnitude, max_magnitude, 0, 0, 0, life_time, life_time).play()

def spawnAnimatedParticleSystem(name, scale, position, use_gravity, animation_frames, time_between_frames, life_time, loop_animation, destroy_when_finished):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, '', animation_frames, time_between_frames, destroy_when_finished, loop_animation, Vector3.ZERO, 0, 0, 0, 0, 0, life_time, life_time)
def spawnAndPlayAnimatedParticleSystem(name, scale, position, use_gravity, animation_frames, time_between_frames, life_time, loop_animation, destroy_when_finished):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, '', animation_frames, time_between_frames, destroy_when_finished, loop_animation, Vector3.ZERO, 0, 0, 0, 0, 0, life_time, life_time).play()

def spawnAnimatedParticleSystemWithVelocity(name, scale, position, use_gravity, animation_frames, time_between_frames, life_time, loop_animation, destroy_when_finished, velocity_direction, max_magnitude, min_magnitude):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, '', animation_frames, time_between_frames, destroy_when_finished, loop_animation, velocity_direction, min_magnitude, max_magnitude, 0, 0, 0, life_time, life_time)
    # i think this one wins the longest function name contest
def spawnAndPlayAnimatedParticleSystemWithVelocity(name, scale, position, use_gravity, animation_frames, time_between_frames, life_time, loop_animation, destroy_when_finished, velocity_direction, max_magnitude, min_magnitude):
    ParticleManager(name, 1, 1, scale, scale, position, use_gravity, '', animation_frames, time_between_frames, destroy_when_finished, loop_animation, velocity_direction, min_magnitude, max_magnitude, 0, 0, 0, life_time, life_time).play()

def getParticleSystemWithName(name):
    for i in ParticleManager._registry:
        if (i.name == name):
            return i

def playParticleSystem(systemName):
    getParticleSystemWithName(systemName).play()

# this exists just so I don't have to call two functions every time

# it's called WHENEVER THE HEIRARCHY CHANGES, 
# and is NOT called during position/rotation updates
def refreshHeirarchy():
    refreshObjectOrder()
    refreshObjectTransforms()

# refreshing the object heirarchy
# DO NOT CALL THIS EVERY FRAME, IT'LL BE SLOW
def refreshObjectOrder():
    # this list will become the object registry, sorted by child level
    sortedObjects = []

    # the idea here is to look for all object of index 0,
    # then loop over again looking for 1,
    # and do that until you loop over everything without finding an index match
    currentlyLookingForLevel = 0
    hasFoundObject = True
    while (hasFoundObject):
        hasFoundObject = False

        for i in range(len(Model._registry)):
            if (Model._registry[i].childLevel == currentlyLookingForLevel):
                sortedObjects.append(Model._registry[i])
                hasFoundObject = True
        
        # after looping, increment the desired level
        currentlyLookingForLevel += 1

    # setting the registry equal to the sorted one, index by index
    for i in range(len(Model._registry)):
        Model._registry[i] = sortedObjects[i]

def get_first_joystick_triangle():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(3)

def get_first_joystick_square():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(2)

def get_first_joystick_circle():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(1)

def get_first_joystick_cross():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(0)

def get_first_joystick_left_bumper():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(9)

def get_first_joystick_right_bumper():
    if (len(connectedJoysticks) == 0):
        return False
    return connectedJoysticks[0].get_button(10)

def get_joystick_left_bumper(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(9)

def get_joystick_right_bumper(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(10)

def get_joystick_triangle(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(3)

def get_joystick_square(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(2)

def get_joystick_circle(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(1)

def get_joystick_cross(index):
    if (len(connectedJoysticks) <= index):
        return False
    return connectedJoysticks[index].get_button(0)

# will use the FIRST joystick
def get_first_joystick_left_x(deadband):
    if (len(connectedJoysticks) == 0):
        return 0
    val = connectedJoysticks[0].get_axis(0)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_first_joystick_left_y(deadband):
    if (len(connectedJoysticks) == 0):
        return 0
    val = connectedJoysticks[0].get_axis(1)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_first_joystick_right_x(deadband):
    if (len(connectedJoysticks) == 0):
        return 0
    val = connectedJoysticks[0].get_axis(2)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_first_joystick_right_y(deadband):
    if (len(connectedJoysticks) == 0):
        return 0
    val = connectedJoysticks[0].get_axis(3)
    if (np.abs(val) < deadband):
        return 0
    return val

# will use joystick with index specified
def get_joystick_left_x(index, deadband):
    if (len(connectedJoysticks) <= index):
        return 0
    val = connectedJoysticks[index].get_axis(0)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_joystick_left_y(index, deadband):
    if (len(connectedJoysticks) <= index):
        return 0
    val = connectedJoysticks[index].get_axis(1)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_joystick_right_x(index, deadband):
    if (len(connectedJoysticks) <= index):
        return 0
    val = connectedJoysticks[index].get_axis(2)
    if (np.abs(val) < deadband):
        return 0
    return val

def get_joystick_right_y(index, deadband):
    if (len(connectedJoysticks) <= index):
        return 0
    val = connectedJoysticks[index].get_axis(3)
    if (np.abs(val) < deadband):
        return 0
    return val

# yes, you could just have a deadband of 0
# instead I have made it its own function
def get_raw_joystick_left_x(index):
    if (len(connectedJoysticks) == 0):
        return 0
    return connectedJoysticks[index].get_axis(0)

def get_raw_joystick_left_y(index):
    if (len(connectedJoysticks) == 0):
        return 0
    return connectedJoysticks[index].get_axis(1)

def get_raw_joystick_right_x(index):
    if (len(connectedJoysticks) == 0):
        return 0
    return connectedJoysticks[index].get_axis(2)

def get_raw_joystick_right_y(index):
    if (len(connectedJoysticks) == 0):
        return 0
    return connectedJoysticks[index].get_axis(3)

def connectJoystick(event):
    joy = pg.joystick.Joystick(event.device_index)
    connectedJoysticks.append(joy)

# with the heirarchy refreshed, 
# we now have to loop through the objects to refresh their local/world vectors
# (if it isn't obvious, call this AFTER refreshObjectHeirarchy() or stuff breaks)
def refreshObjectTransforms():
    for i in range(len(Model._registry)):
        # the idea here is to leave the local forward, up, etc. alone
        # the WORLD transform is the one that's going to change
        
        # when the user messes with the heirarchy, the local vector won't change there either, it'll just mean something different
        Model._registry[i].syncTransformWithParent()

def disableBackfaceCulling():
    pg3d_rendering.renderConfig.backfaceCulling = False

def enableBackfaceCulling():
    pg3d_rendering.renderConfig.backfaceCulling = True

def enablePhysics():
    global physicsEnabled
    physicsEnabled = True

def disablePhysics():
    global physicsEnabled
    physicsEnabled = False

# particles are updated separately from normal physics objects
def enableParticles():
    global particlesEnabled
    particlesEnabled = True

def disableParticles():
    global particlesEnabled
    particlesEnabled = False

# used for camera controllers
def parentCamera(object, offset_x, offset_y, offset_z):
    global cameraParent

    cameraParent = object
    cameraLocalTransform.position = np.asarray([offset_x, offset_y, offset_z])

def parentCameraWithName(objName, offset_x, offset_y, offset_z):
    global cameraParent

    cameraParent = getObject(objName)
    cameraLocalTransform.position = np.asarray([offset_x, offset_y, offset_z])

def unParentCamera():
    global cameraParent
    cameraParent = None

def setRenderingMode(newMode):
    if (m.array_has_item(pg3d_rendering.renderingModes, newMode)):
        pg3d_rendering.renderConfig.renderingMode = newMode
        pg3d_rendering.renderingMode = newMode

def setBackgroundMode(newMode):
    if (m.array_has_item(pg3d_rendering.backGroundModes, newMode)):
        pg3d_rendering.renderConfig.backgroundMode = newMode

def update():
    global timeSinceLastFrame
    global clock
    global hasClockStarted

    global physicsEnabled
    global gravityCoefficient

    timeSinceLastFrame = clock.tick()*0.001

    if (not hasClockStarted):
        timeSinceLastFrame = 0
        hasClockStarted = True

    updateCursor()

    # could have made this use the same variable as physics, but ah well
    # this feels like a feature that's going to change lol
    if (particlesEnabled):
        for i in getObjectsWithTag("particle"):
            if (i.hasTag("gravity")):
                i.add_velocity(0.0,-1.0 * timeSinceLastFrame * gravityCoefficient, 0.0)
            if (i.hasTag("lookAtPlayer")):
                i.set_local_up(cameraWorldTransform.position - i.worldTransform.position)
            if (i.hasTag("animated")):
                # the bool being true means it was destroyed
                if (i.checkAnimation()):
                    continue

            if (i.hasTag("hasDrag") and m.length_3d(i.velocity)):
                i.add_velocity_vector(i.velocity * -i.data["drag_multiplier"])
            if (i.hasTag("scaleChange")):
                i.add_number_to_scale(i.data["scale_change"])

            if (i.data["life_time"] != -1):
                if (i.data["time_when_spawned"] + i.data["life_time"] < pg.time.get_ticks()):
                    destroyObject(i)
                    continue

            i.add_local_position(i.linearVelocity[0] * timeSinceLastFrame,i.linearVelocity[1] * timeSinceLastFrame,i.linearVelocity[2] * timeSinceLastFrame)

    if (physicsEnabled):
        for i in getObjectsWithTag("physics"):
            # objects can have physics, but still not have gravity applied
            # they have to have the gravity tag as well, for gravity
            if (i.hasTag("gravity")):
                i.add_velocity(0.0,-1.0 * timeSinceLastFrame * gravityCoefficient, 0.0)

            # collision logic

            # the strategy here is thus:

            # 0. find midpoint on this collider
            
            # 1. loop through all colliders

                # check intersection:

                # 1a. find closest point on the other collider to the midpoint of this collider
                # 1b. find closest point on THIS collider to the closest point on THAT collider (that we just figured out)
                # 1c. if the points from 1b and 1c are the same, there is an intersection

                # resolve intersection

                # 1d. move this object AWAY so that the closest point on this collider is the closest point on that collider
                # TODO: torque

            collidersInScene = getObjectsWithTag("box_collider")
            sphereCollidersInScene = getObjectsWithTag("sphere_collider")

            # this comes out as a point (x,y,z) (x transformed, y transformed, z transformed)
            # it's in world space!
            returnMidpoint = i.midpoint()
            worldSpaceMidpoint = np.asarray([returnMidpoint[3],returnMidpoint[4],returnMidpoint[5]])

            for j in collidersInScene:

                # don't do anything if talking about the same object
                if (j.name == i.name):
                    continue

                if (not j.shouldBePhysics):
                    continue

                closestPointOnOther = j.closest_point(worldSpaceMidpoint)

                closestPointOnThis = i.closest_point(closestPointOnOther)

                if (m.length_3d(m.subtract_3d(closestPointOnOther, closestPointOnThis)) < 0.01):
                    # this code only runs if the two points are the same (which happens if there's an intersection)

                    # figuring out where the closestPointOnThis should be, basically
                    pushVector = np.asarray([0.0,-1.0,0.0])
                    desiredPoint = i.closest_point(np.asarray([closestPointOnThis[0] + pushVector[0] * 100,closestPointOnThis[1] + pushVector[1] * 100,closestPointOnThis[2] + pushVector[2] * 100]))

                    # resolve the collision (hopefully) 
                    # (we're only moving the object, not what it's hitting, for now)

                    # turns out, this isn't an amazing solution
                    # gotta implement raycasting before I can rlly solve this properly
                    # fortunately, it's enough for a platformer game
                    i.add_local_position(closestPointOnThis[0] - desiredPoint[0],closestPointOnThis[1] - desiredPoint[1],closestPointOnThis[2] - desiredPoint[2])

                    # not a great permanent solution, but make the velocity 0 to make sure the collision stays resolved
                    i.set_velocity(0,0,0)

            # for sphere colliders
            for j in sphereCollidersInScene:
                # don't do anything if talking about the same object
                if (j.name == i.name):
                    continue
                    
                if (not j.shouldBePhysics): # colliddr isn't participating in interactions
                    continue

                # testing for an intersection is wayyy simpler, just a length check
                # (the whole point of sphere colliders is that they're easier to compute btw)

                mp = j.midpoint()
                otherMidpoint = np.asarray([mp[3],mp[4],mp[5]])

                distBetween = m.length_3d(worldSpaceMidpoint - otherMidpoint)

                localRadius = i.data["collider_bounds"]
                otherRadius = j.data["collider_bounds"]

                rSum = otherRadius + localRadius

                if (distBetween < rSum):
                    # there is an intersection!
                    pushVector = m.normalize_3d(worldSpaceMidpoint - otherMidpoint)

                    differenceInRadius = rSum - distBetween

                    i.add_local_position(pushVector[0] * differenceInRadius, pushVector[1] * differenceInRadius, pushVector[2] * differenceInRadius)

            i.add_local_position(i.linearVelocity[0] * timeSinceLastFrame,i.linearVelocity[1] * timeSinceLastFrame,i.linearVelocity[2] * timeSinceLastFrame)
                

def getFrame():
    global cameraWorldTransform
    global cameraLocalTransform
    global cameraParent
    global skyColor

    global renderingMode

    # like a directional light in unity
    light_dir = np.asarray([0.0,1.0,0.0])
    light_dir = light_dir/np.linalg.norm(light_dir)

    # refreshing the camera's transform
    cameraWorldTransform.copy(cameraLocalTransform)
    if (cameraParent != None):
        cameraWorldTransform.add_self_to_other(cameraParent.worldTransform)

    frame= np.ones((pg3d_rendering.renderConfig.screenWidth, pg3d_rendering.renderConfig.screenHeight, 3)).astype('uint8')
    z_buffer = np.zeros((pg3d_rendering.renderConfig.screenWidth, pg3d_rendering.renderConfig.screenHeight)) # start with some SMALL value
    # the value is small because the z buffer stores values of 1/z, so 0 represents the largest depth possible (it would be 1/infinity)

    if (pg3d_rendering.renderConfig.backgroundMode == "skybox"):
        startY = int(m.dot_3d(np.asarray([0.0,-1.0,0.0]), cameraWorldTransform.forward) * pg3d_rendering.renderConfig.screenHeight)
        startY += pg3d_rendering.renderConfig.screenHeight

        # initialize the frame
        for x in range(pg3d_rendering.renderConfig.screenWidth):
            for y in range(pg3d_rendering.renderConfig.screenHeight):
                frame[x,y] = sky_texture[x,startY + y]

    elif (pg3d_rendering.renderConfig.backgroundMode == "solid color"):
        frame[:,:] = skyColor * 255
   
    # draw the frame
    for model in Model._registry:
        if (model.shouldBeDrawn):
            # this function will move the points so that they are centered around the camera
            # basically, handling the camera position/rotation stuff
            transform_points(model, model.points, cameraWorldTransform)
            # this function will project the triangles onto the screen, and draw them
            pg3d_rendering.draw_model(model, frame, model.points, model.triangles, cameraWorldTransform, light_dir, z_buffer,
                        model.texture_uv, model.texture_map, model.texture, model.color, model.textureType)
    
    return frame

def drawScreen(frame):
    # turn the frame into a surface
    surf = pg.transform.scale(pg.surfarray.make_surface(frame),(pg3d_rendering.renderConfig.screenWidth_actual,pg3d_rendering.renderConfig.screenHeight_actual))
    # blit that (draw it) onto the screen
    pg.display.get_surface().blit(surf, (0,0))
    
def update_display():
    pg.display.update()

def quit():
    pg.quit()

def setGravity(a):
    global gravityCoefficient
    gravityCoefficient = a

def setWireframeColor(r,g,b):
    global wireframeColor
    wireframeColor = constructColor(r,g,b)

def setCameraPosition(x,y,z):
    global cameraLocalTransform

    cameraLocalTransform.position = np.asarray([x,y,z])

# how much has the cursor changed since last frame?
# this is thankfully already a variable
def getCursorChange():
    return mouseChange

# called from update(), user should NOT call this
def updateCursor():
    global mousePos
    global mouseChange
    global mouseOffset
   
    if (pg.mouse.get_pos()[0] < 10 or pg.mouse.get_pos()[0] > pg3d_rendering.renderConfig.screenWidth - 10 or pg.mouse.get_pos()[1] < 10 or pg.mouse.get_pos()[1] > pg3d_rendering.renderConfig.screenHeight - 10):
        mouseOffset[0] += pg.mouse.get_pos()[0] - pg3d_rendering.renderConfig.screenWidth/2
        mouseOffset[1] += pg.mouse.get_pos()[1] - pg3d_rendering.renderConfig.screenHeight/2
        pg.mouse.set_pos(pg3d_rendering.renderConfig.screenWidth/2,pg3d_rendering.renderConfig.screenHeight/2)
    mouseChange = m.subtract_2d(mouse_position(), mousePos)
    mousePos = mouse_position()

# there's an offset here because the engine allows the mouse position to be off screen
# its explained at the top of this script I think
def mouse_position():
    return pg.mouse.get_pos() + mouseOffset

def updateCamera_freecam(move_speed):
    global cameraLocalTransform
    global timeSinceLastFrame

    pressed_keys = pg.key.get_pressed()
    if pressed_keys[ord('w')]:
        forward = cameraWorldTransform.forward
        cameraLocalTransform.position[0] += forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * move_speed * timeSinceLastFrame
    elif pressed_keys[ord('s')]:
        forward = cameraWorldTransform.forward
        cameraLocalTransform.position[0] -= forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * move_speed * timeSinceLastFrame
    if pressed_keys[ord('a')]:
        forward = cameraWorldTransform.get_right()
        cameraLocalTransform.position[0] += forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * move_speed * timeSinceLastFrame
    elif pressed_keys[ord('d')]:
        forward = cameraWorldTransform.get_right()
        cameraLocalTransform.position[0] -= forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * move_speed * timeSinceLastFrame
    if pressed_keys[ord('e')]:
        forward = cameraWorldTransform.up
        cameraLocalTransform.position[0] += forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * move_speed * timeSinceLastFrame
    elif pressed_keys[ord('q')]:
        forward = cameraWorldTransform.up
        cameraLocalTransform.position[0] -= forward[0] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * move_speed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * move_speed * timeSinceLastFrame

    xChange = mouseChange[0]
    yChange = mouseChange[1]

    rotate_camera(cameraLocalTransform.up,xChange * -0.001)
    rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001)

# changing how far the camera can tilt up/down
def firstPerson_setCameraRestrictions(min_angle, max_angle):
    global firstPerson_camera_max_dot
    global firstPerson_camera_min_dot

    firstPerson_camera_max_dot = np.cos(max_angle)
    firstPerson_camera_min_dot = np.cos(min_angle)

# a built-in first person controller, including jumping
# ONLY BEEN TESTED WITH A PS5 CONTROLLER!
def updateCamera_firstPerson_controller(move_speed, mouse_sensitivity, enable_movement, jump_force, joystick_deadband):
    global cameraLocalTransform
    global cameraWorldTransform
    global cameraParent

    global timeSinceLastFrame # an attempt to make movement speed constant regardless of framerate

    # these both default to 0.5
    global firstPerson_camera_max_dot
    global firstPerson_camera_min_dot

    # no parent, no controller
    if (cameraParent == None):
        return
    
    if (enable_movement):
        rawF = cameraWorldTransform.forward
        f = m.normalize_3d(m.subtract_3d(rawF, project_3d(rawF, np.asarray([0.0,1.0,0.0]))))
        r = cameraWorldTransform.get_right()

        joystickY = get_first_joystick_left_y(joystick_deadband) * move_speed
        joystickX = get_first_joystick_left_x(joystick_deadband) * move_speed
        cameraParent.add_local_position(-f[0] * joystickY, -f[1] * joystickY, -f[2] * joystickY)
        cameraParent.add_local_position(r[0] * -joystickX, r[1] * -joystickX, r[2] * -joystickX)

        # jump is the bottom button (cross for PS5)
        if (get_first_joystick_cross()):
            if (cameraParent.is_colliding()):
                cameraParent.add_local_position(0.0,0.1,0.0)
                cameraParent.add_velocity(0.0,jump_force,0.0)

    # rotating the camera ***********************************
    xChange = get_first_joystick_right_x(0.1)
    yChange = get_first_joystick_right_y(0.1)

    # you HAVEE to call camera_right() again to deal with the result of the first rotation
    # otherwise, weird things happen that aren't fun
    rotate_camera(np.asarray([0.0,1.0,0.0]),xChange * -0.001 * mouse_sensitivity)
    
    newUp = m.rotate_vector_3d(cameraWorldTransform.up, cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)

    # respecting camera tilt restrictions
    # actually this is looking up, cuz pygame is weird 
    if (yChange < 0):
        if (m.dot_3d(newUp, np.asarray([0.0,1.0,0.0])) > firstPerson_camera_max_dot):
            rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)
    else: # looking down
        if (m.dot_3d(newUp, np.asarray([0.0,1.0,0.0])) > firstPerson_camera_min_dot):
            rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)
    # ***********************************

def updateCamera_firstPerson(move_speed, mouse_sensitivity, enable_movement, jump_force):
    global cameraLocalTransform
    global cameraWorldTransform
    global cameraParent

    global timeSinceLastFrame # an attempt to make movement speed constant regardless of framerate

    # these both default to 0.5
    global firstPerson_camera_max_dot
    global firstPerson_camera_min_dot

    if (cameraParent == None):
        # no parent, no controller
        return
    
    # movement 
    if (enable_movement):
        rawF = cameraWorldTransform.forward
        f = m.normalize_3d(m.subtract_3d(rawF, project_3d(rawF, np.asarray([0.0,1.0,0.0]))))
        r = cameraWorldTransform.get_right()

        pressed_keys = pg.key.get_pressed()
        if pressed_keys[ord('w')]:
            cameraParent.add_local_position(f[0] * timeSinceLastFrame * move_speed,f[1] * timeSinceLastFrame * move_speed,f[2] * timeSinceLastFrame * move_speed)
        elif pressed_keys[ord('s')]:
            cameraParent.add_local_position(-f[0] * timeSinceLastFrame * move_speed,-f[1] * timeSinceLastFrame * move_speed,-f[2] * timeSinceLastFrame * move_speed)
        if pressed_keys[ord('a')]:
            cameraParent.add_local_position(r[0] * timeSinceLastFrame * move_speed,r[1] * timeSinceLastFrame * move_speed,r[2] * timeSinceLastFrame * move_speed)
        elif pressed_keys[ord('d')]:
            cameraParent.add_local_position(-r[0] * timeSinceLastFrame * move_speed,-r[1] * timeSinceLastFrame * move_speed,-r[2] * timeSinceLastFrame * move_speed)

        if pressed_keys[ord(' ')]:
            # only allow jumping if the player is colliding
            # since I'm not checking for specifically the ground it's possible to jump into a ceiling and keep jumping
            # fingers crossed this doesn't become an issue
            if (cameraParent.is_colliding()):
                cameraParent.add_local_position(0.0,0.1,0.0)
                cameraParent.add_velocity(0.0,jump_force,0.0)

    # rotating the camera ***********************************
    xChange = mouseChange[0]
    yChange = mouseChange[1]

    # you HAVEE to call camera_right() again to deal with the result of the first rotation
    # otherwise, weird things happen that aren't fun
    rotate_camera(np.asarray([0.0,1.0,0.0]),xChange * -0.001 * mouse_sensitivity)
    
    newUp = m.rotate_vector_3d(cameraWorldTransform.up, cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)

    # respecting camera tilt restrictions
    # actually this is looking up, cuz pygame is weird 
    if (yChange < 0):
        if (m.dot_3d(newUp, np.asarray([0.0,1.0,0.0])) > firstPerson_camera_max_dot):
            rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)
    else: # looking down
        if (m.dot_3d(newUp, np.asarray([0.0,1.0,0.0])) > firstPerson_camera_min_dot):
            rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001 * mouse_sensitivity)
    # ***********************************


def resetCameraRotation():
    cameraLocalTransform.up = np.asarray([0.0,1.0,0.0])
    cameraLocalTransform.forward = np.asarray([0.0,0.0,1.0])

def setBackGroundColor(r,g,b):
    global skyColor
    skyColor = np.asarray([r/255,g/255,b/255])

    for x in range(pg3d_rendering.renderConfig.screenWidth):
        for y in range(pg3d_rendering.renderConfig.screenHeight * 3):
            texColor = sky_texture[x,y]
            sky_texture[x,y] = np.asarray([texColor[0] * skyColor[0], texColor[1] * skyColor[1], texColor[2] * skyColor[2]])

# ********   OBJECT functions:     ********

# ********   cube:     ********
def spawnCube(name, x,y,z, tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/cube_no-net.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)

    return newObj

def spawnScaledCube(name, x,y,z, scale_x,scale_y,scale_z, tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/cube.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

def spawnCubeWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/cube.obj', texture_path,tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

# ********   plane:     ********
def spawnPlane(name,x,y,z,tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/plane.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    return newObj

def spawnScaledPlane(name,x,y,z,scale_x,scale_y,scale_z,tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/plane.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

def spawnPlaneWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/plane.obj', texture_path,tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

# ********   sphere:     ********
def spawnSphere(name,x,y,z,tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)

    return newObj

def spawnScaledSphere(name,x,y,z, scale_x,scale_y,scale_z,tags):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

def spawnSphereWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    newObj = Model(objName,'pg3d_assets/sphere.obj', texture_path,tags, Color.WHITE)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

def getObjectIndex(name):
    counter = 0
    for i in Model._registry:
        if (i.name == name):
            return counter
        counter += 1


def destroyObjectWithName(objectName):
    global cameraParent

    # I REALLY want to avoid goofy heirarchy logic here, so any children of the object will have their parent set as none
    # regardless if this object was itself a child or not
    obj = getObject(objectName)
    for i in range(len(obj.children)):
        obj.children[i].setParent(None)

    # not quite as simple as removing it from the registry, even though that's step 1
    objIndex = getObjectIndex(objectName)
    Model._registry.pop(objIndex)

    # that's because some levels might still have a reference to the object
    for i in Level._registry:
        indexInLevel = index_in_array(i.objectNames, objectName)

        if (indexInLevel != -1):
            i.objectNames.pop(indexInLevel)
        
    # also, the camera parent might have a reference to it as well
    if (cameraParent.name == objectName):
        cameraParent = None

def destroyObject(obj):
    global cameraParent

    # I REALLY want to avoid goofy heirarchy logic here, so any children of the object will have their parent set as none
    # regardless if this object was itself a child or not
    for i in range(len(obj.children)):
        obj.children[i].setParent(None)

    # not quite as simple as removing it from the registry, even though that's step 1
    objIndex = getObjectIndex(obj.name)
    Model._registry.pop(objIndex)

    # that's because some levels might still have a reference to the object
    for i in Level._registry:
        indexInLevel = index_in_array(i.objectNames, obj.name)

        if (indexInLevel != -1):
            i.objectNames.pop(indexInLevel)
        
    # also, the camera parent might have a reference to it as well
    if (cameraParent.name == obj.name):
        cameraParent = None

def destroyAllObjects():
    length = len(Model._registry)
    for i in range(length):
        j = Model._registry[length - 1 - i]
        # this function should deal with all parent/camera parent stuff
        # aka making sure we don't leave any null references
        destroyObject(j)

def destroyAllObjectsWithTag(tag):
    length = len(Model._registry)
    for i in range(length):
        j = Model._registry[length - 1 - i]
        if (j.hasTag(tag)):
            # this function should deal with all parent/camera parent stuff
            # aka making sure we don't leave any null references
            destroyObject(j)

# this should be changed to not use names
def destroyAllObjectsInLevel(levelName):
    levelData = getLevel(levelName)
    for i in levelData.objectNames:
        destroyObjectWithName(i)

def spawnObjectWithTexture(objPath, texturePath, name, x, y, z, tags, color):
    if (getFirstIndex(name, '(') < len(name)): # object names may NOT have parentheses!
        return
    name = nameModel(name)
    newObj = Model(name,objPath, texturePath,tags,color)

    newObj.set_local_position(x,y,z)

    return newObj

def spawnScaledObjectWithTexture(objPath, texturePath, name, x, y, z, scale_x, scale_y, scale_z, tags, color):
    if (getFirstIndex(name, '(') < len(name)): # object names may NOT have parentheses!
        return
    name = nameModel(name)
    newObj = Model(name,objPath, texturePath,tags,color)

    newObj.set_local_position(x,y,z)
    newObj.set_scale(scale_x,scale_y,scale_z)

    return newObj

def spawnObjectWithTexture(objPath, texturePath, name, x, y, z, tags, color):
    if (getFirstIndex(name, '(') < len(name)): # object names may NOT have parentheses!
        return
    name = nameModel(name)
    newObj = Model(name,objPath, texturePath,tags,color)

    newObj.set_local_position(x,y,z)

    return newObj

def spawnObjectWithColor(objPath, name, x, y, z, tags, colorR, colorG, colorB):
    if (getFirstIndex(name, '(') < len(name)):
        return
    name = nameModel(name)
    newObj = Model(name,objPath, '',tags,np.asarray([colorR,colorG,colorB]).astype('uint8'))

    newObj.set_local_position(x,y,z)

    return newObj

def getObjectsWithTag(tag):
    toReturn = []
    for i in Model._registry:
        if (i.hasTag(tag)):
            toReturn.append(i)

    return toReturn

# makes sure that all objects have unique names by adding (1),(2),(3) to a name
def nameModel(attemptedName):
    objectCount = 0
    for i in Model._registry:
        if (namesMatch(attemptedName,i.name)):
            objectCount += 1

    if (objectCount > 0):
        return attemptedName + "(" + str(objectCount) + ")"
    else:
        return attemptedName

def getObject(name):
    for i in Model._registry:
        if (i.name == name):
            return i

    # originally I had the model at index 0 as the null value
    # I have since learned that python actually has a null type
    return None
    
def namesMatch(a,b):
    aOpenIndex = getFirstIndex(a, '(')
    bOpenIndex = getFirstIndex(b,'(')

    if (aOpenIndex != bOpenIndex):
        return False

    # we IGNORE the parentheses
    for i in range(0,aOpenIndex):
        if (a[i] != b[i]):
            return False
        
    return True
    
# ********  UI functions! (the annoying stuff)       ********

# draw a rectangle on the screen
def draw_rect(frameArray, xPos, yPos, xSize, ySize, color):
    minX = int(xPos-xSize/2)
    maxX = int(xPos+xSize/2)

    minY = int(yPos-ySize/2)
    maxY = int(yPos+ySize/2)
    
    for x in range(max(0,minX),min(pg3d_rendering.renderConfig.screenWidth-1,maxX)):
        for y in range(max(0,minY),min(pg3d_rendering.renderConfig.screenHeight-1,maxY)):
            frameArray[x,y] = color.astype('uint8')

    return frameArray

# draw a circle on the screen
def draw_circle(frameArray, xPos, yPos, radius, color):
    minX = int(xPos - radius)
    maxX = int(xPos + radius)

    minY = int(yPos - radius)
    maxY = int(yPos + radius)
    
    for x in range(max(0,minX),min(pg3d_rendering.renderConfig.screenWidth-1,maxX)):
        for y in range(max(0,minY),min(pg3d_rendering.renderConfig.screenHeight-1,maxY)):
            if ((x - xPos) * (x - xPos) + (y - yPos) * (y - yPos) < radius * radius):
                frameArray[x,y] = color.astype('uint8')

    return frameArray

# pygame has built-in text rendering, 
# but the advantage here is that it syncs with the display resolution

# so that way, you don't get high-res fonts with a low-res display which would look weird
# it's style, that's it
def draw_text(xPos, yPos, color, text_string):
    xOffset = 0

    for i in text_string:
        rawImg = pg.image.load("pg3d_assets/font/" + i + "_l" + ".png")

        w = rawImg.get_width()
        h = rawImg.get_height()

        xOffset += w*4 + 10

        letterImg = pg.transform.scale(rawImg, (w*4, h*4))

        pg.display.get_surface().blit(letterImg, (xPos + xOffset,yPos))


# ********  drawing functions! (the annoying stuff)       ********  

# this function will move the points so that they are centered around the camera
def transform_points(mesh, points, cameraTransform):
    # first, go through the points to figure out where the point is in world space
    # (using the mesh's transforms)
    for i in points:
        j = mesh.transform_point(i)

        i[3] = j[3]
        i[4] = j[4]
        i[5] = j[5]

    # the rest of this function turns the world=relative points into camera-relative points

    # translate to have camera as origin
    points[:,3] -= cameraTransform.position[0]
    points[:,4] -= cameraTransform.position[1]
    points[:,5] -= cameraTransform.position[2]

    camZ = cameraTransform.forward
    forwardVectorAxis = m.normalize_3d(m.cross_3d(camZ,np.asarray([0.0,0.0,1.0])))
    forwardVectorAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]),camZ)

    if (forwardVectorAngle > 0):
        for i in points:
            j = m.rotate_point_3d(i, forwardVectorAxis, forwardVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]
    else:
        forwardVectorAxis = camZ

    upVectorAxis = m.normalize_3d(m.cross_3d(m.rotate_vector_3d(cameraTransform.up,forwardVectorAxis,forwardVectorAngle),np.asarray([0.0,1.0,0.0])))
    upVectorAngle = m.angle_3d(np.asarray([0.0,1.0,0.0]), m.rotate_vector_3d(cameraTransform.up,forwardVectorAxis,forwardVectorAngle))

    if (upVectorAngle > 0):
        for i in points:
            j = m.rotate_point_3d(i, upVectorAxis, upVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]

    # this will be used for projection
    hor_fov_adjust = 0.5*pg3d_rendering.renderConfig.screenWidth/ np.tan(pg3d_rendering.renderConfig.horizontalFOV * 0.5) 
    ver_fov_adjust = 0.5*pg3d_rendering.renderConfig.screenHeight/ np.tan(pg3d_rendering.renderConfig.verticalFOV * 0.5)
    
    # the projected points are stored in indices 6,7,8 so as to not overwrite the other sets of points
    points[:,6] = (-hor_fov_adjust*points[:,3]/np.abs(points[:,5]) + 0.5*pg3d_rendering.renderConfig.screenWidth).astype(np.int32)
    points[:,7] = (-ver_fov_adjust*points[:,4]/np.abs(points[:,5]) + 0.5*pg3d_rendering.renderConfig.screenHeight).astype(np.int32)
    points[:,8] = points[:,5]

    # there's no need to return anything here, because we're just modifying the array we were given
    
# drawing the box that represents a collider (or trigger)
# triggers are drawn in RED, colliders in GREEN, for now
# z-buffering is not used here because draw_triangle() is called with the wireframe mode
def draw_box_collider(isTrigger, worldPosition, sizes):
    global screenWidth
    global screenHeight

    global horizontalFOV
    global verticalFOV

    global wireframeColor
    if (isTrigger):
        wireframeColor = constructColor(255,0,0)
    else:
        wireframeColor = constructColor(0,255,0)

    # TODO: convert the box into triangles, and draw it

def draw_sphere_collider(isTrigger, worldPosition, radius):
    global screenWidth
    global screenHeight

    global horizontalFOV
    global verticalFOV

    global wireframeColor
    if (isTrigger):
        wireframeColor = constructColor(255,0,0)
    else:
        wireframeColor = constructColor(0,255,0)

    # TODO: how do I draw a sphere???
  
# rotate the camera by an axis and angle
# re-defines the forward and up vectors, basically
def rotate_camera(axis,angle):
    up = cameraLocalTransform.up
    forward = cameraLocalTransform.forward

    # new local vectors
    upNew = m.rotate_vector_3d(up,axis,angle)
    forwardNew = m.rotate_vector_3d(forward,axis,angle)

    # assinging the camera vectors
    cameraLocalTransform.forward[0] = forwardNew[0]
    cameraLocalTransform.forward[1] = forwardNew[1]
    cameraLocalTransform.forward[2] = forwardNew[2]

    cameraLocalTransform.up[0] = upNew[0]
    cameraLocalTransform.up[1] = upNew[1]
    cameraLocalTransform.up[2] = upNew[2]

# ********  string helpers:       ********
@njit()
def getFirstIndex(string, char):
    
    for i in range(len(string)):
        if (string[i] == char):
            return i
    
    return len(string)

# based on who is in what level, update which models sould render and which should not
# THE ENGINE DOES NOT LOOP THROUGH LEVELS, it just checks the shouldBeRendered var for each model
# this is to avoid duplicate models, and performance loss
def refreshRenderBooleans():
    # loop through all levels, and set their object's boolean variables to the level's variable
    for i in Level._registry:
        for j in i.objectNames:
            getObject(j).shouldBeDrawn = i.isActive
            getObject(j).shouldBePhysics = i.isActive

    # "solo" objects will be left alone with whatever their variable is

# if you don't want to call level.addObject() for whatever reason, here's another option
def addObjectToLevel(object, levelName):
    getLevel(levelName).addObject(object.name)

# TODO: make sure levels don't have the same name!!
# also some functions for advancing to the next level?

# show ONE SPECIFIC LEVEL, hide all others
def switchToLevel(levelName):
    # hide any levels that don't match the name, show the one that does
    for i in Level._registry:
        if (i.name == levelName):
            i.show()
        else: 
            i.hide()

def switchToNextLevel():
    # finding the level that's loaded currently
    counter = 0
    loadedLevelIndex = -1
    for i in Level._registry:
        if (i.isActive):
            if (loadedLevelIndex != -1):
                return # if multiple levels are loaded, we have no idea what the next one is so do nothing
            
            loadedLevelIndex = counter
            i.hide()
            # no break statement here, because we need to check for multiple levels
        else:
            if (counter != -1):
                i.show()
                return
        
        counter += 1

# create a new level with a name
def createLevel(levelName):
    Level(levelName, [])

    # return a value so you can store the level class in a script
    return getLevel(levelName)

# same as above, but passing in an array of object names
def createLevelWithobjects(levelName, objectNames):
    Level(levelName, objectNames)

    # return a value so you can store the level class in a script
    return getLevel(levelName)

# grab a level class using the name
def getLevel(levelName):
    for i in Level._registry:
        if (i.name == levelName):
            return i

def index_in_array(array, item):
    counter = 0
    for i in array:
        if (i == item):
            return counter
        counter += 1
        
    return -1

# I don't like typing out the np.asarray([]) function, so this one makes colors a bit less verbose
def constructColor(r,g,b):
    return np.asarray([r,g,b]).astype('uint8')
    
# project vector a onto vector b (3D)
def project_3d(a,b):
    bLength = m.length_3d(b)

    coefficient = m.dot_3d(a,b) / (bLength * bLength)

    return np.asarray([b[0] * coefficient,b[1] * coefficient,b[2] * coefficient])

# project vector a onto vector b (2D)
def project_2d(a,b):
    bLength = m.length_2d(b)

    coefficient = m.dot_2d(a,b) / (bLength * bLength)

    return np.asarray(b[0] * coefficient,b[1] * coefficient)
    
# Essentially shorthand for common colors, to make code more readable
# these shouldn't be changing, so they're all constants
# orange was just a color I made in paint, hence the specific numbers
class Color:
    WHITE_01 = np.asarray([1,1,1]).astype('float32')

    RED_01 = np.asarray([1,0,0]).astype('float32')
    GREEN_01 = np.asarray([0,1,0]).astype('float32')
    BLUE_01 = np.asarray([0,0,1]).astype('float32')

    YELLOW_01 = np.asarray([1,1,0]).astype('float32')
    CYAN_01 = np.asarray([0,1,1]).astype('float32')
    MAGENTA_01 = np.asarray([1,0,1]).astype('float32')

    ORANGE_01 = np.asarray([1,0.592156862745098,0.1882352941176471]).astype('float32')

    WHITE = np.asarray([255,255,255]).astype('uint8')

    RED = np.asarray([255,0,0]).astype('uint8')
    GREEN = np.asarray([0,255,0]).astype('uint8')
    BLUE = np.asarray([0,0,255]).astype('uint8')

    YELLOW = np.asarray([255,255,0]).astype('uint8')
    MAGENTA = np.asarray([255,0,255]).astype('uint8')
    CYAN = np.asarray([0,255,255]).astype('uint8')

# helpers, so you don't have to write stuff like np.asarray([])
# like colors, these are constants, because they dont ever change
# i dont like typing capitals, why can't I just have lowercase constants?
class Vector3:
    # unity-like naming convention ************************************************************
    ONE = np.asarray([1.0,1.0,1.0])
    ZERO = np.asarray([0.0,0.0,0.0])

    FORWARD = np.asarray([0.0,0.0,1.0])
    BACKWARD = np.asarray([0.0,0.0,-1.0])

    # left is positive, because PG3D uses a left-handed coordinate system
    LEFT = np.asarray([1.0,0.0,0.0])
    RIGHT = np.asarray([-1.0,0.0,0.0])

    UP = np.asarray([0.0,1.0,0.0])
    DOWN = np.asarray([0.0,-1.0,0.0])
    # ************************************************************

    # alternative names: ************************************************************
    X_POSITIVE = np.asarray([1.0,0.0,0.0])
    X_NEGATIVE = np.asarray([-1.0,0.0,0.0])

    Y_POSITIVE = np.asarray([0.0,1.0,0.0])
    Y_NEGATIVE = np.asarray([0.0,-1.0,0.0])

    Z_POSITIVE = np.asarray([0.0,0.0,1.0])
    Z_NEGATIVE = np.asarray([0.0,0.0,-1.0])
    # ************************************************************

    def new(x,y,z):
        return np.asarray([x,y,z])
class Vector2:
    # unity-like naming convention ************************************************************
    ONE = np.asarray([1.0,1.0])
    ZERO = np.asarray([0.0,0.0])
 
    # in 3D it's left = positive, but here it's right = positive
    # why? idk
    LEFT = np.asarray([-1.0,0.0])
    RIGHT = np.asarray([1.0,0.0])

    UP = np.asarray([0.0,1.0])
    DOWN = np.asarray([0.0,-1.0])
    # ************************************************************

    # alternative names: ************************************************************
    X_POSITIVE = right = np.asarray([1.0,0.0])
    X_NEGATIVE = np.asarray([-1.0,0.0])

    Y_POSITIVE = np.asarray([0.0,1.0])
    Y_NEGATIVE = np.asarray([0.0,-1.0])

    # ************************************************************

    def new(x,y):
        return np.asarray([x,y]) 
    
# I'm not implementing full object heirarchy (because of the transformation issues that that causes)
# instead, objects are grouped into levels
# you cannot move, rotate, or scale a level
# but you can enable/disable them, which allows you to make a platformer or puzzle game or something with multiple stages
# you spawn objects OUTSIDE of a level, just by calling the spawnObject() function
# moving an object inside a level is just a matter of calling level.addObject(), passing in the object class

# can you add one object to multiple levels? yes. not sure what to do abt that
class Level:
    _registry = []

    # the name of the level
    name = ""

    # the names of the objects in the level
    objectNames = []

    # whether to render all the objects in the level
    # the check against this variable is done inside of getFrame()

    # DO NOT EDIT THIS MANUALLY, use the show() and hide() functions!
    isActive = True

    def __init__(self, name, objNames):
        self.name = name
        self.objectNames = objNames

        # add to the universal list
        self._registry.append(self)

    def show(self):
        self.isActive = True
        refreshRenderBooleans()  # calling this function only when a change is made, for performance reasons

    def hide(self):
        self.isActive = False
        refreshRenderBooleans() # calling this function only when a change is made, for performance reasons

    def addObject(self, objName):
        if (not m.array_has_item(self.objectNames, objName)):
            self.objectNames.append(objName)

# more helpers
class Rotation:
    DEG_TO_RAD = np.pi / 180
    RAD_TO_DEG = 180 / np.pi

    def toRadians(deg):
        return deg * np.pi / 180
    
    def toDegrees(rad):
        return rad * 180 / np.pi