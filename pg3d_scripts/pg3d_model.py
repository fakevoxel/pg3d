import numpy as np
from . import pg3d_math as m
from . import pg3d as engine
from . import pg3d_utils as utils
import pygame as pg

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

    shouldBePhysics = True

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
        self.points, self.triangles, self.texture_uv, self.texture_map =  utils.read_obj(path_obj)
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

    def disablePhysicsInteraction(self):
        self.shouldBePhysics = False

    def enablePhysicsInteraction(self):
        self.shouldBePhysics = True

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
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.forward
            
        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.up)
        
        if upRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        colliderBounds = self.data["collider_bounds"]

        # now, clamp it 
        # this function takes in (point, point point) and (box, box, box)
        clampedPoint = m.clamp_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),colliderBounds)

        rotatedPoint = clampedPoint

        #print(str(clampedPoint + worldSpaceMidpoint) + "     " + str(foreignPoint))

        # UNROTATE THE POINT
        if upRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(clampedPoint, upRotationAxis, -upRotationAngle)
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(rotatedPoint, forwardRotationAxis, -forwardRotationAngle)

        # add the position back
        return np.asarray([rotatedPoint[0] + worldSpaceMidpoint[0],rotatedPoint[1] + worldSpaceMidpoint[1],rotatedPoint[2] + worldSpaceMidpoint[2]])
    
    def is_point_inside(self, foreignPoint, bounds):
        rmpoint= self.midpoint()
        worldSpaceMidpoint = np.asarray([rmpoint[3],rmpoint[4],rmpoint[5]])
        localPoint = np.asarray([foreignPoint[0] - worldSpaceMidpoint[0],foreignPoint[1] - worldSpaceMidpoint[1],foreignPoint[2] - worldSpaceMidpoint[2]])

        # now, we rotate it using the opposite rotation we would use to transform a point
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.forward

        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.up)

        if upRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        return m.point_in_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),bounds)
        
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

    def is_colliding(self):
        collidersInScene = engine.getObjectsWithTag("box_collider")

        # this comes out as a point (x,y,z) (x transformed, y transformed, z transformed)
        # it's in world space!
        returnMidpoint = self.midpoint()
        worldSpaceMidpoint = np.asarray([returnMidpoint[3],returnMidpoint[4],returnMidpoint[5]])

        for j in collidersInScene:

            # don't do anything if talking about the same object
            if (j.name == self.name):
                continue

            if (not j.shouldBePhysics):
                continue

            closestPointOnOther = j.closest_point(worldSpaceMidpoint)

            closestPointOnThis = self.closest_point(closestPointOnOther)

            if (m.length_3d(m.subtract_3d(closestPointOnOther, closestPointOnThis)) < 0.01):
                # this code only runs if the two points are the same (which happens if there's an intersection)

                return True
            
        return False

    def is_triggered(self):
        # assuming there IS actually a trigger collider when this function is called
        
        # also, the only objects that are detected in trigger colliders are ones with the "interact" tag
        # ALSO, COLLIDERS are the only thing that triggers a trigger collider, not other trigger colliders
        possibleObjects = engine.getObjectsWithTag("interact")

        # loop through each, and check to see if the closest point on their collider
        for i in possibleObjects:
            if (not i.shouldBePhysics):
                    continue
            
            if (self.is_point_inside(i.position, self.data["trigger_bounds"])):
                return True
            
        return False

    def add_box_collider(self,boundsX,boundsY,boundsZ):
        self.add_tag("box_collider")

        self.add_data("collider_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    def add_box_trigger(self,boundsX,boundsY,boundsZ):
        self.add_tag("box_trigger")

        self.add_data("trigger_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    def add_tag(self, tagName):
        if (m.array_has_item(self.tags, tagName)):
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
        newForward = m.rotate_vector_3d(self.forward, angle, axis)
        newUp = m.rotate_vector_3d(self.up, angle, axis)

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

        crossProduct = m.normalize_3d(m.cross_3d(f, u))
        
        return np.asarray([-crossProduct[0],-crossProduct[1],-crossProduct[2]])

    def set_forward(self, v):
        appliedRotationAxis = m.normalize_3d(m.cross_3d(self.forward, v))
        appliedRotationAngle = m.angle_3d(self.forward, v)

        if (appliedRotationAngle > 0.001 and appliedRotationAngle < np.pi - 0.001):
            self.forward = m.rotate_vector_3d(self.forward, appliedRotationAxis, appliedRotationAngle)
            self.up = m.rotate_vector_3d(self.up, appliedRotationAxis, appliedRotationAngle)

    def set_up(self, v):
        appliedRotationAxis = m.cross_3d(self.up, v)
        appliedRotationAngle = m.angle_3d(self.up, v)

        self.forward = m.rotate_vector_3d(self.forward, appliedRotationAxis, appliedRotationAngle)
        self.up = m.rotate_vector_3d(self.up, appliedRotationAxis, appliedRotationAngle)

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
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.forward)
        if (forwardRotationAngle <= 0):
            forwardRotationAxis = self.forward
        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.up)
        rotatedPoint = point
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_point_3d(point, forwardRotationAxis, forwardRotationAngle)
        if upRotationAngle > 0:
            rotatedPoint = m.rotate_point_3d(rotatedPoint, upRotationAxis, upRotationAngle)
        point[3] = rotatedPoint[3]
        point[4] = rotatedPoint[4]
        point[5] = rotatedPoint[5]

        # then position
        point[3] += self.position[0]
        point[4] += self.position[1]
        point[5] += self.position[2]

        return point