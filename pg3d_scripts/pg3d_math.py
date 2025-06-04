import numpy as np
from numba import njit

@njit()
def clamp(val, lower, upper):
    return min(max(val, lower), upper)

def average_point_3d(list):
    toReturn = np.asarray([0.0,0.0,0.0])
    for i in list:
        toReturn[0] += i[3] / len(list)
        toReturn[1] += i[4] / len(list)
        toReturn[2] += i[5] / len(list)

    return toReturn

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