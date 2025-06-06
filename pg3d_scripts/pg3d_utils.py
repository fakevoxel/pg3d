import numpy as np
import random

# generates a string of random number characters of a given length
# used for particle system hashcodes, but those were removed so its just here now
def random_number_string(length):
    toReturn = ""

    for i in range(length):
        toReturn += str(random.randint(0, 9))

    return toReturn

# ********  MESH helpers:       ********

# there's something weird going on here with the winding order of triangles
# I'm not complaining bc it works, but its still weird
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