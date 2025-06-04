import numpy as np
from . import pg3d_math as m
from numba import njit

renderConfig = None

# possible rendering modes
# "texture" is just normal rendering
# "uv" is showing the uv coordinates
# "wireframe" shows lines
# "states" shows how the triangles are being rendered using colors:
    # green is a normal triangle
    # red is 
    # blue is
renderingModes = ["texture","uv","wireframe","states"]

# possible background modes
backGroundModes = ["solid color","skybox"]

# the color that the wireframe renderer uses
# this is NOT passed into draw_triangle(), instead it can be set before calling
wireframeColor = np.asarray([255,0,0]).astype('uint8')

# this piece of code is brought to you by: me being tired of passing variables around
class RenderingConfig:
    # wireframe, uv coords, texture, stuff like that
    renderingMode = ""
    # skybox? solid color?
    backgroundMode = ""
    # do I not render away-facing faces?
    backfaceCulling = False
    # the render-resolution
    screenWidth = 0
    screenHeight = 0
    # the fov
    verticalFOV = 0
    horizontalFOV = 0
    # projection adjustments (aka magic), stored so as to make calculations easier
    hor_fov_adjust = 0
    ver_fov_adjust = 0

    # display resolution (scaled to this)
    screenWidth_actual = 0
    screenHeight_actual = 0

    def __init__(self, rMode, bfCulling, sWidth, sHeight, vFov, hFov, hFovA, vFovA, bMode, sWA, sHA):
        self.renderingMode = rMode
        self.backgroundMode = bMode
        self.backfaceCulling = bfCulling
        self.screenWidth = sWidth
        self.screenHeight = sHeight
        self.verticalFOV = vFov
        self.horizontalFOV = hFov
        self.hor_fov_adjust = hFovA
        self.ver_fov_adjust = vFovA
        self.screenWidth_actual = sWA
        self.screenHeight_actual = sHA

def init(w, h, horfov, vertfov, horfovA, vertfovA, r, b, swa, sha):
    global renderConfig

    renderConfig = RenderingConfig(r, False, w, h, vertfov, horfov, horfovA, vertfovA, b, swa, sha)


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

# z-buffering is still used EVEN during wireframe
def draw_model(mesh, frame, points, triangles, cameraTransform, light_dir, z_buffer, texture_uv, texture_map, texture, color, textureType):
    global renderConfig

    textureTypeIndex = 0

    if (textureType == "alphaclip"):
        textureTypeIndex = 1

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

            draw_triangle(renderConfig.screenWidth, renderConfig.screenHeight, frame, z_buffer, texture, projpoints, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderConfig.renderingMode, np.asarray([1,1,1]), renderConfig.backfaceCulling, textureTypeIndex)
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

            # null value
            v0state = 0
            v1state = 0
            v2state = 0

            # add any <0 vertices to a list
            # using the same index convention as normal points
            if (z0 <= 0):
                v0state = -1
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[0][3],projpoints[0][4],projpoints[0][5],projpoints[0][6],projpoints[0][7],projpoints[0][8]]))
                problemUV.append(rawUVs[0])
            else:
                v0state = 1
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[0][3],projpoints[0][4],projpoints[0][5],projpoints[0][6],projpoints[0][7],projpoints[0][8]]))
                goodUV.append(rawUVs[0])
            if (z1 <= 0):
                # vertex 1 is not valid
                v1state = -1
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[1][3],projpoints[1][4],projpoints[1][5],projpoints[1][6],projpoints[1][7],projpoints[1][8]]))
                problemUV.append(rawUVs[1])
            else:
                # vertex 1 is valid
                v1state = 1
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[1][3],projpoints[1][4],projpoints[1][5],projpoints[1][6],projpoints[1][7],projpoints[1][8]]))
                goodUV.append(rawUVs[1])
            if (z2 <= 0):
                v2state = -1
                problemVertices.append(np.asarray([0.0,0.0,0.0,projpoints[2][3],projpoints[2][4],projpoints[2][5],projpoints[2][6],projpoints[2][7],projpoints[2][8]]))
                problemUV.append(rawUVs[2])
            else:
                v2state = 1
                goodVertices.append(np.asarray([0.0,0.0,0.0,projpoints[2][3],projpoints[2][4],projpoints[2][5],projpoints[2][6],projpoints[2][7],projpoints[2][8]]))
                goodUV.append(rawUVs[2])

            if (len(problemVertices) == 2):
                # first case, where two vertices are behind
                # here we will end up with one clipped triangle

                # getting the intersect point in camera-relative space
                # using 3, 4, 5 because we want cam-relative

                # here is our triangle as-is
                if (v1state == 1):
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
                else:
                    p1 = np.asarray([goodVertices[0][3],goodVertices[0][4],goodVertices[0][5]])
                    p2 = np.asarray([problemVertices[0][3],problemVertices[0][4],problemVertices[0][5]])
                    p3 = np.asarray([problemVertices[1][3],problemVertices[1][4],problemVertices[1][5]])

                    parameter = (0.01 - p2[2]) / (p1[2] - p2[2])
                    intersect1 = m.add_3d(p2, np.asarray([(p1[0]-p2[0]) * parameter,(p1[1]-p2[1]) * parameter,(p1[2]-p2[2]) * parameter]))
                    goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                    goodUV.append(np.asarray([problemUV[0][0] + (goodUV[0][0] - problemUV[0][0]) * parameter, problemUV[0][1] + (goodUV[0][1] - problemUV[0][1]) * parameter]))

                    parameter = (0.01 - p3[2]) / (p1[2] - p3[2])
                    intersect1 = m.add_3d(p3, np.asarray([(p1[0]-p3[0]) * parameter,(p1[1]-p3[1]) * parameter,(p1[2]-p3[2]) * parameter]))
                    goodVertices.append(np.asarray([0.0,0.0,0.0,intersect1[0],intersect1[1],intersect1[2],0.0,0.0,0.0]))
                    goodUV.append(np.asarray([problemUV[1][0] + (goodUV[0][0] - problemUV[1][0]) * parameter, problemUV[1][1] + (goodUV[0][1] - problemUV[1][1]) * parameter]))

                # the good vertices array will have items with ONLY SIX VALUES, representing the cam-relative points and then the projected points
                # however, right now the projected part is all zeros

                goodVertices[1][6] = (-renderConfig.hor_fov_adjust*goodVertices[1][3]/np.abs(goodVertices[1][5]) + 0.5*renderConfig.screenWidth).astype(np.int32)
                goodVertices[1][7] = (-renderConfig.ver_fov_adjust*goodVertices[1][4]/np.abs(goodVertices[1][5]) + 0.5*renderConfig.screenHeight).astype(np.int32)
                goodVertices[1][8] = goodVertices[1][5] 

                goodVertices[2][6] = (-renderConfig.hor_fov_adjust*goodVertices[2][3]/np.abs(goodVertices[2][5]) + 0.5*renderConfig.screenWidth).astype(np.int32)
                goodVertices[2][7] = (-renderConfig.ver_fov_adjust*goodVertices[2][4]/np.abs(goodVertices[2][5]) + 0.5*renderConfig.screenHeight).astype(np.int32)
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

                draw_triangle(renderConfig.screenWidth, renderConfig.screenHeight, frame, z_buffer, texture, goodVertices, goodUV, minX, maxX, minY, maxY, text_size, z0, z1, z2,renderConfig.renderingMode, np.asarray([1,1,1]), renderConfig.backfaceCulling, textureTypeIndex)
            elif (len(problemVertices) == 1):
                # here only one vertex is an issue
                # the procedure is similar, but we end up with two triangles

                if (v1state == -1):
                    rColor = np.asarray([0,255,0])
                elif (v0state == -1):
                    rColor = np.asarray([255,0,0])
                elif (v2state == -1):
                    rColor = np.asarray([0,0,255])

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

                goodVertices[2][6] = (-renderConfig.hor_fov_adjust*goodVertices[2][3]/np.abs(goodVertices[2][5]) + 0.5*renderConfig.screenWidth).astype(np.int32)
                goodVertices[2][7] = (-renderConfig.ver_fov_adjust*goodVertices[2][4]/np.abs(goodVertices[2][5]) + 0.5*renderConfig.screenHeight).astype(np.int32)
                goodVertices[2][8] = goodVertices[2][5] 

                goodVertices[3][6] = (-renderConfig.hor_fov_adjust*goodVertices[3][3]/np.abs(goodVertices[3][5]) + 0.5*renderConfig.screenWidth).astype(np.int32)
                goodVertices[3][7] = (-renderConfig.ver_fov_adjust*goodVertices[3][4]/np.abs(goodVertices[3][5]) + 0.5*renderConfig.screenHeight).astype(np.int32)
                goodVertices[3][8] = goodVertices[3][5] 

                # this is where we have to turn our array of four points into two triangles

                if (v1state == -1):
                    good1 = np.asarray([goodVertices[0],goodVertices[2],goodVertices[1]])
                    good2 = np.asarray([goodVertices[1],goodVertices[2],goodVertices[3]])
                else:
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

                if (v1state == -1):
                    uv1 = np.asarray([goodUV[0] * z01,goodUV[2] * z11,goodUV[1] * z21])
                    uv2 = np.asarray([goodUV[1] * z02,goodUV[2] * z12,goodUV[3] * z22])
                else:
                    uv1 = np.asarray([goodUV[0] * z01,goodUV[1] * z11,goodUV[2] * z21])
                    uv2 = np.asarray([goodUV[1] * z02,goodUV[3] * z12,goodUV[2] * z22])

                draw_triangle(renderConfig.screenWidth, renderConfig.screenHeight, frame, z_buffer, texture, good1, uv1, minX1, maxX1, minY1, maxY1, text_size, z01, z11, z21,renderConfig.renderingMode, np.asarray([1,1,1]), renderConfig.backfaceCulling, textureTypeIndex)
                draw_triangle(renderConfig.screenWidth, renderConfig.screenHeight, frame, z_buffer, texture, good2, uv2, minX2, maxX2, minY2, maxY2, text_size, z02, z12, z22,renderConfig.renderingMode, np.asarray([1,1,1]), renderConfig.backfaceCulling, textureTypeIndex)


        #  we do nothing if the triangle is all behind (state == 1), we just skip those

# z-buffering NOT used for wireframe, it is for the others though
@njit()
def draw_triangle(sW, sH, frame, z_buffer, texture, proj_points, uv_points, minX, maxX, minY, maxY, text_size, z0, z1, z2, renderMode, color, cullBack, textureType):
    global wireframeColor

    renderColor = color
    
    # looping through every pixel in the bounding box that the triangle represents
    # we limit this box to the edges of the screen, because we don't care about anything else

    # because of these restrictions we don't need any further checks for making sure the x and y are valid
    for y in range(max(minY, 0), min(maxY, sH)):
        for x in range(max(minX, 0), min(maxX, sW)):
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
            if ((dotab >= 0) and (dotbc >= 0) and (dotca >= 0)):
                inTriangle = True
            else:
                inTriangle = False

            if (inTriangle):
                a0 = dotbc / 2
                a1 = dotca / 2
                a2 = dotab / 2
                
                sum = (a0 + a1 + a2)
                if (sum > 0):
                    invAreaSum = 1 / (a0 + a1 + a2)
                    w0 = a0 * invAreaSum
                    w1 = a1 * invAreaSum
                    w2 = a2 * invAreaSum
                else:
                    w0 = 1
                    w1 = 0
                    w2 = 0  

                # sinze z0,z1, and z2 are all 1/z at some point, this value will also be 1 / z
                z = w0*z0 + w1*z1 + w2*z2
                u = ((w0*uv_points[0][0] + w1*uv_points[1][0] + w2*uv_points[2][0])*(1/z + 0.0001))
                v = ((w0*uv_points[0][1] + w1*uv_points[1][1] + w2*uv_points[2][1])*(1/z + 0.0001))

                # z needs to be greater than the value at the z buffer, meaning 1 / z needs to be less
                # also make sure the u and v coords are valid, they need to be [0..1]
                if z > z_buffer[x, y] and min(u,v) >= 0 and max(u,v) <= 1:
                    # showing the u and v coords as a color, not the actual texture just yet
                    if (renderMode == "states"):
                        frame[x, y] = renderColor

                        # z buffer stores values of 1 / z
                        z_buffer[x, y] = z
                    elif (renderMode == "uv"):
                        frame[x, y] = np.asarray([u*255,v*255,0]).astype('uint8')

                        # z buffer stores values of 1 / z
                        z_buffer[x, y] = z
                    elif (renderMode == "texture"):
                        pixelColor = texture[int(u*text_size[0] + 1)][int(v*text_size[1])]
                        # ALL objects in the scene are rendered using alpha-clip, so if there's no color it's transparent
                        if (textureType == 1):
                            if (pixelColor[0] > 0 and pixelColor[1] > 0 and pixelColor[2] > 0):
                                frame[x, y] = pixelColor * color

                                # z buffer stores values of 1 / z
                                z_buffer[x, y] = z
                        else:
                            frame[x, y] = pixelColor * color

                        # z buffer stores values of 1 / z
                        z_buffer[x, y] = z