# rendering code was written by FINFET, and heavily modified by me
# (by that I mean I rewrote everything because FINFET didn't implement triangle clipping)

import pygame as pg
import numpy as np
from numba import njit

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
skyColor = np.asarray([0,0,0]).astype('uint8')

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

    screenWidth = w
    screenHeight = h
    
    screenWidth_actual = wActual
    screenHeight_actual = hActual

    verticalFOV = ver * np.pi / 180
    horizontalFOV = verticalFOV*screenWidth/screenHeight

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

                closestPointOnOther = j.closest_point(worldSpaceMidpoint)

                closestPointOnThis = i.closest_point(closestPointOnOther)

                if (length_3d(subtract_3d(closestPointOnOther, closestPointOnThis)) < 0.01):
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
    z_buffer = np.ones((screenWidth, screenHeight))

    # initialize the frame
    frame[:,:,:] = skyColor
    z_buffer[:,:] = 0 # start with some SMALL value
    # the value is small because the z buffer stores values of 1/z, so 0 represents the largest depth possible (it would be 1/infinity)

    # draw the frame
    for model in Model._registry:
        if (model.shouldBeDrawn):
            # this function will move the points so that they are centered around the camera
            # basically, handling the camera position/rotation stuff
            transform_points(model, model.points, camera)
            # this function will project the triangles onto the screen, and draw them
            draw_model(model, frame, model.points, model.triangles, camera, light_dir, z_buffer,
                        model.texture_uv, model.texture_map, model.texture, model.color)
    
    # skybox rendering is NOT SUPPORTED right now!!
    # if (backgroundMode == "skybox"):
    #     draw_skybox(frame,z_buffer)
    
    return frame

# skybox is not supported (or finished) because it's laggy!
@njit
def draw_skybox(frame,z_buffer):
    for x in range(screenWidth):
        for y in range(screenHeight):
            if (z_buffer[x,y] == 0): # only do skybox stuff on z_buffer coords that haven't been touched
                frame[x,y] = np.asarray([255,0,0]).astype('uint8')

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
    mouseChange = subtract_2d(mouse_position(), mousePos)
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
        forward = camera_forward(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('s')]:
        forward = camera_forward(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('a')]:
        forward = camera_right(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('d')]:
        forward = camera_right(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame
    if pressed_keys[ord('e')]:
        forward = camera_up(camera)
        camera[0] += forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * moveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('q')]:
        forward = camera_up(camera)
        camera[0] -= forward[0] * moveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * moveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * moveSpeed * timeSinceLastFrame

    xChange = mouseChange[0]
    yChange = mouseChange[1]

    rotate_camera(camera,camera_up(camera),xChange * -0.001)
    rotate_camera(camera,camera_right(camera),yChange * 0.001)

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

    rawF = camera_forward(camera)
    f = subtract_3d(rawF, project_3d(rawF, np.asarray([0.0,1.0,0.0])))
    r = camera_right(camera)

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
    rotate_camera(camera,camera_right(camera),yChange * 0.001)

def resetCameraRotation():
    camera[3] = 0.0
    camera[4] = 0.0
    camera[5] = 1.0

    camera[6] = 0.0
    camera[7] = 1.0
    camera[8] = 0.0

# ********   OBJECT functions:     ********

def setBackGroundColor(r,g,b):
    global skyColor
    skyColor = np.asarray([r,g,b]).astype('uint8')

def spawnCube(x,y,z,tags):
    name = nameModel("cube")
    Model(name,'assets/cube.obj', 'assets/grid_16.png',tags, Color.white)

    getObject(name).set_position(x,y,z)

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
    
    return Model._registry[0]
    
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

@njit
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

    camZ = camera_forward(camera)
    forwardVectorAxis = normalize_3d(cross_3d(camZ,np.asarray([0.0,0.0,1.0])))
    forwardVectorAngle = angle_3d(np.asarray([0.0,0.0,1.0]),camZ)

    if (forwardVectorAngle > 0):
        for i in points:
            j = rotate_point_3d(i, forwardVectorAxis, forwardVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]
    else:
        forwardVectorAxis = camZ

    upVectorAxis = normalize_3d(cross_3d(rotate_vector_3d(camera_up(camera),forwardVectorAxis,forwardVectorAngle),np.asarray([0.0,1.0,0.0])))
    upVectorAngle = angle_3d(np.asarray([0.0,1.0,0.0]), rotate_vector_3d(camera_up(camera),forwardVectorAxis,forwardVectorAngle))

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

        # Use Cross-Product to get surface normal
        # as said above, this is relative to the camera
        vet1 = np.asarray([points[triangle[1]][3]  - points[triangle[0]][3],points[triangle[1]][4]  - points[triangle[0]][4],points[triangle[1]][5]  - points[triangle[0]][5]])
        vet2 = np.asarray([points[triangle[2]][3]  - points[triangle[0]][3],points[triangle[2]][4]  - points[triangle[0]][4],points[triangle[2]][5]  - points[triangle[0]][5]])

        # camera relative normal vector
        # it's not a unit vector! it will have magnitude of sin(theta)
        normal = np.cross(vet1, vet2)

        # backface culling !!!
        if (backfaceCulling):
            normalLength = np.sqrt(normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2])

            v1 = np.asarray([normal[0]/normalLength,normal[1]/normalLength,normal[2]/normalLength])
            v2 = np.asarray([0.0,0.0,1.0])
            if ((v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]) > 0.5):
                continue

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

            draw_triangle(frame, z_buffer, texture, projpoints, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderingMode, color)
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
                p2 = np.asarray([problemVertices[0][3],problemVertices[0][4],problemVertices[0][5]])
                p3 = np.asarray([problemVertices[1][3],problemVertices[1][4],problemVertices[1][5]])

                parameter = (0.01 - p2[2]) / (p1[2] - p2[2])
                intersect1 = add_3d(p2, np.asarray([(p1[0]-p2[0]) * parameter,(p1[1]-p2[1]) * parameter,(p1[2]-p2[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[0][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[0][1] - problemUV[0][1]) * parameter]))

                parameter = (0.01 - p3[2]) / (p1[2] - p3[2])
                intersect1 = add_3d(p3, np.asarray([(p1[0]-p3[0]) * parameter,(p1[1]-p3[1]) * parameter,(p1[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[1][0] + (goodUV[0][0] - problemUV[1][0]) * parameter, problemUV[1][1] + (goodUV[0][1] - problemUV[1][1]) * parameter]))

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

                draw_triangle(frame, z_buffer, texture, goodVertices, goodUV, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderingMode, color)
            elif (len(problemVertices) == 1):
                # here only one vertex is an issue
                # the procedure is similar, but we end up with two triangles

                # here is our triangle as-is
                p1 = np.asarray([goodVertices[0][3],goodVertices[0][4],goodVertices[0][5]])
                p2 = np.asarray([goodVertices[1][3],goodVertices[1][4],goodVertices[1][5]])
                p3 = np.asarray([problemVertices[0][3],problemVertices[0][4],problemVertices[0][5]])

                parameter = (0.01 - p3[2]) / (p1[2] - p3[2])
                intersect1 = add_3d(p3, np.asarray([(p1[0]-p3[0]) * parameter,(p1[1]-p3[1]) * parameter,(p1[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[0][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[0][1] - problemUV[0][1]) * parameter]))

                parameter = (0.01 - p3[2]) / (p2[2] - p3[2])
                intersect1 = add_3d(p3, np.asarray([(p2[0]-p3[0]) * parameter,(p2[1]-p3[1]) * parameter,(p2[2]-p3[2]) * parameter]))
                goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                goodUV.append(np.asarray([problemUV[0][0] + (goodUV[1][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[1][1] - problemUV[0][1]) * parameter]))

                goodVertices[2][6] = (-hor_fov_adjust*goodVertices[2][3]/np.abs(goodVertices[2][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[2][7] = (-ver_fov_adjust*goodVertices[2][4]/np.abs(goodVertices[2][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[2][8] = goodVertices[2][5] 

                goodVertices[3][6] = (-hor_fov_adjust*goodVertices[3][3]/np.abs(goodVertices[3][5]) + 0.5*screenWidth).astype(np.int32)
                goodVertices[3][7] = (-ver_fov_adjust*goodVertices[3][4]/np.abs(goodVertices[3][5]) + 0.5*screenHeight).astype(np.int32)
                goodVertices[3][8] = goodVertices[3][5] 

                # this is where we have to turn our array of four points into two triangles

                good1 = np.asarray([goodVertices[0],goodVertices[1],goodVertices[2]])
                good2 = np.asarray([goodVertices[1],goodVertices[3],goodVertices[2]])

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

                uv1 = np.asarray([goodUV[0] * z01,goodUV[1] * z11,goodUV[2] * z21])
                uv2 = np.asarray([goodUV[1] * z02,goodUV[3] * z12,goodUV[2] * z22])

                draw_triangle(frame, z_buffer, texture, good1, uv1, minX1, maxX1, minY1, maxY1, text_size, z01, z11, z21,renderingMode, color)
                draw_triangle(frame, z_buffer, texture, good2, uv2, minX2, maxX2, minY2, maxY2, text_size, z02, z12, z22,renderingMode, color)


        #  we do nothing if the triangle is all behind (state == 1), we just skip those

# z-buffering NOT used for wireframe, it is for the others though
@njit
def draw_triangle(frame, z_buffer, texture, proj_points, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2, renderMode, color):
    global screenWidth
    global screenHeight

    global wireframeColor

    # barycentric denominator, based on https://codeplea.com/triangular-interpolation
    # this will come into play when calculating the texture coordinates, and depth at the current pixel
    denominator = 1 / ((proj_points[1][7] - proj_points[2][7])*(proj_points[0][6] - proj_points[2][6]) +
    (proj_points[2][6] - proj_points[1][6])*(proj_points[0][7] - proj_points[2][7]) + 1e-32)
    
    # looping through every pixel in the bounding box that the triangle represents
    # we limit this box to the edges of the screen, because we don't care about anything else

    # because of these restrictions we don't need any further checks for making sure the x and y are valid
    for y in range(max(minY, 0), min(maxY, screenHeight)):
        for x in range(max(minX, 0), min(maxX, screenWidth)):

            # barycentric weights
            w0 = ((proj_points[1][7]-proj_points[2][7])*(x - proj_points[2][6]) + (proj_points[2][6]-proj_points[1][6])*(y - proj_points[2][7]))*denominator
            w1 = ((proj_points[2][7]-proj_points[0][7])*(x - proj_points[2][6]) + (proj_points[0][6]-proj_points[2][6])*(y - proj_points[2][7]))*denominator
            w2 = 1 - w0 - w1

            if (renderMode == "wireframe"):
                if (w0 < 0 or w1 < 0 or w2 < 0):
                    continue

                if (np.abs(w0*z0) < 0.0001 or np.abs(w1*z1) < 0.0001 or np.abs(w2*z2) < 0.0001):
                        frame[x, y] = wireframeColor
            else:
                # if any weight is negative, we're outside the triangle and so we won't do anything
                if (w0 < 0 or w1 < 0 or w2 < 0):
                    continue

                # sinze z0,z1, and z2 are all 1/z at some point, this value will also be 1 / z
                z = w0*z0 + w1*z1 + w2*z2
                u = ((w0*uv_points[0][0] + w1*uv_points[1][0] + w2*uv_points[2][0])*(1/z + 0.0001))
                v = ((w0*uv_points[0][1] + w1*uv_points[1][1] + w2*uv_points[2][1])*(1/z + 0.0001))

                # z needs to be greater than the value at the z buffer, meaning 1 / z needs to be less
                # also make sure the u and v coords are valid, they need to be [0..1]
                if z > z_buffer[x, y] and min(u,v) >= 0 and max(u,v) <= 1:
                    # showing the u and v coords as a color, not the actual texture just yet
                    if (renderMode == "uv"):
                        frame[x, y] = np.asarray([u*255,v*255,0]).astype('uint8')

                        # z buffer stores values of 1 / z
                        z_buffer[x, y] = z
                    elif (renderMode == "texture"):
                        pixelColor = texture[int(u*text_size[0] + 1)][int(v*text_size[1])]
                        # ALL objects in the scene are rendered using alpha-clip, so if there's no color it's transparent
                        if (pixelColor[0] > 0 and pixelColor[1] > 0 and pixelColor[2] > 0):
                            frame[x, y] = pixelColor * color

                            # z buffer stores values of 1 / z
                            z_buffer[x, y] = z

@njit
def clamp(val, lower, upper):
    return min(max(val, lower), upper)

def average_point_3d(list):
    toReturn = np.asarray([0.0,0.0,0.0])
    for i in list:
        toReturn[0] += i[3] / len(list)
        toReturn[1] += i[4] / len(list)
        toReturn[2] += i[5] / len(list)

    return toReturn

# ********  2D vector helpers:  ********  

@njit()
def dot_2d(arr1, arr2): 
    return arr1[0]*arr2[0] + arr1[1]*arr2[1]

# linearly interpolate from one point to another, using parameter t
@njit()
def lerp_2d(a, b, t):
    return np.asarray([a[0] + (b[0]-a[0]) * t, a[1] + (b[1]-a[1]) * t])

# add b to a
@njit()
def add_2d(a, b):
    return np.asarray([a[0] + b[0],a[1] + b[1]])

# subtract b from a 
@njit()
def subtract_2d(a, b):
    return np.asarray([a[0] - b[0], a[1] - b[1]])

# length of a vector, using pythagorean theorem
@njit()
def length_2d(a):
    return np.sqrt(a[0] * a[0] + a[1] * a[1])

# takes in a vector, outputs that vector as a unit vector
def normalize_2d(a):
    l = length_2d(a)

    if (l == 0):
        return np.asarray([0.0,0.0])

    return np.asarray([a[0]/l,a[1]/l])

# ********  3D vector helpers:       ********

@njit()
def dot_3d(arr1, arr2): 
    return arr1[0]*arr2[0] + arr1[1]*arr2[1] + arr1[2]*arr2[2]

# interpolation for direction
# not sure if this is how slerp is supposed to be done but ah well
def slerp_3d(a,b,t):
    rotationAxis = normalize_3d(cross_3d(a,b))
    rotationAngle = angle_3d(a,b)

    return rotate_vector_3d(a,rotationAxis, rotationAngle * t)

# linearly interpolate from one point to another, using parameter t
@njit()
def lerp_3d(a, b, t):
    return np.asarray([a[0] + (b[0]-a[0]) * t, a[1] + (b[1]-a[1]) * t, a[2] + (b[2]-a[2]) * t])

# add b to a
@njit()
def add_3d(a, b):
    return np.asarray([a[0] + b[0],a[1] + b[1], a[2] + b[2]])

# subtract b from a 
@njit
def subtract_3d(a, b):
    return np.asarray([a[0] - b[0], a[1] - b[1], a[2] - b[2]])

# length of a vector, using pythagorean theorem
@njit()
def length_3d(a):
    return np.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])

# local vectors of the camera (forward, up, right)
# the forward and up vectors are defined in the camera, 
# the right vector is calculated as a cross product between the two
@njit()
def camera_forward(camera):
    return np.asarray([camera[3],camera[4],camera[5]])
@njit()
def camera_up(camera):
    return np.asarray([camera[6],camera[7],camera[8]])
def camera_right(camera):
    crossProduct = normalize_3d(cross_3d(camera_forward(camera), camera_up(camera)))
    return np.asarray([-crossProduct[0],-crossProduct[1],-crossProduct[2]])

# calculate the angle in RADIANS between two vectors
def angle_3d(a, b):
    dp = dot_3d(a,b)
    la = length_3d(a)
    lb = length_3d(b)

    return np.acos((dp) / (la * lb))

# calculate the cross product between two vectors
# (there is no cross in 2d)
@njit()
def cross_3d(a,b):
    return np.asarray([a[1]*b[2] - a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]])

# takes in a vector, outputs that vector as a unit vector
def normalize_3d(a):
    l = length_3d(a)

    if (l == 0):
        return np.asarray([0.0,0.0,0.0])

    return np.asarray([a[0]/l,a[1]/l,a[2]/l])

# rotate a vector (x,y,z) around another vector, by an angle
@njit
def rotate_vector_3d(vector, axis, angle):
    # rotate around x axis
    i = np.asarray([0.0,0.0,0.0])
    i[0] = vector[0] * (     (axis[0] * axis[0]) * (1 - np.cos(angle)) + np.cos(angle)                  ) + vector[1] * (        (axis[1] * axis[0]) * (1 - np.cos(angle)) - (axis[2] * np.sin(angle))         ) + vector[2] * (        (axis[0] * axis[2]) * (1 - np.cos(angle)) + (axis[1] * np.sin(angle))     )
    i[1] = vector[0] * (     (axis[0] * axis[1]) * (1 - np.cos(angle)) + (axis[2] * np.sin(angle))     ) + vector[1] * (        (axis[1] * axis[1]) * (1 - np.cos(angle)) + np.cos(angle)                      ) + vector[2] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) - (axis[0] * np.sin(angle))     )
    i[2] = vector[0] * (     (axis[0] * axis[2]) * (1 - np.cos(angle)) - (axis[1] * np.sin(angle))     ) + vector[1] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) + (axis[0] * np.sin(angle))         ) + vector[2] * (        (axis[2] * axis[2]) * (1 - np.cos(angle)) + np.cos(angle)                  )
    
    return i   
# rotate the camera by an axis and angle
# re-defines the forward and up vectors, basically
def rotate_camera(camera,axis,angle):
    up = camera_up(camera)
    forward = camera_forward(camera)

    # new local vectors
    upNew = rotate_vector_3d(up,axis,angle)
    forwardNew = rotate_vector_3d(forward,axis,angle)

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

# ********  MESH helpers:       ********

def read_obj(fileName):
    '''
    Read wavefront models with or without textures, supports triangles and quads (turned into triangles)
    '''
    vertices, triangles, texture_uv, texture_map = [], [], [], []

    with open(fileName) as f:
        for line in f.readlines():

            splitted = line.split() # split the line in a list

            if len(splitted) == 0: # skip empty lines
                continue

            if splitted[0] == "v": # vertices
                vertices.append(splitted[1:4] + [1,1,1] + [1,1,1]) # aditional spaces for transformation, and projection

            elif splitted[0] == "vt": # texture coordinates
                texture_uv.append(splitted[1:3])

            elif splitted[0] == "f": # Faces

                if len(splitted[1].split("/")) == 1: # no textures
                    triangles.append([splitted[1], splitted[2], splitted[3]])

                    if len(splitted) > 4: # quads, make additional triangle
                        triangles.append([splitted[1], splitted[3], splitted[4]])

                else: # with textures
                    p1 = splitted[1].split("/")
                    p2 = splitted[2].split("/")
                    p3 = splitted[3].split("/")
                    triangles.append([p1[0], p2[0], p3[0]])
                    texture_map.append([p1[1], p2[1], p3[1]])
                    
                    if len(splitted) > 4: # quads, make additional triangle
                        p4 = splitted[4].split("/")
                        triangles.append([p1[0], p3[0], p4[0]])
                        texture_map.append([p1[1], p3[1], p4[1]])
                
    vertices = np.asarray(vertices).astype(float)
    triangles = np.asarray(triangles).astype(int) - 1 # adjust indexes to start with 0

    texture_uv = np.asarray(texture_uv).astype(float)
    texture_uv[:,1] = 1 - texture_uv[:,1] # apparently obj textures are upside down
    texture_map = np.asarray(texture_map).astype(int) - 1 # adjust indexes to start with 0
    
    return vertices, triangles, texture_uv, texture_map

# based on who is in what level, update which models sould render and which should not
# THE ENGINE DOES NOT LOOP THROUGH LEVELS, it just checks the shouldBeRendered var for each model
# this is to avoid duplicate models, and performance loss
def refreshRenderBooleans():
    # loop through all levels, and set their object's boolean variables to the level's variable
    for i in Level._registry:
        for j in i.objectNames:
            getObject(j).shouldBeDrawn = i.isActive

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

class Model:
    _registry = []

    name = ""

    # there are some tags that the engine looks for, like the 'physics' tag
    tags = []

    # models use dictionaries as per-object variables
    # this allows the storage of things like collider data
    # (there is a collider TAG too, because it makes it easier to search through objects (objects have less tags than data), but that might change)
    data = {}

    # essentially a unity transform component:

    # scale, then rotation, then position is applied
    position = np.asarray([0.0,0.0,0.0])
    forward = np.asarray([0.0,0.0,1.0])
    up = np.asarray([0.0,1.0,0.0])
    scale = np.asarray([1.0,1.0,1.0])

    # physics stuff
    linearVelocity = np.asarray([0.0,0.0,0.0])
    angularVelocity = np.asarray([0.0,0.0,0.0])
    
    # average of all vertices
    rawMidpoint = np.asarray([0.0,0.0,0.0])

    color = np.asarray([0,0,0]).astype('uint8')
    
    # whether to render the object or not
    # normally this is set through the level system, the object inherits the variable from the parent level
    # IF THE OBJECT IS IN A LEVEL, you cannot manually enable/disable it BUT YOU CAN IF IT'S NOT IN A LEVEL by calling show()/hide()
    shouldBeDrawn = True

    def __init__(self, name, path_obj, path_texture, tags, color):
        self.name = name

        self.tags = tags

        self.position = np.asarray([0.0,0.0,0.0])
        self.forward = np.asarray([0.0,0.0,1.0])
        self.up = np.asarray([0.0,1.0,0.0])
        # scale is for each axis
        self.scale = np.asarray([1.0,1.0,1.0])

        self._registry.append(self)
        # points are stored using nine numbers
        # the first three is the point as it appears in the mesh file
        # the next three is the point as it appears in the scene, RELATIVE TO THE CAMERA
        # the final three is the point as it appears projected onto the screen
        self.points, self.triangles, self.texture_uv, self.texture_map =  read_obj(path_obj)
        self.texture = pg.surfarray.array3d(pg.image.load(path_texture))

        self.rawMidpoint = self.calculateRawMidpoint()

        self.data = {}

        # for textured models, the color is multiplied by the texture
        # for colored models, the color applies to all geometry
        self.color = color

    def show(self):
        self.shouldBeDrawn = True

    def hide(self):
        self.shouldBeDrawn = False

    # given a point, find the closest point ON THIS OBJECT'S COLLIDER
    def closest_point(self, foreignPoint):
        # we're assuming that if the object has a collider tag, it has the necessary data
        # if this somehow isn't true, we get problems lol because the collider defaults to 0,0,0

        # the proceudre is basically to transform the given point so that it's relative to the local axes,
        # then clamp it to the box,
        # then transform it back

        # move the point so its POSITION is local
        rmpoint= self.midpoint()
        worldSpaceMidpoint = np.asarray([rmpoint[3],rmpoint[4],rmpoint[5]])
        localPoint = np.asarray([foreignPoint[0] - worldSpaceMidpoint[0],foreignPoint[1] - worldSpaceMidpoint[1],foreignPoint[2] - worldSpaceMidpoint[2]])

        # now, we rotate it using the opposite rotation we would use to transform a point
        forwardRotationAxis = normalize_3d(cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.forward
            
        rotatedUpAxis = rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = normalize_3d(cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = angle_3d(rotatedUpAxis, self.up)
        
        if upRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        colliderBounds = self.data["collider_bounds"]

        # now, clamp it 
        # this function takes in (point, point point) and (box, box, box)
        clampedPoint = clamp_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),colliderBounds)

        rotatedPoint = clampedPoint

        #print(str(clampedPoint + worldSpaceMidpoint) + "     " + str(foreignPoint))

        # UNROTATE THE POINT
        if upRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(clampedPoint, upRotationAxis, -upRotationAngle)
        if forwardRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(rotatedPoint, forwardRotationAxis, -forwardRotationAngle)

        # add the position back
        return np.asarray([rotatedPoint[0] + worldSpaceMidpoint[0],rotatedPoint[1] + worldSpaceMidpoint[1],rotatedPoint[2] + worldSpaceMidpoint[2]])
    
    def is_point_inside(self, foreignPoint):
        rmpoint= self.midpoint()
        worldSpaceMidpoint = np.asarray([rmpoint[3],rmpoint[4],rmpoint[5]])
        localPoint = np.asarray([foreignPoint[0] - worldSpaceMidpoint[0],foreignPoint[1] - worldSpaceMidpoint[1],foreignPoint[2] - worldSpaceMidpoint[2]])

        # now, we rotate it using the opposite rotation we would use to transform a point
        forwardRotationAxis = normalize_3d(cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.forward

        rotatedUpAxis = rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = normalize_3d(cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = angle_3d(rotatedUpAxis, self.up)

        if upRotationAngle > 0:
            rotatedPoint = rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        colliderBounds = self.data["collider_bounds"]

        return point_in_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),colliderBounds)
        
        # there's no reason to un-transform the point, we're only trying to find whether its in the box

    def add_data(self, key, value):
        # update the entry in the dictionary
        self.data[key] = value

    def calculateRawMidpoint(self):
        toReturn = np.asarray([0.0,0.0,0.0])

        for i in self.points:
            toReturn[0] += i[0] / len(self.points)
            toReturn[1] += i[1] / len(self.points)
            toReturn[2] += i[2] / len(self.points)

        return toReturn
    
    def midpoint(self):
        rawMidpoint = np.asarray([self.rawMidpoint[0],self.rawMidpoint[1],self.rawMidpoint[2],0.0,0.0,0.0])
        return self.transform_point(rawMidpoint)

    # whether the tags array has a given tag
    def hasTag(self, tag):
        for i in self.tags:
            if (i == tag):
                return True
            
        return False

    # when messing with models, please use the functions and don't mess with the variables themselves!

    def is_triggered(self):
        # assuming there IS actually a trigger collider when this function is called
        
        # also, the only objects that are detected in trigger colliders are ones with the "interact" tag
        # ALSO, COLLIDERS are the only thing that triggers a trigger collider, not other trigger colliders
        possibleObjects = getObjectsWithTag("interact")

        # loop through each, and check to see if the closest point on their collider

    def add_collider(self,boundsX,boundsY,boundsZ):
        self.add_tag("collider")

        self.add_data("collider_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    def add_trigger(self,boundsX,boundsY,boundsZ):
        self.add_tag("trigger")

        self.add_data("trigger_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    def add_tag(self, tagName):
        if (array_has_item(self.tags, tagName)):
            return
        self.tags.append(tagName)

    def add_velocity(self,x,y,z):
        self.linearVelocity[0] += x
        self.linearVelocity[1] += y
        self.linearVelocity[2] += z

    def set_velocity(self,x,y,z):
        self.linearVelocity[0] = x
        self.linearVelocity[1] = y
        self.linearVelocity[2] = z

    # set position to some numbers
    def set_position(self, x, y, z):
        self.position[0] = x
        self.position[1] = y
        self.position[2] = z
    
    # translate with individual numbers
    def add_position(self, x, y, z):
        self.position[0] += x
        self.position[1] += y
        self.position[2] += z

    # rotate around any axis, using a CC angle
    def rotate(self, angle, axis):
        newForward = rotate_vector_3d(self.forward, angle, axis)
        newUp = rotate_vector_3d(self.up, angle, axis)

        self.forward[0] = newForward[0]
        self.forward[1] = newForward[1]
        self.forward[2] = newForward[2]

        self.up[0] = newUp[0]
        self.up[1] = newUp[1]
        self.up[2] = newUp[2]

    def get_forward(self):
        return self.forward

    def get_up(self):
        return self.up

    def get_right(self):
        f = self.forward
        u = self.up

        crossProduct = normalize_3d(cross_3d(f, u))
        
        return np.asarray([-crossProduct[0],-crossProduct[1],-crossProduct[2]])

    def set_forward(self, v):
        appliedRotationAxis = normalize_3d(cross_3d(self.forward, v))
        appliedRotationAngle = angle_3d(self.forward, v)

        if (appliedRotationAngle > 0.001 and appliedRotationAngle < np.pi - 0.001):
            self.forward = rotate_vector_3d(self.forward, appliedRotationAxis, appliedRotationAngle)
            self.up = rotate_vector_3d(self.up, appliedRotationAxis, appliedRotationAngle)

    def set_up(self, v):
        appliedRotationAxis = cross_3d(self.up, v)
        appliedRotationAngle = angle_3d(self.up, v)

        self.forward = rotate_vector_3d(self.forward, appliedRotationAxis, appliedRotationAngle)
        self.up = rotate_vector_3d(self.up, appliedRotationAxis, appliedRotationAngle)

    # set scale with three numbers
    def set_scale(self, a, b, c):
        self.scale[0] = a
        self.scale[1] = b
        self.scale[2] = c

    def transform_point(self, point):
        # scale first
        point[3] = point[0] * self.scale[0]
        point[4] = point[1] * self.scale[1]
        point[5] = point[2] * self.scale[2]

        # then rotation
        forwardRotationAxis = normalize_3d(cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        if (forwardRotationAngle <= 0):
            forwardRotationAxis = self.forward
        rotatedUpAxis = rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = normalize_3d(cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = angle_3d(rotatedUpAxis, self.up)
        rotatedPoint = point
        if forwardRotationAngle > 0:
            rotatedPoint = rotate_point_3d(point, forwardRotationAxis, forwardRotationAngle)
        if upRotationAngle > 0:
            rotatedPoint = rotate_point_3d(rotatedPoint, upRotationAxis, upRotationAngle)
        point[3] = rotatedPoint[3]
        point[4] = rotatedPoint[4]
        point[5] = rotatedPoint[5]

        # then position
        point[3] += self.position[0]
        point[4] += self.position[1]
        point[5] += self.position[2]

        return point
    
def array_has_item(array, item):
    for i in array:
        if (i == item):
            return True
        
    return False

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
    bLength = length_3d(b)

    coefficient = dot_3d(a,b) / (bLength * bLength)

    return np.asarray([b[0] * coefficient,b[1] * coefficient,b[2] * coefficient])

# project vector a onto vector b (2D)
def project_2d(a,b):
    bLength = length_2d(b)

    coefficient = dot_2d(a,b) / (bLength * bLength)

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