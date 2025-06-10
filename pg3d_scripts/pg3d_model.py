import numpy as np
from . import pg3d_math as m
from . import pg3d as engine
from . import pg3d_utils as utils
import pygame as pg

class Model:
    _registry = []

    def __init__(self, name, path_obj, path_texture, tags, color):

        # the interesting thing is, python doesn't care if you initialize variables outside of the __init__ function
        # if you say they exist here, they exist
        
        # in fact, if you DON'T say they exist here and DO above, they will be treated as global variables (for some reason)
        # by that I mean there will be one instance of the variable for ALL models, not for each

        self.name = name

        # there are some tags that the engine looks for, like the 'physics' tag
        self.tags = tags

        # the world and local transforms of an object
        # both the same, since obj doesn't start out as a child
        self.localTransform = ModelTransform(np.asarray([0.0,0.0,0.0]), np.asarray([0.0,0.0,1.0]), np.asarray([0.0,1.0,0.0]), np.asarray([1.0,1.0,1.0]))
        self.worldTransform = ModelTransform(np.asarray([0.0,0.0,0.0]), np.asarray([0.0,0.0,1.0]), np.asarray([0.0,1.0,0.0]), np.asarray([1.0,1.0,1.0]))

        self._registry.append(self)
        # points are stored using nine numbers
        # the first three is the point as it appears in the mesh file
        # the next three is the point as it appears in the scene, RELATIVE TO THE CAMERA
        # the final three is the point as it appears projected onto the screen
        self.points, self.triangles, self.texture_uv, self.texture_map =  utils.read_obj(path_obj)
        self.texture = pg.surfarray.array3d(pg.image.load(path_texture))

        # average of all vertices
        self.rawMidpoint = self.calculateRawMidpoint()

        # physics stuff, not a part of the transform class
        self.angularVelocity = np.asarray([0.0,0.0,0.0])
        self.linearVelocity = np.asarray([0.0,0.0,0.0])

        # whether to render the object or not
        # normally this is set through the level system, the object inherits the variable from the parent level
        # IF THE OBJECT IS IN A LEVEL, you cannot manually enable/disable it BUT YOU CAN IF IT'S NOT IN A LEVEL by calling show()/hide()
        self.shouldBeDrawn = True

        # whether the collider, etc. should interact
        self.shouldBePhysics = True

        # models use dictionaries as per-object variables
        # this allows the storage of things like collider data
        # (there is a collider TAG too, because it makes it easier to search through objects (objects have less tags than data), but that might change)
        self.data = {}

        self.parent = None

        # I thought at first that we don't need a reference to children, but it does make syncing everything easier
        # (this is a list of objects)
        self.children = []
        # how many parents does this object have?
        # not a child --> 0
        # child of an object --> 1
        # child of an object, which itself is a child of an object --> 2

        # it's used to sort the heirarchy so that transforms can be applied properly
        self.childLevel = 0

        # for textured models, the color is multiplied by the texture
        # for colored models, the color applies to all geometry
        self.color = color

        # either opaque or alphaclip, changes how the renderer deals with transparency
        self.textureType = "opaque"

    # only used for particle objects, advances the sprite to create an animation
    def checkAnimation(self):
        # time between frames is in millis
        if (pg.time.get_ticks() > self.data["last_frame_time"] + self.data["time_between_frames"]):
            self.data["current_frame_index"] += 1
            if (self.data["current_frame_index"] >= len(self.data["animation_frames"])):
                if (self.data["destroy_when_finish"]):
                    engine.destroyObject(self)
                    return True
                elif(self.data["loop_animation"]): # restarting the animation
                    self.data["current_frame_index"] = 0
                else:
                    self.remove_tag("animated") # just leaving the object as-is, on the last frame
            else:
                self.setTexture(self.data["animation_frames"][self.data["current_frame_index"]])
                self.data["last_frame_time"] = pg.time.get_ticks()

        return False
    
    # changes the texture on the model
    def setTexture(self, texture_path):
        self.texture = pg.surfarray.array3d(pg.image.load(texture_path))

    # switching between texture types ***********
    def setTextureType(self, newType):
        self.textureType = newType
    def setAsOpaque(self):
        self.textureType = "opaque"
    def setAsTransparent(self):
        self.textureType = "alphaclip"
    # ********************************************

    # transform stuff ********************************************

    # set the transform based on the parent
    def syncTransformWithParent(self):
        # DO NOT CHANGE THE LOCAL TRANSFORM

        if (self.parent == None): 
            # can't really do much without a parent lol
            # but we do need to make sure the world and local transforms are the same
            self.worldTransform.copy(self.localTransform)

            return
        
        # okay, so we do actually have a parent cuz the func didnt return

        # first, copy the local to the world
        self.worldTransform.copy(self.localTransform)
        self.worldTransform.add_self_to_other(self.parent.worldTransform) # as mentioned basically everywhere, the parent's world transform HAS TO BE DONE FIRST

    def setParent(self, otherObject):
        if (otherObject == None):
            # if the object WAS a child, remove all refs
            if (self.parent != None):
                self.parent.children.pop(self)

            self.parent = None
            self.childLevel = 0
            # that way, you can call setParent(None) to make it not a child
            return
        self.parent = otherObject
        self.childLevel = otherObject.childLevel + 1

        self.syncChildren()

        otherObject.children.append(self)

        engine.refreshHeirarchy()
    # again, so I don't have to call 2 functions
    def syncChildren(self):
        self.syncChildrenLevels()
        self.syncChildrenTransforms()
    # loop through all children and refresh their child level, 
    # which is to say how far down a family tree they are
    def syncChildrenLevels(self):
        for i in range(len(self.children)):
            self.children[i].childLevel = self.childLevel + 1
            self.children[i].syncChildrenLevels()
    # loop through all children and refresh their transforms
    def syncChildrenTransforms(self):
        for i in self.children:
            i.syncTransformWithParent()
            i.syncChildrenTransforms()

    # random boolean stuff ********************************************
    def show(self):
        self.shouldBeDrawn = True
    def hide(self):
        self.shouldBeDrawn = False

    def disablePhysicsInteraction(self):
        self.shouldBePhysics = False
    def enablePhysicsInteraction(self):
        self.shouldBePhysics = True
    # ********************************************

    # adding a variable to this object
    def add_data(self, key, value):
        # update the entry in the dictionary
        self.data[key] = value

    # figure out where in world space the midpoint of the object is
    # the midpoint is used for collision detection and stuff
    def calculateRawMidpoint(self):
        toReturn = np.asarray([0.0,0.0,0.0])

        for i in self.points:
            toReturn[0] += i[0] / len(self.points)
            toReturn[1] += i[1] / len(self.points)
            toReturn[2] += i[2] / len(self.points)

        return toReturn
    # the midpoint, in world space
    # (provided the raw midpoint has already been calculated, which it should be cuz thats done in init())
    def midpoint(self):
        rawMidpoint = np.asarray([self.rawMidpoint[0],self.rawMidpoint[1],self.rawMidpoint[2],0.0,0.0,0.0])
        return self.transform_point(rawMidpoint)
    
    def getMidpointAsVector(self):
        mp = self.midpoint()
        return np.asarray([mp[3],mp[4],mp[5]])

    # whether the tags array has a given tag
    def hasTag(self, tag):
        for i in self.tags:
            if (i == tag):
                return True
            
        return False
    
    def add_tag(self, tagName):
        if (m.array_has_item(self.tags, tagName)):
            return
        self.tags.append(tagName)

    def remove_tag(self, tagName):
        if (m.array_has_item(self.tags, tagName)):
            # pop whatever tag
            self.tags.pop(engine.index_in_array(self.tags, tagName))
    
    # COLLISION STUFF ****************************************************************************************

    # same as below, but for sphere colliders
    def closest_point_sphere(self, foreignPoint):
        rmpoint= self.midpoint()
        worldSpaceMidpoint = np.asarray([rmpoint[3],rmpoint[4],rmpoint[5]])

        localPoint = np.asarray([foreignPoint[0] - worldSpaceMidpoint[0],foreignPoint[1] - worldSpaceMidpoint[1],foreignPoint[2] - worldSpaceMidpoint[2]])

        return m.normalize_3d(localPoint) * self.data["collider_bounds"]
    
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
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.worldTransform.forward
            
        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.worldTransform.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.worldTransform.up)
        
        if upRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        colliderBounds = self.data["collider_bounds"]

        # now, clamp it 
        # this function takes in (point, point point) and (box, box, box)
        clampedPoint = m.clamp_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),colliderBounds)

        rotatedPoint = clampedPoint

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
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward)
        rotatedPoint = localPoint
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(localPoint, forwardRotationAxis, forwardRotationAngle)
        else:
            forwardRotationAxis = self.worldTransform.forward

        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.worldTransform.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.worldTransform.up)

        if upRotationAngle > 0:
            rotatedPoint = m.rotate_vector_3d(rotatedPoint, upRotationAxis, upRotationAngle)

        return m.point_in_box_3d(rotatedPoint,np.asarray([0.0,0.0,0.0]),bounds)
        
        # there's no reason to un-transform the point, we're only trying to find whether its in the box
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
 
    # "cheap" trigger functions **********************************************************************
    # im calling them cheap because they don't actually check trigger interaction, 
    # they check whether the other object's position is in this objects trigger
    # so its a really weird system that you really would never use unless you're REALLY starved for frames

    def is_triggered_cheap(self):
        # assuming there IS actually a trigger collider when this function is called
        
        # also, the only objects that are detected in trigger colliders are ones with the "interact" tag
        # ALSO, COLLIDERS are the only thing that triggers a trigger collider, not other trigger colliders
        possibleObjects = engine.getObjectsWithTag("interact")

        # loop through each, and check to see if the closest point on their collider
        for i in possibleObjects:
            if (not i.shouldBePhysics):
                    continue
            
            if (self.is_point_inside(i.worldTransform.position, self.data["trigger_bounds"])):
                return True
            
        return False
    
    def is_triggered_sphere_cheap(self):
        possibleObjects = engine.getObjectsWithTag("interact")

        for i in possibleObjects:
            if (not i.shouldBePhysics):
                    continue
                
            # using worldTransform instead of midpoint
            if (m.length_3d(i.worldTransform.position - self.worldTransform.position) < self.data["trigger_bounds"]):
                return True
            
        return False
    # **********************************************************************

    # actual trigger functions **********************************************************************
    # this function checks trigger interactions with OTHER SPHERE TRIGGERS ONLY
    # it should ONLY BE CALLED FOR OBJECTS THAT HAVE A SPHERE TRIGGER THEMSELVES
    def is_triggered_sphere_only(self):
        possibleObjects = engine.getObjectsWithTag("interact")

        for i in possibleObjects:
            if (not i.shouldBePhysics):
                    continue
                
            # as said above, we're only checking objects that have sphere triggers on them
            # if the object doesn't have this tag, it doesn't have a sphere collider
            if (not m.array_has_item(i.tags, "sphere_trigger")):
                continue
            
            if (m.length_3d(i.getMidpointAsVector() - self.getMidpointAsVector()) < self.data["trigger_bounds"] + i.data["trigger_bounds"]):
                return True
            
        return False
    
    def get_triggered_objects_sphere_only(self):
        possibleObjects = engine.getObjectsWithTag("interact")

        actualObjects = []

        for i in possibleObjects:
            if (not i.shouldBePhysics):
                    continue
                
            # as said above, we're only checking objects that have sphere triggers on them
            # if the object doesn't have this tag, it doesn't have a sphere collider
            if (not m.array_has_item(i.tags, "sphere_trigger")):
                continue
            
            if (m.length_3d(i.getMidpointAsVector() - self.getMidpointAsVector()) < self.data["trigger_bounds"] + i.data["trigger_bounds"]):
                actualObjects.append(i)
        
        return actualObjects
    
    # ****************************************************************************************

    def add_box_collider(self,boundsX,boundsY,boundsZ):
        self.add_tag("box_collider")

        self.add_data("collider_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    # since you won't be able to have sphere AND box colliders on the same object,
    # we can just use the same data entry, passing in only one value
    def add_sphere_collider(self,radius):
        self.add_tag("sphere_collider")

        self.add_data("collider_bounds", np.asarray([radius]))

    def add_box_trigger(self,boundsX,boundsY,boundsZ):
        self.add_tag("box_trigger")

        self.add_data("trigger_bounds", np.asarray([boundsX,boundsY,boundsZ]))

    def add_sphere_trigger(self,radius):
        self.add_tag("sphere_trigger")

        self.add_data("trigger_bounds", np.asarray([radius]))

    # im honestly not super worried about performance for the below functions, 
    # because really how often are you messing with collider bounds?

    # ONLY CALLED FOR OBJECTS WITH SPHERE COLLIDER
    # this function is just easier than setting the data entry, it's really only for user-friendlyness
    def set_collider_radius(self, r):
        self.data["collider_bounds"] = r
    # ONLY SPHERE TRIGGER
    def set_trigger_radius(self, r):
        self.data["trigger_bounds"] = r

    # ONLY BOX COLLIDER
    def set_collider_bounds(self, x, y, z):
        self.data["collider_bounds"][0] = x
        self.data["collider_bounds"][1] = y
        self.data["collider_bounds"][2] = z
    # ONLY BOX TRIGGER
    def set_trigger_bounds(self, x, y, z):
        self.data["trigger_bounds"][0] = x
        self.data["trigger_bounds"][1] = y
        self.data["trigger_bounds"][2] = z

    # when messing with models, please use the functions and don't mess with the variables themselves!
    # ESPECIALLY WITH TRANSFORM-COMPONENT STUFF, it makes life easier (and doesn't break the heirarchy)

    def add_velocity(self,x,y,z):
        self.linearVelocity[0] += x
        self.linearVelocity[1] += y
        self.linearVelocity[2] += z

    def add_velocity_vector(self,new_velocity_vector):
        self.linearVelocity[0] += new_velocity_vector[0]
        self.linearVelocity[1] += new_velocity_vector[1]
        self.linearVelocity[2] += new_velocity_vector[2]

    def set_velocity(self,x,y,z):
        self.linearVelocity[0] = x
        self.linearVelocity[1] = y
        self.linearVelocity[2] = z
    
    def set_velocity_vector(self,new_velocity_vector):
        self.linearVelocity[0] = new_velocity_vector[0]
        self.linearVelocity[1] = new_velocity_vector[1]
        self.linearVelocity[2] = new_velocity_vector[2]

    # set position to some numbers
    # this sets the LOCAL POSITION
    def set_local_position(self, x, y, z):
        self.localTransform.position[0] = x
        self.localTransform.position[1] = y
        self.localTransform.position[2] = z

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()
    
    # translate with individual numbers
    def add_local_position(self, x, y, z):
        self.localTransform.position[0] += x
        self.localTransform.position[1] += y
        self.localTransform.position[2] += z

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    # rotate around any axis, using a CC angle
    # why tf did I decide to put angle first??
    def rotate(self, angle, axis):
        newForward = m.rotate_vector_3d(self.localTransform.forward, axis, angle)
        newUp = m.rotate_vector_3d(self.localTransform.up, axis, angle)

        if (np.abs(newForward[0]) > 0 or np.abs(newForward[1]) > 0 or np.abs(newForward[2]) > 0):
            self.localTransform.forward[0] = newForward[0]
            self.localTransform.forward[1] = newForward[1]
            self.localTransform.forward[2] = newForward[2]

        if (np.abs(newUp[0]) > 0 or np.abs(newUp[1]) > 0 or np.abs(newUp[2]) > 0):
            self.localTransform.up[0] = newUp[0]
            self.localTransform.up[1] = newUp[1]
            self.localTransform.up[2] = newUp[2]

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def get_forward(self):
        return self.localTransform.forward

    def get_up(self):
        return self.localTransform.up

    def set_local_forward(self, forward_vector):
        appliedRotationAxis = m.normalize_3d(m.cross_3d(self.localTransform.forward, forward_vector))
        appliedRotationAngle = m.angle_3d(self.localTransform.forward, forward_vector)

        if (appliedRotationAngle > 0.001 and appliedRotationAngle < np.pi - 0.001):
            self.localTransform.forward = m.rotate_vector_3d(self.localTransform.forward, appliedRotationAxis, appliedRotationAngle)
            self.localTransform.up = m.rotate_vector_3d(self.localTransform.up, appliedRotationAxis, appliedRotationAngle)

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def set_local_up(self, forward_vector):
        appliedRotationAxis = m.normalize_3d(m.cross_3d(self.localTransform.up, forward_vector))
        appliedRotationAngle = m.angle_3d(self.localTransform.up, forward_vector)

        if (appliedRotationAngle > 0.01):
            self.localTransform.forward = m.rotate_vector_3d(self.localTransform.forward, appliedRotationAxis, appliedRotationAngle)
            self.localTransform.up = m.rotate_vector_3d(self.localTransform.up, appliedRotationAxis, appliedRotationAngle)

            self.syncTransformWithParent() # refreshing the world transform
            self.syncChildren()

    # set scale with three numbers
    def set_scale(self, a, b, c):
        self.localTransform.scale[0] = a
        self.localTransform.scale[1] = b
        self.localTransform.scale[2] = c

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def set_scale_vector(self, new_scale_vector):
        self.localTransform.scale[0] += new_scale_vector[0]
        self.localTransform.scale[1] += new_scale_vector[1]
        self.localTransform.scale[2] += new_scale_vector[2]

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    # same as above, but with one number
    def set_scale_to_number(self, n):
        self.localTransform.scale[0] = n
        self.localTransform.scale[1] = n
        self.localTransform.scale[2] = n

        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()
    # not usually gonna be used, but hey? someone might want it
    def add_scale(self, a, b, c):
        self.localTransform.scale[0] += a
        self.localTransform.scale[1] += b
        self.localTransform.scale[2] += c
        
        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def add_scale_vector(self, vector_to_add):
        self.localTransform.scale[0] += vector_to_add[0]
        self.localTransform.scale[1] += vector_to_add[1]
        self.localTransform.scale[2] += vector_to_add[2]
        
        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def add_number_to_scale(self, n):
        self.localTransform.scale[0] += n
        self.localTransform.scale[1] += n
        self.localTransform.scale[2] += n
        
        self.syncTransformWithParent() # refreshing the world transform
        self.syncChildren()

    def transform_point(self, point):
        # scale first
        point[3] = point[0] * self.worldTransform.scale[0]
        point[4] = point[1] * self.worldTransform.scale[1]
        point[5] = point[2] * self.worldTransform.scale[2]

        # then rotation
        forwardRotationAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward))
        forwardRotationAngle = m.angle_3d(np.asarray([0.0,0.0,1.0]), self.worldTransform.forward)
        if (forwardRotationAngle <= 0):
            forwardRotationAxis = self.worldTransform.forward
        rotatedUpAxis = m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]), forwardRotationAxis, forwardRotationAngle)
        upRotationAxis = m.normalize_3d(m.cross_3d(rotatedUpAxis, self.worldTransform.up))
        upRotationAngle = m.angle_3d(rotatedUpAxis, self.worldTransform.up)
        rotatedPoint = point
        if forwardRotationAngle > 0:
            rotatedPoint = m.rotate_point_3d(point, forwardRotationAxis, forwardRotationAngle)
        if upRotationAngle > 0:
            rotatedPoint = m.rotate_point_3d(rotatedPoint, upRotationAxis, upRotationAngle)
        point[3] = rotatedPoint[3]
        point[4] = rotatedPoint[4]
        point[5] = rotatedPoint[5]

        # then position
        point[3] += self.worldTransform.position[0]
        point[4] += self.worldTransform.position[1]
        point[5] += self.worldTransform.position[2]

        return point
    
# essentially a unity transform component:
# since objects now have parents and children, every object will have a WORLD set of transforms and a set of LOCAL transforms
class ModelTransform:
    # midpoint isn't on here because the world-space midpoint is really the only one that'll be used

    # velocity isn't on here because what even is local velocity anyways?

    # scale, then rotation, then position is applied, in that order, when transforming
    position = np.asarray([0.0,0.0,0.0])
    forward = np.asarray([0.0,0.0,1.0])
    up = np.asarray([0.0,1.0,0.0])
    scale = np.asarray([1.0,1.0,1.0])

    def __init__(self, pos, f, u, scl):
        self.position = pos

        self.forward = f
        self.up = u

        self.scale = scl

    # literally just ctrl+c, ctrl+v the data from another transform
    def copy(self, otherTransform):
        self.position[0] = otherTransform.position[0]
        self.position[1] = otherTransform.position[1]
        self.position[2] = otherTransform.position[2]

        self.scale[0] = otherTransform.scale[0]
        self.scale[1] = otherTransform.scale[1]
        self.scale[2] = otherTransform.scale[2]

        self.forward[0] = otherTransform.forward[0]
        self.forward[1] = otherTransform.forward[1]
        self.forward[2] = otherTransform.forward[2]

        self.up[0] = otherTransform.up[0]
        self.up[1] = otherTransform.up[1]
        self.up[2] = otherTransform.up[2]

    def get_right(self):
        f = self.forward
        u = self.up

        crossProduct = m.normalize_3d(m.cross_3d(f, u))

        # negative, because we're using a left-handed coordinate system
        return np.asarray([-crossProduct[0],-crossProduct[1],-crossProduct[2]])
    
    # this function is a bit weird
    # it adds THE CURRENT TRANSFORM DATA to ANOTHER SET OF TRANSFORM DATA
    # (not adding another set to this set)

    # this is how world-space transforms are calculated:
    # the local transform is added to the PARENT'S world transform

    # since we're looping over all objects starting with parents and going down,
    # the parent's world space transform will have already been calculated

    def add_self_to_other(self, otherTransform):
        # positions can just be added (because a + b = b + a)

        otherRight = otherTransform.get_right()

        xVector = np.asarray([otherRight[0] * self.position[0], otherRight[1] * self.position[0], otherRight[2] * self.position[0]])
        yVector = np.asarray([otherTransform.up[0] * self.position[1], otherTransform.up[1] * self.position[1], otherTransform.up[2] * self.position[1]])
        zVector = np.asarray([otherTransform.forward[0] * self.position[2], otherTransform.forward[1] * self.position[2], otherTransform.forward[2] * self.position[2]])

        self.position[0] = otherTransform.position[0] + xVector[0] + yVector[0] + zVector[0]
        self.position[1] = otherTransform.position[1] + xVector[1] + yVector[1] + zVector[1]
        self.position[2] = otherTransform.position[2] + xVector[2] + yVector[2] + zVector[2]

        # scales are multiplied, because if this one is 2 and the other one is 4, 
        # then it should be 2 times 4, or 8

        # can just be applied as an offset (because, like addition, a x b = b x a)
        self.scale[0] *= otherTransform.scale[0]
        self.scale[1] *= otherTransform.scale[1]
        self.scale[2] *= otherTransform.scale[2]

        # rotations are the tricky part
        # I have to figure out how rotated the forward and up vectors are from the other's, 
        # then store that as a rotational offset of sorts, then apply that rotation to the other's vectors to get the final rotations

        # so the first question is, what two axis and angles get us from the world to this one?

        # rotating from the OTHER forward vector to THIS one
        forwardVectorAxis = m.normalize_3d(m.cross_3d(np.asarray([0.0,0.0,1.0]),self.forward))
        forwardVectorAngle = m.angle_3d(self.forward,np.asarray([0.0,0.0,1.0]))

        if (forwardVectorAngle == 0):
            forwardVectorAxis = np.asarray([0.0,0.0,1.0])

            self.forward[0] = otherTransform.forward[0]
            self.forward[1] = otherTransform.forward[1]
            self.forward[2] = otherTransform.forward[2]
        else:
            # rotate BOTH THE FORWARD AND UP VECTORS using this rotation
            newForward = m.rotate_vector_3d(otherTransform.forward, forwardVectorAxis, forwardVectorAngle)

            self.forward[0] = newForward[0]
            self.forward[1] = newForward[1]
            self.forward[2] = newForward[2]

        # FROM THERE, rotating from the OTHER UP VECTOR to THIS ONE
        # the rotation axis will just end up being the new forward vector (if all goes well)
        # but we CANNOT use the new forward vector, the cross product sometimes being negative IS VITAL
        upVectorAxis = m.normalize_3d(m.cross_3d(   m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]),forwardVectorAxis,forwardVectorAngle)        ,self.up))
        upVectorAngle = m.angle_3d(self.up,   m.rotate_vector_3d(np.asarray([0.0,1.0,0.0]),forwardVectorAxis,forwardVectorAngle)        )

        # rotate ONLY THE UP VECTOR, since rotating the forward vector won't do anything

        newUp = m.rotate_vector_3d(m.rotate_vector_3d(otherTransform.up,forwardVectorAxis,forwardVectorAngle), upVectorAxis, upVectorAngle)

        self.up[0] = newUp[0]
        self.up[1] = newUp[1]
        self.up[2] = newUp[2]

        # that SHOULD be everything (lol)