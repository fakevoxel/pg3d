# rendering code was written by FINFET, and heavily modified by me
# (by that I mean I rewrote everything because FINFET didn't implement triangle clipping)

import pygame as pg
import numpy as np
from numba import njit
import random
from .pg3d_model import Model
from . import pg3d_math as m

# just to keep track of things, not actually used in code
version = "0.1"

# these are the default values for the screen
# they aren't gonna do anything, because the user passes their own values when they call init()
screenWidth = 400
screenHeight = 300
screenWidth_actual = 800
screenHeight_actual = 600
verticalFOV = np.pi / 4
horizontalFOV = verticalFOV*screenWidth/screenHeight

# this is the default sky color, but can be set using setSkyColor()
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
# position (x,y,z), forward (x,y,z), up (x,y,z)
# the right vector is NOT defined/kept track of because it's unecessary, knowing the other two is enough
# why is the right vector the one that's ommited? idk
camera = np.asarray([0.0, 0.0, 0.0,       0.0, 0.0, 1.0,      0.0, 1.0, 0.0])

# object parenting is not supported, but CAMERA parenting is (bc im lazy)
cameraParent = None
cameraLocalOffset = np.asarray([0.0,0.0,0.0])

# this amounts to nothing, because skybox rendering is not supported
backgroundMode = "solid color"
backGroundModes = ["solid color","skybox"]

# this actually DOES change stuff, you can choose to show uv coords if you want to debug stuff
renderingMode = "texture"
# the color that the wireframe renderer uses
# this is NOT passed into draw_triangle(), instead it can be set before calling
wireframeColor = np.asarray([255,0,0]).astype('uint8')
renderingModes = ["texture","uv","wireframe"]

physicsEnabled = False
backfaceCulling = True

sky_texture = None

# ********      main engine functions:     ********   
def init(w, h, wActual, hActual, ver):
    global screenWidth
    global screenHeight
    global verticalFOV
    global horizontalFOV

    global screenWidth_actual
    global screenHeight_actual

    global camera
    global clock

    global hor_fov_adjust
    global ver_fov_adjust

    global sky_texture

    screenWidth = w
    screenHeight = h
    
    screenWidth_actual = wActual
    screenHeight_actual = hActual

    verticalFOV = ver * np.pi / 180
    horizontalFOV = verticalFOV*screenWidth/screenHeight
    
    sky_texture = np.zeros((screenWidth, screenHeight * 3, 3)).astype('uint8')
    pg.surfarray.surface_to_array(sky_texture, pg.transform.scale(pg.image.load("pg3d_assets/sky_better.png"), (screenWidth, screenHeight * 3)))

    # gotta project those points
    hor_fov_adjust = 0.5*screenWidth/ np.tan(horizontalFOV * 0.5) 
    ver_fov_adjust = 0.5*screenHeight/ np.tan(verticalFOV * 0.5)

    # required for pygame to work properly
    pg.init()

    clock = pg.time.Clock()

    camera = np.asarray([0.0, 0.0, 0.0,       0.0, 0.0, 1.0,      0.0, 1.0, 0.0])

    pg.display.set_mode((screenWidth_actual, screenHeight_actual),pg.FULLSCREEN)

    pg.mouse.set_visible(0)
    pg.mouse.set_pos(screenWidth/2,screenHeight/2)

def disableBackfaceCulling():
    global backfaceCulling
    backfaceCulling = False

def enableBackfaceCulling():
    global backfaceCulling
    backfaceCulling = True

def enablePhysics():
    global physicsEnabled
    physicsEnabled = True

def disablePhysics():
    global physicsEnabled
    physicsEnabled = False

# used for camera controllers
def parentCamera(parentName, offX, offY, offZ):
    global cameraParent
    global cameraLocalOffset

    cameraParent = getObject(parentName)
    cameraLocalOffset = np.asarray([offX,offY,offZ])

def unParentCamera():
    global cameraParent
    cameraParent = None

def setRenderingMode(newMode):
    global renderingMode
    global renderingModes
    if (array_has_item(renderingModes, newMode)):
        renderingMode = newMode

def setBackgroundMode(newMode):
    global backgroundMode
    global backGroundModes
    if (array_has_item(backGroundModes, newMode)):
        backgroundMode = newMode

def update():
    global timeSinceLastFrame
    global clock
    global hasClockStarted

    global physicsEnabled
    global gravityCoefficient

    global cameraParent
    global cameraLocalOffset

    if (cameraParent != None):
        # the camera is parented, so move it to the position of the parent, plus an offset
        parentPosition = cameraParent.position
        camera[0] = parentPosition[0] + cameraLocalOffset[0]
        camera[1] = parentPosition[1] + cameraLocalOffset[1]
        camera[2] = parentPosition[2] + cameraLocalOffset[2]

    timeSinceLastFrame = clock.tick()*0.001

    if (not hasClockStarted):
        timeSinceLastFrame = 0
        hasClockStarted = True

    updateCursor()

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
                    i.add_position(closestPointOnThis[0] - desiredPoint[0],closestPointOnThis[1] - desiredPoint[1],closestPointOnThis[2] - desiredPoint[2])

                    # not a great permanent solution, but make the velocity 0 to make sure the collision stays resolved
                    i.set_velocity(0,0,0)

            i.add_position(i.linearVelocity[0] * timeSinceLastFrame,i.linearVelocity[1] * timeSinceLastFrame,i.linearVelocity[2] * timeSinceLastFrame)
                

def getFrame():
    global camera
    global skyColor

    global renderingMode

    # like a directional light in unity
    light_dir = np.asarray([0.0,1.0,0.0])
    light_dir = light_dir/np.linalg.norm(light_dir)

    frame= np.ones((screenWidth, screenHeight, 3)).astype('uint8')
    z_buffer = np.zeros((screenWidth, screenHeight)) # start with some SMALL value
    # the value is small because the z buffer stores values of 1/z, so 0 represents the largest depth possible (it would be 1/infinity)

    if (backgroundMode == "skybox"):
        startY = int(m.dot_3d(np.asarray([0.0,-1.0,0.0]), m.camera_forward(camera)) * screenHeight)
        startY += screenHeight

        # initialize the frame
        for x in range(screenWidth):
            for y in range(screenHeight):
                frame[x,y] = sky_texture[x,startY + y]

    elif (backgroundMode == "solid color"):
        frame[:,:] = skyColor * 255
   
    # draw the frame
    for model in Model._registry:
        if (model.shouldBeDrawn):
            # this function will move the points so that they are centered around the camera
            # basically, handling the camera position/rotation stuff
            transform_points(model, model.points, camera)
            # this function will project the triangles onto the screen, and draw them
            draw_model(model, frame, model.points, model.triangles, camera, light_dir, z_buffer,
                        model.texture_uv, model.texture_map, model.texture, model.color)
    
    return frame

def drawScreen(frame):
    # turn the frame into a surface
    surf = pg.transform.scale(pg.surfarray.make_surface(frame),(screenWidth_actual,screenHeight_actual))
    # blit that (draw it) onto the screen
    pg.display.get_surface().blit(surf, (0,0))
    pg.display.update()

def quit():
    pg.quit()

def setGravity(a):
    global gravityCoefficient
    gravityCoefficient = a

def setWireframeColor(r,g,b):
    global wireframeColor
    wireframeColor = constructColor(r,g,b)

# x,y,z is an offset
def moveCameraToObject(object, x, y, z):
    pos = object.position

    camera[0] = pos[0] + x
    camera[1] = pos[1] + y
    camera[2] = pos[2] + z

def setCameraPosition(x,y,z):
    global camera

    camera[0] = x
    camera[1] = y
    camera[2] = z

def updateCursor():
    global mousePos
    global mouseChange
    global mouseOffset
    global screenWidth
    global screenHeight
    if (pg.mouse.get_pos()[0] < 10 or pg.mouse.get_pos()[0] > screenWidth - 10 or pg.mouse.get_pos()[1] < 10 or pg.mouse.get_pos()[1] > screenHeight - 10):
        mouseOffset[0] += pg.mouse.get_pos()[0] - screenWidth/2
        mouseOffset[1] += pg.mouse.get_pos()[1] - screenHeight/2
        pg.mouse.set_pos(screenWidth/2,screenHeight/2)
    mouseChange = m.subtract_2d(mouse_position(), mousePos)
    mousePos = mouse_position()
def mouse_position():
    return pg.mouse.get_pos() + mouseOffset

def updateCamera_freecam(moveSpeed):
    global screenWidth
    global screenHeight

    global camera
    global timeSinceLastFrame

    pressed_keys = pg.key.get_pressed()
    if pressed_keys[ord('w')]:
        forward = m.camera_forward(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('s')]:
        forward = m.camera_forward(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('a')]:
        forward = m.camera_right(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('d')]:
        forward = m.camera_right(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('e')]:
        forward = m.camera_up(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('q')]:
        forward = m.camera_up(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame

    xChange = mouseChange[0]
    yChange = mouseChange[1]

    rotate_camera(camera,m.camera_up(camera),xChange * -0.001)
    rotate_camera(camera,m.camera_right(camera),yChange * 0.001)

def updateCamera_firstPerson(moveSpeed):
    global screenWidth
    global screenHeight

    global camera
    global cameraParent

    global timeSinceLastFrame

    if (cameraParent == None):
        # no parent, no controller
        return
    
    # movement 

    rawF = m.camera_forward(camera)
    f = m.subtract_3d(rawF, project_3d(rawF, np.asarray([0.0,1.0,0.0])))
    r = m.camera_right(camera)

    pressed_keys = pg.key.get_pressed()
    if pressed_keys[ord('w')]:
        cameraParent.add_position(f[0] * timeSinceLastFrame * moveSpeed,f[1] * timeSinceLastFrame * moveSpeed,f[2] * timeSinceLastFrame * moveSpeed)
    elif pressed_keys[ord('s')]:
        cameraParent.add_position(-f[0] * timeSinceLastFrame * moveSpeed,-f[1] * timeSinceLastFrame * moveSpeed,-f[2] * timeSinceLastFrame * moveSpeed)
    if pressed_keys[ord('a')]:
        cameraParent.add_position(r[0] * timeSinceLastFrame * moveSpeed,r[1] * timeSinceLastFrame * moveSpeed,r[2] * timeSinceLastFrame * moveSpeed)
    elif pressed_keys[ord('d')]:
        cameraParent.add_position(-r[0] * timeSinceLastFrame * moveSpeed,-r[1] * timeSinceLastFrame * moveSpeed,-r[2] * timeSinceLastFrame * moveSpeed)

    # rotation
    xChange = mouseChange[0]
    yChange = mouseChange[1]

    # you HAVEE to call camera_right() again to deal with the result of the first rotation
    # otherwise, weird things happen that aren't fun
    rotate_camera(camera,np.asarray([0.0,1.0,0.0]),xChange * -0.001)
    rotate_camera(camera,m.camera_right(camera),yChange * 0.001)

def resetCameraRotation():
    camera[3] = 0.0
    camera[4] = 0.0
    camera[5] = 1.0

    camera[6] = 0.0
    camera[7] = 1.0
    camera[8] = 0.0

def setBackGroundColor(r,g,b):
    global skyColor
    skyColor = np.asarray([r/255,g/255,b/255])

    for x in range(screenWidth):
        for y in range(screenHeight * 3):
            texColor = sky_texture[x,y]
            sky_texture[x,y] = np.asarray([texColor[0] * skyColor[0], texColor[1] * skyColor[1], texColor[2] * skyColor[2]])

# ********   OBJECT functions:     ********

# ********   cube:     ********
def spawnCube(x,y,z,tags):
    name = nameModel("cube")
    Model(name,'pg3d_assets/cube.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
def spawnScaledCube(x,y,z,sx,sy,sz,tags):
    name = nameModel("cube")
    Model(name,'pg3d_assets/cube.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
    getObject(name).set_scale(sx,sy,sz)

# ********   plane:     ********
def spawnPlane(x,y,z,tags):
    name = nameModel("plane")
    Model(name,'pg3d_assets/cube.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
def spawnScaledPlane(x,y,z,sx,sy,sz,tags):
    name = nameModel("plane")
    Model(name,'pg3d_assets/plane.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
    getObject(name).set_scale(sx,sy,sz)

# ********   sphere:     ********
def spawnSphere(x,y,z,tags):
    name = nameModel("sphere")
    Model(name,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
def spawnScaledSphere(x,y,z,sx,sy,sz,tags):
    name = nameModel("sphere")
    Model(name,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)
    getObject(name).set_scale(sx,sy,sz)

def getObjectIndex(name):
    counter = 0
    for i in Model._registry:
        if (i.name == name):
            return counter
        counter += 1


def destroyObject(objectName):
    global cameraParent
    global cameraLocalOffset

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
        cameraLocalOffset = np.asarray([0.0,0.0,0.0])

def spawnObjectWithTexture(objPath, texturePath, name, x, y, z, tags, color):
    if (getFirstIndex(name, '(') < len(name)): # object names may NOT have parentheses!
        return
    name = nameModel(name)
    Model(name,objPath, texturePath,tags,color)

    getObject(name).set_position(x,y,z)

def spawnObjectWithColor(objPath, name, x, y, z, tags, colorR, colorG, colorB):
    if (getFirstIndex(name, '(') < len(name)):
        return
    name = nameModel(name)
    Model(name,objPath, '',tags,np.asarray([colorR,colorG,colorB]).astype('uint8'))

    getObject(name).set_position(x,y,z)

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
    global screenWidth
    global screenHeight

    minX = int(xPos-xSize/2)
    maxX = int(xPos+xSize/2)

    minY = int(yPos-ySize/2)
    maxY = int(yPos+ySize/2)
    
    for x in range(max(0,minX),min(screenWidth-1,maxX)):
        for y in range(max(0,minY),min(screenHeight-1,maxY)):
            frameArray[x,y] = color.astype('uint8')

    return frameArray

# draw a circle on the screen
def draw_circle(frameArray, xPos, yPos, radius, color):
    global screenWidth
    global screenHeight

    minX = int(xPos - radius)
    maxX = int(xPos + radius)

    minY = int(yPos - radius)
    maxY = int(yPos + radius)
    
    for x in range(max(0,minX),min(screenWidth-1,maxX)):
        for y in range(max(0,minY),min(screenHeight-1,maxY)):
            if ((x - xPos) * (x - xPos) + (y - yPos) * (y - yPos) < radius * radius):
                frameArray[x,y] = color.astype('uint8')

    return frameArray

# ********  drawing functions! (the annoying stuff)       ********

@njit()
def rotate_point_3d(vector, axis, angle):
    # rotate around x axis
    i = np.asarray([0.0,0.0,0.0,0.0,0.0,0.0])
    i[3] = vector[3] * (     (axis[0] * axis[0]) * (1 - np.cos(angle)) + np.cos(angle)                  ) + vector[4] * (        (axis[1] * axis[0]) * (1 - np.cos(angle)) - (axis[2] * np.sin(angle))         ) + vector[5] * (        (axis[0] * axis[2]) * (1 - np.cos(angle)) + (axis[1] * np.sin(angle))     )
    i[4] = vector[3] * (     (axis[0] * axis[1]) * (1 - np.cos(angle)) + (axis[2] * np.sin(angle))     ) + vector[4] * (        (axis[1] * axis[1]) * (1 - np.cos(angle)) + np.cos(angle)                      ) + vector[5] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) - (axis[0] * np.sin(angle))     )
    i[5] = vector[3] * (     (axis[0] * axis[2]) * (1 - np.cos(angle)) - (axis[1] * np.sin(angle))     ) + vector[4] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) + (axis[0] * np.sin(angle))         ) + vector[5] * (        (axis[2] * axis[2]) * (1 - np.cos(angle)) + np.cos(angle)                  )
    
    return i   

# this function will move the points so that they are centered around the camera
def transform_points(mesh, points, camera):
    global screenWidth
    global screenHeight

    global horizontalFOV
    global verticalFOV

    # first, go through the points to figure out where the point is in world space
    # (using the mesh's transforms)
    for i in points:
        j = mesh.transform_point(i)

        i[3] = j[3]
        i[4] = j[4]
        i[5] = j[5]

    # the rest of this function turns the world=relative points into camera-relative points

    # translate to have camera as origin
    points[:,3] -= camera[0]
    points[:,4] -= camera[1]
    points[:,5] -= camera[2]

    camZ = m.camera_forward(camera)
    forwardVectorAxis = m.normalize_3d(m.cross_3d(camZ,np.asarray([0.0,0.0,1.0])))
    forwardVectorAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]),camZ)

    if (forwardVectorAngle > 0):
        for i in points:
            j = rotate_point_3d(i, forwardVectorAxis, forwardVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]
    else:
        forwardVectorAxis = camZ

    upVectorAxis = m.normalize_3d(m.cross_3d(m.rotate_vector_3d(m.camera_up(camera),forwardVectorAxis,forwardVectorAngle),np.asarray([0.0,1.0,0.0])))
    upVectorAngle = m.angle_3d(np.asarray([0.0,1.0,0.0]), m.rotate_vector_3d(m.camera_up(camera),forwardVectorAxis,forwardVectorAngle))

    if (upVectorAngle > 0):
        for i in points:
            j = rotate_point_3d(i, upVectorAxis, upVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]

    # this will be used for projection
    hor_fov_adjust = 0.5*screenWidth/ np.tan(horizontalFOV * 0.5) 
    ver_fov_adjust = 0.5*screenHeight/ np.tan(verticalFOV * 0.5)
    
    # the projected points are stored in indices 6,7,8 so as to not overwrite the other sets of points
    points[:,6] = (-hor_fov_adjust*points[:,3]/np.abs(points[:,5]) + 0.5*screenWidth).astype(np.int32)
    points[:,7] = (-ver_fov_adjust*points[:,4]/np.abs(points[:,5]) + 0.5*screenHeight).astype(np.int32)
    points[:,8] = points[:,5]

    # there's no need to return anything here, because we're just modifying the array we were given

# figuring out whether a triangle is in front of the camera (return 0), behind (return 1), or both (return 2, needs to be clipped)
def triangle_state(points, triangle):
    state0 = True
    state1 = True
    state2 = True
    if (points[triangle[0]][8] < 0):
        state0 = False
    if (points[triangle[1]][8] < 0):
        state1 = False
    if (points[triangle[2]][8] < 0):
        state2 = False

    if (state0 and state1 and state2):
        return 0 # all in front
    elif (not state0 and not state1 and not state2):
        return 1 # all behind
    else:
        return 2 # both
    
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

def draw_box_collider(isTrigger, worldPosition, radius):
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
    

# z-buffering is still used EVEN during wireframe
def draw_model(mesh, frame, points, triangles, camera, light_dir, z_buffer, texture_uv, texture_map, texture, color):
    global screenWidth
    global screenHeight

    global renderingMode

    global horizontalFOV
    global verticalFOV

    global hor_fov_adjust
    global ver_fov_adjust

    global backfaceCulling

    # for the first part of things, we're gonna use the set of points that's transformed to be camera-relative
    # in other words, indices 3,4 and 5

    # the size of the mesh's texture
    text_size = [len(texture)-1, len(texture[0])-1]
    for index in range(len(triangles)):
        
        triangle = triangles[index]

        # ******* STEP 1: *******
        # we have to figure out which triangles are behind the camera, in front of the camera, or both (some verts behind, some in front)

        # 0 if in front, 1 if behind, 2 if both
        triangleState = triangle_state(points, triangle)

        # only draw the triangle if state is 1, meaning entirely in front
        if (triangleState == 0):
            # ******* STEP 2: *******
            # once we've confirmed we're drawing the shape, we have to project it onto the screen

            # defining the points the triangle is made of
            projpoints = []
            projpoints.append(points[triangle[0]])
            projpoints.append(points[triangle[1]])
            projpoints.append(points[triangle[2]])
            # (the points have their projected versions stored as indices 6,7,8)

            # getting the depth values of each point (using 8, the projected depth)
            z0 = 1 / projpoints[0][8]
            z1 = 1 / projpoints[1][8]
            z2 = 1 / projpoints[2][8]
            # keep in mind that these are always positive here, because of the triangle state check

            # figuring out the uv coordinates of each point
            uv_points = texture_uv[texture_map[index]]
            uv_points[0], uv_points[1], uv_points[2] = uv_points[0]*z0, uv_points[1]*z1, uv_points[2]*z2

            # the bounding box that the triangle occupies
            minX = np.min([projpoints[0][6],projpoints[1][6],projpoints[2][6]])
            maxX = np.max([projpoints[0][6],projpoints[1][6],projpoints[2][6]])

            minY = np.min([projpoints[0][7],projpoints[1][7],projpoints[2][7]])
            maxY = np.max([projpoints[0][7],projpoints[1][7],projpoints[2][7]])

            draw_triangle(frame, z_buffer, texture, projpoints, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderingMode, np.asarray([0,255,0]), backfaceCulling)
        elif(triangleState == 2):
            # here, the triangle is both behind and in front, and we need to clip it

            # defining the points the triangle is made of
            projpoints = []
            projpoints.append(points[triangle[0]])
            projpoints.append(points[triangle[1]])
            projpoints.append(points[triangle[2]])
            # (the points have their projected versions stored as indices 6,7,8)

            # getting the depth values of each point (using 8, the projected depth)
            z0 = projpoints[0][8]
            z1 = projpoints[1][8]
            z2 = projpoints[2][8]
            # these are NOT always positive! at least one will be <0

            # ******* STEP 3: *******
            # this step only applies to type-2 triangles
            # we CANNOT, UNDER ANY CIRCUMSTANCES, render triangles behind the camera with our method
            # don't try.
            # instead:
            # we have to clip the triangle, and then render the new 1 or 2 triangles
            # these new triangles will be in front

            # in other words:
            # 1. figure out the problem vertices
            # 2. figure out where the line segments intersect the z-plane
            # 3. build new triangles, including things like uv coordinates
            # 4. feed those triangles to draw_triangle

            problemVertices = []
            goodVertices = []
            goodUV = []
            problemUV = []

            rawUVs = texture_uv[texture_map[index]]

            # add any <0 vertices to a list
            # using the same index convention as normal points
            if (z0 < 0):
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[0][3],projpoints[0][4],projpoints[0][5],projpoints[0][6],projpoints[0][7],projpoints[0][8]]))
                problemUV.append(rawUVs[0])
            else:
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[0][3],projpoints[0][4],projpoints[0][5],projpoints[0][6],projpoints[0][7],projpoints[0][8]]))
                goodUV.append(rawUVs[0])
            if (z1 < 0):
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[1][3],projpoints[1][4],projpoints[1][5],projpoints[1][6],projpoints[1][7],projpoints[1][8]]))
                problemUV.append(rawUVs[1])
            else:
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[1][3],projpoints[1][4],projpoints[1][5],projpoints[1][6],projpoints[1][7],projpoints[1][8]]))
                goodUV.append(rawUVs[1])
            if (z2 < 0):
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[2][3],projpoints[2][4],projpoints[2][5],projpoints[2][6],projpoints[2][7],projpoints[2][8]]))
                problemUV.append(rawUVs[2])
            else:
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[2][3],projpoints[2][4],projpoints[2][5],projpoints[2][6],projpoints[2][7],projpoints[2][8]]))
                goodUV.append(rawUVs[2])

            if (len(problemVertices) == 2):
                # first case, where two vertices are behind
                # here we will end up with one clipped triangle

                # getting the intersect point in camera-relative space
                # using 3, 4, 5 because we want cam-relative

                # here is our triangle as-is
                p1 = np.asarray([goodVertices[0][3],goodVertices[0][4],goodVertices[0][5]])
                p2 = np.asarray([problemVertices[1][3],problemVertices[1][4],problemVertices[1][5]])
                p3 = np.asarray([problemVertices[0][3],problemVertices[0][4],problemVertices[0][5]])

                parameter = (0.01 - p2[2]) / (p1[2] - p2[2])
                intersect1 = m.add_3d(p2, np.asarray([(p1[0]-p2[0]) * parameter,(p1[1]-p2[1]) * parameter,(p1[2]-p2[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[1][0] + (goodUV[0][0] - problemUV[1][0]) * parameter, problemUV[1][1] + (goodUV[0][1] - problemUV[1][1]) * parameter]))

                parameter = (0.01 - p3[2]) / (p1[2] - p3[2])
                intersect1 = m.add_3d(p3, np.asarray([(p1[0]-p3[0]) * parameter,(p1[1]-p3[1]) * parameter,(p1[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[0][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[0][1] - problemUV[0][1]) * parameter]))

                # the good vertices array will have items with ONLY SIX VALUES, representing the cam-relative points and then the projected points
                # however, right now the projected part is all zeros

                goodVertices[1][6] = (-hor_fov_adjust*goodVertices[1][3]/np.abs(goodVertices[1][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[1][7] = (-ver_fov_adjust*goodVertices[1][4]/np.abs(goodVertices[1][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[1][8] = goodVertices[1][5] 

                goodVertices[2][6] = (-hor_fov_adjust*goodVertices[2][3]/np.abs(goodVertices[2][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[2][7] = (-ver_fov_adjust*goodVertices[2][4]/np.abs(goodVertices[2][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[2][8] = goodVertices[2][5]     

                # the bounding box that the triangle occupies
                minX = np.min([goodVertices[0][6],goodVertices[1][6],goodVertices[2][6]])
                maxX = np.max([goodVertices[0][6],goodVertices[1][6],goodVertices[2][6]])

                minY = np.min([goodVertices[0][7],goodVertices[1][7],projpoints[2][7]])
                maxY = np.max([goodVertices[0][7],goodVertices[1][7],projpoints[2][7]])

                # new z values!
                z0 = 1 / goodVertices[0][8]
                z1 = 1 / goodVertices[1][8]
                z2 = 1 / goodVertices[2][8]

                goodUV[0] = goodUV[0] * z0
                goodUV[1] = goodUV[1] * z1
                goodUV[2] = goodUV[2] * z2

                # now that we have our three triangle points (not behind the camera anymore), we can draw them

                draw_triangle(frame, z_buffer, texture, goodVertices, goodUV, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderingMode, np.asarray([0,0,255]), backfaceCulling)
            elif (len(problemVertices) == 1):
                # here only one vertex is an issue
                # the procedure is similar, but we end up with two triangles

                # here is our triangle as-is
                p1 = np.asarray([goodVertices[0][3],goodVertices[0][4],goodVertices[0][5]])
                p2 = np.asarray([goodVertices[1][3],goodVertices[1][4],goodVertices[1][5]])
                p3 = np.asarray([problemVertices[0][3],problemVertices[0][4],problemVertices[0][5]])

                parameter = (0.01 - p3[2]) / (p1[2] - p3[2])
                intersect1 = m.add_3d(p3, np.asarray([(p1[0]-p3[0]) * parameter,(p1[1]-p3[1]) * parameter,(p1[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[0][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[0][1] - problemUV[0][1]) * parameter]))

                parameter = (0.01 - p3[2]) / (p2[2] - p3[2])
                intersect1 = m.add_3d(p3, np.asarray([(p2[0]-p3[0]) * parameter,(p2[1]-p3[1]) * parameter,(p2[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[1][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[1][1] - problemUV[0][1]) * parameter]))

                goodVertices[2][6] = (-hor_fov_adjust*goodVertices[2][3]/np.abs(goodVertices[2][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[2][7] = (-ver_fov_adjust*goodVertices[2][4]/np.abs(goodVertices[2][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[2][8] = goodVertices[2][5] 

                goodVertices[3][6] = (-hor_fov_adjust*goodVertices[3][3]/np.abs(goodVertices[3][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[3][7] = (-ver_fov_adjust*goodVertices[3][4]/np.abs(goodVertices[3][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[3][8] = goodVertices[3][5] 

                # this is where we have to turn our array of four points into two triangles

                good1 = np.asarray([goodVertices[0],goodVertices[2],goodVertices[1]])
                good2 = np.asarray([goodVertices[1],goodVertices[2],goodVertices[3]])

                # the bounding box that the triangle occupies
                minX1 = np.min([good1[0][6],good1[1][6],good1[2][6]])
                maxX1 = np.max([good1[0][6],good1[1][6],good1[2][6]])

                minY1 = np.min([good1[0][7],good1[1][7],good1[2][7]])
                maxY1 = np.max([good1[0][7],good1[1][7],good1[2][7]])

                minX2 = np.min([good2[0][6],good2[1][6],good2[2][6]])
                maxX2 = np.max([good2[0][6],good2[1][6],good2[2][6]])

                minY2 = np.min([good2[0][7],good2[1][7],good2[2][7]])
                maxY2 = np.max([good2[0][7],good2[1][7],good2[2][7]])

                # new z values!
                z01 = 1 / good1[0][8]
                z11 = 1 / good1[1][8]
                z21 = 1 / good1[2][8]

                z02 = 1 / good2[0][8]
                z12 = 1 / good2[1][8]
                z22 = 1 / good2[2][8]

                uv1 = np.asarray([goodUV[0] * z01,goodUV[2] * z11,goodUV[1] * z21])
                uv2 = np.asarray([goodUV[1] * z02,goodUV[2] * z12,goodUV[3] * z22])

                draw_triangle(frame, z_buffer, texture, good1, uv1, minX1, maxX1, minY1, maxY1, text_size, z01, z11, z21,renderingMode, np.asarray([255,0,0]), backfaceCulling)
                draw_triangle(frame, z_buffer, texture, good2, uv2, minX2, maxX2, minY2, maxY2, text_size, z02, z12, z22,renderingMode, np.asarray([255,0,0]), backfaceCulling)


        #  we do nothing if the triangle is all behind (state == 1), we just skip those

# z-buffering NOT used for wireframe, it is for the others though
@njit()
def draw_triangle(frame, z_buffer, texture, proj_points, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2, renderMode, color, cullBack):
    global screenWidth
    global screenHeight

    global wireframeColor
    
    # looping through every pixel in the bounding box that the triangle represents
    # we limit this box to the edges of the screen, because we don't care about anything else

    # because of these restrictions we don't need any further checks for making sure the x and y are valid
    for y in range(max(minY, 0), min(maxY, screenHeight)):
        for x in range(max(minX, 0), min(maxX, screenWidth)):
            apx = x - proj_points[0][6]
            apy = y - proj_points[0][7]
            
            bpx = x - proj_points[1][6]
            bpy = y - proj_points[1][7]
            
            cpx = x - proj_points[2][6]
            cpy = y - proj_points[2][7]

            # (y, -x) for c 90 deg rotation
            dotab = apx * (proj_points[1][7] - proj_points[0][7]) + apy * -(proj_points[1][6] - proj_points[0][6])
            dotbc = bpx * (proj_points[2][7] - proj_points[1][7]) + bpy * -(proj_points[2][6] - proj_points[1][6])
            dotca = cpx * (proj_points[0][7] - proj_points[2][7]) + cpy * -(proj_points[0][6] - proj_points[2][6])

            # line segments: 0 -> 1,    1 -> 2,        2 -> 0
            if ((dotab > 0) and (dotbc > 0) and (dotca > 0)):
                inTriangle = True
            elif ((dotab < 0) and (dotbc < 0) and (dotca < 0)):
                inTriangle = True
            else:
                inTriangle = False

            if (inTriangle):
                a0 = dotbc / 2
                a1 = dotca / 2
                a2 = dotab / 2
                
                invAreaSum = 1 / (a0 + a1 + a2)
                w0 = a0 * invAreaSum
                w1 = a1 * invAreaSum
                w2 = a2 * invAreaSum

                # sinze z0,z1, and z2 are all 1/z at some point, this value will also be 1 / z
                z = w0*z0 + w1*z1 + w2*z2
                u = ((w0*uv_points[0][0] + w1*uv_points[1][0] + w2*uv_points[2][0])*(1/z + 0.0001))
                v = ((w0*uv_points[0][1] + w1*uv_points[1][1] + w2*uv_points[2][1])*(1/z + 0.0001))

                # z needs to be greater than the value at the z buffer, meaning 1 / z needs to be less
                # also make sure the u and v coords are valid, they need to be [0..1]
                if z > z_buffer[x, y] and min(u,v) >= 0 and max(u,v) <= 1:
                    # showing the u and v coords as a color, not the actual texture just yet
                    if (renderMode == "uv"):
                        frame[x, y] = color

                        # z buffer stores values of 1 / z
                        z_buffer[x, y] = z
                    elif (renderMode == "texture"):
                        pixelColor = texture[int(u*text_size[0] + 1)][int(v*text_size[1])]
                        # ALL objects in the scene are rendered using alpha-clip, so if there's no color it's transparent
                        if (pixelColor[0] > 0 and pixelColor[1] > 0 and pixelColor[2] > 0):
                            frame[x, y] = pixelColor * color

                            # z buffer stores values of 1 / z
                            z_buffer[x, y] = z
  
# rotate the camera by an axis and angle
# re-defines the forward and up vectors, basically
def rotate_camera(camera,axis,angle):
    up = m.camera_up(camera)
    forward = m.camera_forward(camera)

    # new local vectors
    upNew = m.rotate_vector_3d(up,axis,angle)
    forwardNew = m.rotate_vector_3d(forward,axis,angle)

    # assinging the camera vectors
    camera[3] = forwardNew[0]
    camera[4] = forwardNew[1]
    camera[5] = forwardNew[2]

    camera[6] = upNew[0]
    camera[7] = upNew[1]
    camera[8] = upNew[2]

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
    
def array_has_item(array, item):
    for i in array:
        if (i == item):
            return True
        
    return False

def index_in_array(array, item):
    counter = 0
    for i in array:
        if (i == item):
            return counter
        counter += 1
        
    return -1

# the box's bounds represent SIZE, NOT EXTENTS
def clamp_box_3d(point, boxCenter, boxSizes):
    newX = min(max(point[0], boxCenter[0] - boxSizes[0]/2), boxCenter[0] + boxSizes[0]/2)
    newY = min(max(point[1], boxCenter[1] - boxSizes[1]/2), boxCenter[1] + boxSizes[1]/2)
    newZ = min(max(point[2], boxCenter[2] - boxSizes[2]/2), boxCenter[2] + boxSizes[2]/2)

    return np.asarray([newX,newY,newZ])

# I don't like typing out the np.asarray([]) function, so this one makes colors a bit less verbose
def constructColor(r,g,b):
    return np.asarray([r,g,b]).astype('uint8')

# whether a point is in an AABB (axis aligned bounding box)
# again, the sizes are SIZES, NOT EXTENTS in each direction
def point_in_box_3d(point, boxCenter, boxSizes):
    if (point[0] > boxCenter[0] - boxSizes[0]/2 and point[1] > boxCenter[1] - boxSizes[1]/2 and point[2] > boxCenter[2] - boxSizes[2]/2 and point[0] < boxCenter[0] + boxSizes[0]/2 and point[1] < boxCenter[1] + boxSizes[1]/2 and point[2] < boxCenter[2] + boxSizes[2]/2):
        return True
    else:
        return False
    
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
    
class Color:
    white = np.asarray([1,1,1]).astype('float32')

    red = np.asarray([1,0,0]).astype('float32')
    green = np.asarray([0,1,0]).astype('float32')
    blue = np.asarray([0,0,1]).astype('float32')

    yellow = np.asarray([1,1,0]).astype('float32')
    cyan = np.asarray([0,1,1]).astype('float32')
    magenta = np.asarray([1,0,1]).astype('float32')

    orange = np.asarray([1,0.592156862745098,0.1882352941176471]).astype('float32')

class Vector3:
    one = np.asarray([1.0,1.0,1.0])
    zero = np.asarray([0.0,0.0,0.0])

    forward = np.asarray([0.0,0.0,1.0])
    backward = np.asarray([0.0,0.0,-1.0])

    # left is positive, because PG3D uses a left-handed coordinate system
    left = np.asarray([1.0,0.0,0.0])
    right = np.asarray([-1.0,0.0,0.0])

    up = np.asarray([0.0,1.0,0.0])
    down = np.asarray([0.0,-1.0,0.0])

    def new(x,y,z):
        return np.asarray(x,y,z)
    
class Vector2:

    one = np.asarray([1.0,1.0])
    zero = np.asarray([0.0,0.0])
 
    # in 3D it's left = positive, but here it's right = positive
    # why? idk
    left = np.asarray([-1.0,0.0])
    right = np.asarray([1.0,0.0])

    up = np.asarray([0.0,1.0])
    down = np.asarray([0.0,-1.0])

    def new(x,y):
        return np.asarray(x,y) 
    
# generates a string of random number characters of a given length
def random_number_string(length):
    toReturn = ""

    for i in range(length):
        toReturn += str(random.randint(0, 9))

    return toReturn
    
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
        if (not array_has_item(self.objectNames, objName)):
            self.objectNames.append(objName)

# TODO: the entire particle system

# basically the way i'm doing the particle system is this:

# particle managers control the spawning/transforming/deleting of the objects in a particle system
# each manager has a hashcode, which is applied as a tag to the objects it controls so everyone knows what belongs to what

# particle managers are NOT objects, and DO NOT CORRESPOND to an object! they are separate and held in a separate list!

class ParticleManager:  
    # separate registry for particle managers
    _registry = []

    hash = ""

    def __init__(self):
        # we create a string of random numeric characters, of length 24 (random long-enough number that i picked)
        hash = random_number_string(24)

        self._registry.append(self)