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

# just to keep track of things, not actually used in code
version = "0.1"

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
# position (x,y,z), forward (x,y,z), up (x,y,z) (scale does nothing)
# the right vector is NOT defined/kept track of because it's unecessary, knowing the other two is enough
# why is the right vector the one that's ommited? idk
cameraWorldTransform = None
cameraLocalTransform = None
cameraParent = None

physicsEnabled = False

sky_texture = None

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

# used for camera controllers
def parentCamera(object, offX, offY, offZ):
    global cameraParent

    cameraParent = object
    cameraLocalTransform.position = np.asarray([offX, offY, offZ])

def parentCameraWithName(objName, offX, offY, offZ):
    global cameraParent

    cameraParent = getObject(objName)
    cameraLocalTransform.position = np.asarray([offX, offY, offZ])

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
                    i.add_local_position(closestPointOnThis[0] - desiredPoint[0],closestPointOnThis[1] - desiredPoint[1],closestPointOnThis[2] - desiredPoint[2])

                    # not a great permanent solution, but make the velocity 0 to make sure the collision stays resolved
                    i.set_velocity(0,0,0)

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
def mouse_position():
    return pg.mouse.get_pos() + mouseOffset

def updateCamera_freecam(moveSpeed):
    global cameraLocalTransform
    global timeSinceLastFrame

    pressed_keys = pg.key.get_pressed()
    if pressed_keys[ord('w')]:
        forward = cameraWorldTransform.forward
        cameraLocalTransform.position[0] += forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('s')]:
        forward = cameraWorldTransform.forward
        cameraLocalTransform.position[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('a')]:
        forward = cameraWorldTransform.get_right()
        cameraLocalTransform.position[0] += forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('d')]:
        forward = cameraWorldTransform.get_right()
        cameraLocalTransform.position[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('e')]:
        forward = cameraWorldTransform.up
        cameraLocalTransform.position[0] += forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] += forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('q')]:
        forward = cameraWorldTransform.up
        cameraLocalTransform.position[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        cameraLocalTransform.position[2] -= forward[2] * moveSpeed * timeSinceLastFrame

    xChange = mouseChange[0]
    yChange = mouseChange[1]

    rotate_camera(cameraLocalTransform.up,xChange * -0.001)
    rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001)

def updateCamera_firstPerson(moveSpeed, mouseSensitivity, enableMovement):
    global screenWidth
    global screenHeight

    global cameraLocalTransform
    global cameraWorldTransform
    global cameraParent

    global timeSinceLastFrame

    if (cameraParent == None):
        # no parent, no controller
        return
    
    # movement 

    if (enableMovement):
        rawF = cameraWorldTransform.forward
        f = m.subtract_3d(rawF, project_3d(rawF, np.asarray([0.0,1.0,0.0])))
        r = cameraWorldTransform.get_right()

        pressed_keys = pg.key.get_pressed()
        if pressed_keys[ord('w')]:
            cameraParent.add_local_position(f[0] * timeSinceLastFrame * moveSpeed,f[1] * timeSinceLastFrame * moveSpeed,f[2] * timeSinceLastFrame * moveSpeed)
        elif pressed_keys[ord('s')]:
            cameraParent.add_local_position(-f[0] * timeSinceLastFrame * moveSpeed,-f[1] * timeSinceLastFrame * moveSpeed,-f[2] * timeSinceLastFrame * moveSpeed)
        if pressed_keys[ord('a')]:
            cameraParent.add_local_position(r[0] * timeSinceLastFrame * moveSpeed,r[1] * timeSinceLastFrame * moveSpeed,r[2] * timeSinceLastFrame * moveSpeed)
        elif pressed_keys[ord('d')]:
            cameraParent.add_local_position(-r[0] * timeSinceLastFrame * moveSpeed,-r[1] * timeSinceLastFrame * moveSpeed,-r[2] * timeSinceLastFrame * moveSpeed)

    # rotation
    xChange = mouseChange[0]
    yChange = mouseChange[1]

    # you HAVEE to call camera_right() again to deal with the result of the first rotation
    # otherwise, weird things happen that aren't fun
    rotate_camera(np.asarray([0.0,1.0,0.0]),xChange * -0.001 * mouseSensitivity)
    rotate_camera(cameraLocalTransform.get_right(),yChange * 0.001 * mouseSensitivity)

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
    Model(objName,'pg3d_assets/cube_no-net.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(objName).set_local_position(x,y,z)

    return getObject(objName)

def spawnScaledCube(name, x,y,z, scale_x,scale_y,scale_z, tags):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/cube.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

def spawnCubeWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/cube.obj', texture_path,tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

# ********   plane:     ********
def spawnPlane(name,x,y,z,tags):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/plane.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    return getObject(objName)

def spawnScaledPlane(name,x,y,z,scale_x,scale_y,scale_z,tags):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/plane.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

def spawnPlaneWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/plane.obj', texture_path,tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

# ********   sphere:     ********
def spawnSphere(name,x,y,z,tags):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(name).set_local_position(x,y,z)

    return getObject(objName)

def spawnScaledSphere(name,x,y,z, scale_x,scale_y,scale_z,tags):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/sphere.obj', 'pg3d_assets/grid_16.png',tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

def spawnSphereWithTexture(name, x,y,z, scale_x,scale_y,scale_z, tags, texture_path):
    objName = nameModel(name)
    Model(objName,'pg3d_assets/sphere.obj', texture_path,tags, Color.white)

    getObject(objName).set_local_position(x,y,z)
    getObject(objName).set_scale(scale_x,scale_y,scale_z)

    return getObject(objName)

def getObjectIndex(name):
    counter = 0
    for i in Model._registry:
        if (i.name == name):
            return counter
        counter += 1


def destroyObject(objectName):
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

def spawnObjectWithTexture(objPath, texturePath, name, x, y, z, tags, color):
    if (getFirstIndex(name, '(') < len(name)): # object names may NOT have parentheses!
        return
    name = nameModel(name)
    Model(name,objPath, texturePath,tags,color)

    getObject(name).set_local_position(x,y,z)

def spawnObjectWithColor(objPath, name, x, y, z, tags, colorR, colorG, colorB):
    if (getFirstIndex(name, '(') < len(name)):
        return
    name = nameModel(name)
    Model(name,objPath, '',tags,np.asarray([colorR,colorG,colorB]).astype('uint8'))

    getObject(name).set_local_position(x,y,z)

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
    
class Color:
    white = np.asarray([1,1,1]).astype('float32')

    red = np.asarray([1,0,0]).astype('float32')
    green = np.asarray([0,1,0]).astype('float32')
    blue = np.asarray([0,0,1]).astype('float32')

    yellow = np.asarray([1,1,0]).astype('float32')
    cyan = np.asarray([0,1,1]).astype('float32')
    magenta = np.asarray([1,0,1]).astype('float32')

    orange = np.asarray([1,0.592156862745098,0.1882352941176471]).astype('float32')

# helpers, so you don't have to write stuff like np.asarray([])
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

    # alternative names:
    x_positive = np.asarray([1.0,0.0,0.0])
    x_negative = np.asarray([-1.0,0.0,0.0])

    y_positive = np.asarray([0.0,1.0,0.0])
    y_negative = np.asarray([0.0,-1.0,0.0])

    z_positive = np.asarray([0.0,0.0,1.0])
    z_negative = np.asarray([0.0,0.0,-1.0])

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

    # alternative names:
    x_positive = right = np.asarray([1.0,0.0])
    x_negative = np.asarray([-1.0,0.0])

    y_positive = np.asarray([0.0,1.0])
    y_negative = np.asarray([0.0,-1.0])

    def new(x,y):
        return np.asarray(x,y) 
    
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
    degToRadConversion = np.pi / 180
    radToDegConversion = 180 / np.pi

    def toRadians(deg):
        return deg * np.pi / 180
    
    def toDegrees(rad):
        return rad * 180 / np.pi