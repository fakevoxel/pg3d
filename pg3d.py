# rendering code was written by ________, and heavily modified by me

import pygame as pg
import numpy as np
from numba import njit

screenWidth = 800
screenHeight = 600

verticalFOV = np.pi / 4
horizontalFOV = verticalFOV*screenWidth/screenHeight

skyColor = np.asarray([200,100,0]).astype('uint8')

mouseChange = np.asarray([0.0,0.0])
mousePos = np.asarray([0.0,0.0])
mouseOffset = np.asarray([0.0,0.0])

cameraMoveSpeed = 10
cameraRotateSpeed = 0.001

shipVelocity = np.asarray([0.0,0.0,0.0])
maxShipVelocity = 1

gravityCoefficient = 0.5

timeSinceLastFrame = 0

camera = np.asarray([0.0, 0.0, -10.0,       0.0, 0.0, 1.0,      0.0, 1.0, 0.0])
clock = pg.time.Clock()

def setGravity(a):
    global gravityCoefficient
    gravityCoefficient = a

def moveCamera():
    global camera
    global timeSinceLastFrame
    pressed_keys = pg.key.get_pressed()
    if pressed_keys[ord('w')]:
        forward = camera_forward(camera)
        camera[0] += forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * cameraMoveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('s')]:
        forward = camera_forward(camera)
        camera[0] -= forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * cameraMoveSpeed * timeSinceLastFrame
    if pressed_keys[ord('a')]:
        forward = camera_right(camera)
        camera[0] += forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * cameraMoveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('d')]:
        forward = camera_right(camera)
        camera[0] -= forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * cameraMoveSpeed * timeSinceLastFrame
    if pressed_keys[ord('e')]:
        forward = camera_up(camera)
        camera[0] += forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] += forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] += forward[2] * cameraMoveSpeed * timeSinceLastFrame
    elif pressed_keys[ord('q')]:
        forward = camera_up(camera)
        camera[0] -= forward[0] * cameraMoveSpeed * timeSinceLastFrame
        camera[1] -= forward[1] * cameraMoveSpeed * timeSinceLastFrame
        camera[2] -= forward[2] * cameraMoveSpeed * timeSinceLastFrame
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
    mouseChange = subtract_vector_2d(mouse_position(), mousePos)
    mousePos = mouse_position()
def mouse_position():
    return pg.mouse.get_pos() + mouseOffset

def rotateCamera():
    global screenWidth
    global screenHeight

    xChange = mouseChange[0]
    yChange = mouseChange[1]

    rotate_camera(camera,camera_up(camera),xChange * -0.001)
    rotate_camera(camera,camera_right(camera),yChange * 0.001)

def init(w, h, ver):
    global screenWidth
    global screenHeight
    global verticalFOV
    global horizontalFOV

    global camera
    global clock

    screenWidth = w
    screenHeight = h
    verticalFOV = ver
    horizontalFOV = verticalFOV*screenWidth/screenHeight

    # required for pygame to work properly
    pg.init()

    clock = pg.time.Clock()

    # position (x,y,z), right (x,y,z), up (x,y,z), forward (x,y,z)
    camera = np.asarray([0.0, 0.0, -10.0,       0.0, 0.0, 1.0,      0.0, 1.0, 0.0])

    pg.display.set_mode((screenWidth, screenHeight), pg.FULLSCREEN)

    pg.mouse.set_visible(0)
    pg.mouse.set_pos(screenWidth/2,screenHeight/2)

def setBackGroundColor(r,g,b):
    global skyColor
    skyColor = np.asarray([r,g,b]).astype('uint8')

def update():
    global timeSinceLastFrame
    global clock

    timeSinceLastFrame = clock.tick()*0.001

    updateCursor()

    for i in getObjectsWithTag("physics"):
        i.add_velocity(0.0,-1.0 * timeSinceLastFrame * gravityCoefficient, 0.0)
        i.add_position(i.linearVelocity[0] * timeSinceLastFrame,i.linearVelocity[1] * timeSinceLastFrame,i.linearVelocity[2] * timeSinceLastFrame)

def getFrame():
    global camera
    global skyColor

    # like a directional light in unity
    light_dir = np.asarray([0.0,1.0,0.0])
    light_dir = light_dir/np.linalg.norm(light_dir)

    frame= np.ones((screenWidth, screenHeight, 3)).astype('uint8')
    z_buffer = np.ones((screenWidth, screenHeight))

    # initialize the frame
    frame[:,:,:] = skyColor
    z_buffer[:,:] = 1e32 # start with some big value

    # draw the frame
    # TODO: proper object spawning
    for model in Model._registry:
        project_points(model, model.points, camera)
        draw_model(model, frame, model.points, model.triangles, camera, light_dir, z_buffer, model.textured,
                    model.texture_uv, model.texture_map, model.texture)
    
    return frame

def spawnCube(x,y,z,tags):
    name = nameModel("cube")
    Model(name,'assets/cube.obj', 'assets/grid_16.png',tags)

    getObject(name).set_position(x,y,z)

# object names may NOT have parentheses!
def spawnObject(objPath, texturePath, name, x, y, z, tags):
    if (getFirstIndex(name, '(') < len(name)):
        return
    name = nameModel("cube")
    Model(name,objPath, texturePath,tags)

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
    
def getFirstIndex(string, char):
    
    for i in range(len(string)):
        if (string[i] == char):
            return i
    
    return len(string)

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
            
def drawScreen(frame):
    # turn the frame into a surface
    surf = pg.surfarray.make_surface(frame)
    # blit that (draw it) onto the screen
    pg.display.get_surface().blit(surf, (0,0)); pg.display.update()

def quit():
    pg.quit()

class Model:
    _registry = []

    name = ""

    # there are some tags that the engine looks for, like the 'physics' tag
    tags = []

    # models use dictionaries as per-object variables

    # essentially a unity transform component:

    # scale, then rotation, then position is applied
    position = np.asarray([0.0,0.0,0.0])
    forward = np.asarray([0.0,0.0,1.0])
    up = np.asarray([0.0,1.0,0.0])
    scale = np.asarray([1.0,1.0,1.0])

    # physics stuff
    linearVelocity = np.asarray([0.0,0.0,0.0])
    angularVelocity = np.asarray([0.0,0.0,0.0])

    def __init__(self, name, path_obj, path_texture, tags):
        self.name = name

        self.tags = tags

        self.position = np.asarray([0.0,0.0,0.0])
        self.forward = np.asarray([0.0,0.0,1.0])
        self.up = np.asarray([0.0,1.0,0.0])
        # scale is for each axis
        self.scale = np.asarray([1.0,1.0,1.0])

        self._registry.append(self)
        self.points, self.triangles, self.texture_uv, self.texture_map, self.textured =  read_obj(path_obj)
        if self.textured:
            self.texture = pg.surfarray.array3d(pg.image.load(path_texture))
        else:
            self.texture_uv, self.texture_map = np.ones((2,2)), np.random.randint(1, 2, (2,3))
            self.texture = np.random.randint(0, 255, (10, 10,3))

    # whether the tags array has a given tag
    def hasTag(self, tag):
        for i in self.tags:
            if (i == tag):
                return True
            
        return False

    # when messing with models, please use the functions and don't mess with the variables themselves!
    
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

    def set_forward(self, v):
        appliedRotationAxis = normalize_vector(cross_vector(self.forward, v))
        appliedRotationAngle = angle_vector_3d(self.forward, v)

        if (appliedRotationAngle > 0.001 and appliedRotationAngle < np.pi - 0.001):
            self.forward = rotate_vector_3d(self.forward, appliedRotationAxis, appliedRotationAngle)
            self.up = rotate_vector_3d(self.up, appliedRotationAxis, appliedRotationAngle)

    def set_up(self, v):
        appliedRotationAxis = cross_vector(self.up, v)
        appliedRotationAngle = angle_vector_3d(self.up, v)

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
        forwardRotationAxis = normalize_vector(cross_vector(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = angle_vector_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        rotatedUpAxis = rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = normalize_vector(cross_vector(rotatedUpAxis, self.up))
        upRotationAngle = angle_vector_3d(rotatedUpAxis, self.up)
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

# rotate a vector (x,y,z) around another vector, by an angle
@njit
def rotate_vector_3d(vector, axis, angle):
    # rotate around x axis
    i = np.asarray([0.0,0.0,0.0])
    i[0] = vector[0] * (     (axis[0] * axis[0]) * (1 - np.cos(angle)) + np.cos(angle)                  ) + vector[1] * (        (axis[1] * axis[0]) * (1 - np.cos(angle)) - (axis[2] * np.sin(angle))         ) + vector[2] * (        (axis[0] * axis[2]) * (1 - np.cos(angle)) + (axis[1] * np.sin(angle))     )
    i[1] = vector[0] * (     (axis[0] * axis[1]) * (1 - np.cos(angle)) + (axis[2] * np.sin(angle))     ) + vector[1] * (        (axis[1] * axis[1]) * (1 - np.cos(angle)) + np.cos(angle)                      ) + vector[2] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) - (axis[0] * np.sin(angle))     )
    i[2] = vector[0] * (     (axis[0] * axis[2]) * (1 - np.cos(angle)) - (axis[1] * np.sin(angle))     ) + vector[1] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) + (axis[0] * np.sin(angle))         ) + vector[2] * (        (axis[2] * axis[2]) * (1 - np.cos(angle)) + np.cos(angle)                  )
    
    return i   

# rotate a vector (x,y,z) around another vector, by an angle
@njit
def rotate_point_3d(vector, axis, angle):
    # rotate around x axis
    i = np.asarray([0.0,0.0,0.0,0.0,0.0,0.0])
    i[3] = vector[3] * (     (axis[0] * axis[0]) * (1 - np.cos(angle)) + np.cos(angle)                  ) + vector[4] * (        (axis[1] * axis[0]) * (1 - np.cos(angle)) - (axis[2] * np.sin(angle))         ) + vector[5] * (        (axis[0] * axis[2]) * (1 - np.cos(angle)) + (axis[1] * np.sin(angle))     )
    i[4] = vector[3] * (     (axis[0] * axis[1]) * (1 - np.cos(angle)) + (axis[2] * np.sin(angle))     ) + vector[4] * (        (axis[1] * axis[1]) * (1 - np.cos(angle)) + np.cos(angle)                      ) + vector[5] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) - (axis[0] * np.sin(angle))     )
    i[5] = vector[3] * (     (axis[0] * axis[2]) * (1 - np.cos(angle)) - (axis[1] * np.sin(angle))     ) + vector[4] * (        (axis[1] * axis[2]) * (1 - np.cos(angle)) + (axis[0] * np.sin(angle))         ) + vector[5] * (        (axis[2] * axis[2]) * (1 - np.cos(angle)) + np.cos(angle)                  )
    
    return i   

def project_points(mesh, points, camera):
    global screenWidth
    global screenHeight

    global horizontalFOV
    global verticalFOV

    hor_fov_adjust = 0.5*screenWidth/ np.tan(horizontalFOV * 0.5) 
    ver_fov_adjust = 0.5*screenHeight/ np.tan(verticalFOV * 0.5)

    # go through the points and apply the mesh's transforms
    for i in points:
        j = mesh.transform_point(i)

        i[3] = j[3]
        i[4] = j[4]
        i[5] = j[5]

    # translate to have camera as origin
    points[:,3] -= camera[0]
    points[:,4] -= camera[1]
    points[:,5] -= camera[2]

    camZ = camera_forward(camera)
    forwardVectorAxis = normalize_vector(cross_vector(camZ,np.asarray([0.0,0.0,1.0])))
    forwardVectorAngle = angle_vector_3d(np.asarray([0.0,0.0,1.0]),camZ)

    if (forwardVectorAngle > 0):
        for i in points:
            j = rotate_point_3d(i, forwardVectorAxis, forwardVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]

    upVectorAxis = normalize_vector(cross_vector(rotate_vector_3d(camera_up(camera),forwardVectorAxis,forwardVectorAngle),np.asarray([0.0,1.0,0.0])))
    upVectorAngle = angle_vector_3d(np.asarray([0.0,1.0,0.0]), rotate_vector_3d(camera_up(camera),forwardVectorAxis,forwardVectorAngle))

    if (upVectorAngle > 0):
        for i in points:
            j = rotate_point_3d(i, upVectorAxis, upVectorAngle)
            i[3] = j[3]
            i[4] = j[4]
            i[5] = j[5]

    # jump over 0 to avoid zero division ¯\_(ツ)_/¯
    points[:,5][(points[:,5] < 0.001) & (points[:,5] > -0.001)] = -0.001 
    points[:,3] = (-hor_fov_adjust*points[:,3]/points[:,5] + 0.5*screenWidth).astype(np.int32)
    points[:,4] = (-ver_fov_adjust*points[:,4]/points[:,5] + 0.5*screenHeight).astype(np.int32)


@njit()
def dot_3d(arr1, arr2): 
    return arr1[0]*arr2[0] + arr1[1]*arr2[1] + arr1[2]*arr2[2]

def draw_model(mesh, frame, points, triangles, camera, light_dir, z_buffer, textured, texture_uv, texture_map, texture):
    global screenWidth
    global screenHeight

    points2 = points.copy()

    # make the points correct
    for i in points2:
        k = np.asarray([0.0,0.0,0.0,0.0,0.0,0.0])
        k[0] = i[0]
        k[1] = i[1]
        k[2] = i[2]
        j = mesh.transform_point(k)
        i[0] = j[3]
        i[1] = j[4]
        i[2] = j[5]

    text_size = [len(texture)-1, len(texture[0])-1]
    color_scale = 230/np.max(np.abs(points2[:,:3]))
    for index in range(len(triangles)):
        
        triangle = triangles[index]

        # Use Cross-Product to get surface normal
        vet1 = points2[triangle[1]][:3]  - points2[triangle[0]][:3]
        vet2 = points2[triangle[2]][:3] - points2[triangle[0]][:3]

        # backface culling with dot product between normal and camera ray
        normal = np.cross(vet1, vet2)
        normal = normal/np.sqrt(normal[0]*normal[0] + normal[1]*normal[1] + normal[2]*normal[2])
        #CameraRay = (points2[triangle[0]][:3] - camera[:3])/points2[triangle[0]][5]
        CameraRay = normalize_vector(points2[triangle[0]][:3] - camera[:3])

        # get projected 2d points for crude filtering of offscreen triangles
        xxs = [points2[triangle[0]][3],  points2[triangle[1]][3],  points2[triangle[2]][3]]
        yys = [points2[triangle[0]][4],  points2[triangle[1]][4],  points2[triangle[2]][4]]
        z_min = min([points2[triangle[0]][5],  points2[triangle[1]][5],  points2[triangle[2]][5]])

        # check valid values
        if filter_triangles(z_min, normal, CameraRay, xxs, yys):

            shade = 0.5*dot_3d(light_dir, normal) + 0.5 #  directional lighting

            proj_points = points2[triangle][:,3:]
            sorted_y = proj_points[:,1].argsort()

            start = proj_points[sorted_y[0]]
            middle = proj_points[sorted_y[1]]
            stop = proj_points[sorted_y[2]]

            x_slopes = get_slopes(start[0], middle[0], stop[0], start[1], middle[1], stop[1])

            if textured:
                z0, z1, z2 = 1/proj_points[0][2], 1/proj_points[1][2], 1/proj_points[2][2]
                uv_points = texture_uv[texture_map[index]]
                uv_points[0], uv_points[1], uv_points[2] = uv_points[0]*z0, uv_points[1]*z1, uv_points[2]*z2
                draw_text_triangles(frame, z_buffer, texture, proj_points, start, middle, stop, uv_points, x_slopes, shade, text_size, z0, z1, z2)

            else:
                color = shade*np.abs(points2[triangles[index][0]][:3])*color_scale + 25
                start[2], middle[2], stop[2] = 1/start[2], 1/middle[2], 1/stop[2]
                z_slopes = get_slopes(start[2], middle[2], stop[2], start[1], middle[1], stop[1])
                draw_flat_triangle(frame, z_buffer, color, start, middle, stop, x_slopes, z_slopes)

@njit()
def rotate(point, rot):
    return np.asarray([point[0],point[1] + rot])

@njit()
def draw_text_triangles(frame, z_buffer, texture, proj_points, start, middle, stop, uv_points, x_slopes, shade, text_size, z0, z1, z2):
    global screenWidth
    global screenHeight

    # barycentric denominator, based on https://codeplea.com/triangular-interpolation
    denominator = ((proj_points[1][1] - proj_points[2][1])*(proj_points[0][0] - proj_points[2][0]) +
                    (proj_points[2][0] - proj_points[1][0])*(proj_points[0][1] - proj_points[2][1]) + 1e-32)
    
    for y in range(max(0, start[1]), min(screenHeight, stop[1]+1)):
        x1 = start[0] + int((y-start[1])*x_slopes[0])
        if y < middle[1]:
            x2 = start[0] + int((y-start[1])*x_slopes[1])
        else:
            x2 = middle[0] + int((y-middle[1])*x_slopes[2])
        minx, maxx = max(0, min(x1, x2, screenWidth)), min(screenWidth, max(0, x1+1, x2+1))
        
        for x in range(minx, maxx):
            # barycentric weights
            w0 = ((proj_points[1][1]-proj_points[2][1])*(x - proj_points[2][0]) + (proj_points[2][0]-proj_points[1][0])*(y - proj_points[2][1]))/denominator
            w1 = ((proj_points[2][1]-proj_points[0][1])*(x - proj_points[2][0]) + (proj_points[0][0]-proj_points[2][0])*(y - proj_points[2][1]))/denominator
            w2 = 1 - w0 - w1

            z = 1/(w0*z0 + w1*z1 + w2*z2)
            u = ((w0*uv_points[0][0] + w1*uv_points[1][0] + w2*uv_points[2][0])*z)
            v = ((w0*uv_points[0][1] + w1*uv_points[1][1] + w2*uv_points[2][1])*z)

            if z < z_buffer[x, y] and min(u,v) >= 0 and max(u,v) < 1:
                z_buffer[x, y] = z
                frame[x, y] = shade*texture[int(u*text_size[0])][int(v*text_size[1])]

@njit()
def draw_flat_triangle(frame, z_buffer, color, start, middle, stop, x_slopes, z_slopes):
    global screenWidth
    global screenHeight

    for y in range(max(0, int(start[1])), min(screenHeight, int(stop[1]+1))):
        delta_y = y - start[1]
        x1 = start[0] + int(delta_y*x_slopes[0])
        z1 = start[2] + delta_y*z_slopes[0]

        if y < middle[1]:
            x2 = start[0] + int(delta_y*x_slopes[1])
            z2 = start[2] + delta_y*z_slopes[1]

        else:
            delta_y = y - middle[1]
            x2 = middle[0] + int(delta_y*x_slopes[2])
            z2 = middle[2] + delta_y*z_slopes[2]
        
        if x1 > x2: # lower x should be on the left
            x1, x2 = x2, x1
            z1, z2 = z2, z1

        xx1, xx2 = max(0, min(screenWidth, int(x1))), max(0, min(screenWidth, int(x2+1)))
        if xx1 != xx2:
            z_slope = (z2 - z1)/(x2 - x1 + 1e-32)
            if min(z_buffer[xx1:xx2, y]) == 1e32: # check z buffer, fresh pixels
                z_buffer[xx1:xx2, y] = 1/((np.arange(xx1, xx2)-x1)*z_slope + z1)
                frame[xx1:xx2, y] = color

            else:
                for x in range(xx1, xx2):
                    z = 1/(z1 + (x - x1)*z_slope + 1e-32) # retrive z
                    if z < z_buffer[x][y]: # check z buffer
                        z_buffer[x][y] = z
                        frame[x, y] = color

@njit()
def get_slopes(num_start, num_middle, num_stop, den_start, den_middle, den_stop):
    slope_1 = (num_stop - num_start)/(den_stop - den_start + 1e-32) # + 1e-32 avoid zero division ¯\_(ツ)_/¯
    slope_2 = (num_middle - num_start)/(den_middle - den_start + 1e-32)
    slope_3 = (num_stop - num_middle)/(den_stop - den_middle + 1e-32)

    return np.asarray([slope_1, slope_2, slope_3])

@njit()
def filter_triangles(z_min, normal, CameraRay, xxs, yys): #TODO replace filtering with proper clipping
    # only points on +z, facing the camera, check triangle bounding box

    # and max(xxs) >= 0 and min(xxs) < screenWidth and max(yys) >= 0 and min(yys) < screenHeight
    
    if z_min > 0 and dot_3d(normal, CameraRay) < 0:
        return True
    else:
        return False     

# interpolation for direction
# not sure if this is how slerp is supposed to be done but ah well
def slerp_vector_3d(a,b,t):
    rotationAxis = normalize_vector(cross_vector(a,b))
    rotationAngle = angle_vector_3d(a,b)

    return rotate_vector_3d(a,rotationAxis, rotationAngle * t)

# linearly interpolate from one point to another, using parameter t
def lerp_vector_2d(a, b, t):
    return np.asarray([a[0] + (b[0]-a[0]) * t, a[1] + (b[1]-a[1]) * t])

def add_vector_2d(a, b):
    return np.asarray([a[0] + b[0],a[1] + b[1]])

def subtract_vector_2d(a, b):
    return np.asarray([a[0] - b[0], a[1] - b[1]])

# local vectors of the camera
def camera_forward(camera):
    return np.asarray([camera[3],camera[4],camera[5]])
def camera_up(camera):
    return np.asarray([camera[6],camera[7],camera[8]])
def camera_right(camera):
    crossProduct = normalize_vector(cross_vector(camera_forward(camera), camera_up(camera)))
    return np.asarray([-crossProduct[0],-crossProduct[1],-crossProduct[2]])

def length_vector(a):
    return np.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])

def angle_vector_3d(a, b):
    dp = dot_3d(a,b)
    la = length_vector(a)
    lb = length_vector(b)

    return np.acos((dp) / (la * lb))

def cross_vector(a,b):
    return np.asarray([a[1]*b[2] - a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]])

def normalize_vector(a):
    l = length_vector(a)

    return np.asarray([a[0]/l,a[1]/l,a[2]/l])

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
                vertices.append(splitted[1:4] + [1,1,1]) # aditional spaces for projection

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

    if len(texture_uv) > 0 and len(texture_map) > 0:
        textured = True
        texture_uv = np.asarray(texture_uv).astype(float)
        texture_uv[:,1] = 1 - texture_uv[:,1] # apparently obj textures are upside down
        texture_map = np.asarray(texture_map).astype(int) - 1 # adjust indexes to start with 0
        
    else:
        texture_uv, texture_map = np.asarray(texture_uv), np.asarray(texture_map)
        textured = False 
    
    return vertices, triangles, texture_uv, texture_map, textured