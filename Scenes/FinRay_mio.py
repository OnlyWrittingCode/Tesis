import Sofa
import numpy as np
import Geometries.Constants as Constants

import os

ThisPath = os.path.dirname(os.path.abspath(__file__))+'/'
path = os.path.dirname(os.path.abspath(__file__))+'/Geometries/'
PathGmshGeometries = os.path.dirname(os.path.abspath(__file__))+'/../Geometries/Gmsh/'



#Guardar datos del sensor magnetico



class Controller(Sofa.Core.Controller):   
    
    def __init__(self, *args, **kwargs):
        Sofa.Core.Controller.__init__(self, *args, **kwargs)
        print(" Python::__init__::" + str(self.name.value))
        
        self.RootNode = kwargs['RootNode']
        print(kwargs['RootNode'])
        #print(self.FinRayNode)
        #self.FinRayNode.getRootNode()
        print('RootNode: ' + repr(self.RootNode))
        print('RootNode: ' + repr(kwargs['RootNode']))
        
        self.ContactNode = kwargs['ContactNode']
        self.ContactNodeMO = kwargs["ContactNodeMO"]
        self.SphereROI = kwargs['SphereROI']
        self.SphereROI2 = kwargs['SphereROI2']
        self.FPA = kwargs['FPA']
        self.CableEffector = kwargs['CableEffector']
        self.ContactColIdx = 3
        self.ContactRowIdx = 3
        self.DesiredLengthPercentage = 1.0
        # self.Dirty2CleanIdxList = kwargs['Dirty2CleanIdxList']
        self.mlx_info_path = os.path.join(ThisPath, 'MlxInfo.txt')
        
    
    def mapCapCoordinatesTo3DCoords(self):
        WeightList = np.ones(Constants.NRowsTactile*Constants.NColsTactile)        
        IdxList = [
        [self.ContactColIdx, self.ContactRowIdx],
        [self.ContactColIdx, self.ContactRowIdx+1],
        [self.ContactColIdx+1, self.ContactRowIdx],
        [self.ContactColIdx+1, self.ContactRowIdx+1]]
        NContactPoints = 4
        print(f"WeightList:{WeightList}" )
        print(f"IdxList:{IdxList}" )
        Sum = np.array([0,0,0])
        for Idx in IdxList:
            LinearIdx = Idx[0] + Idx[1]*Constants.NColsTactile 
            print(f"LinearIdx: {LinearIdx}")
            Coords3D =  np.array(self.ContactNodeMO.position.value[LinearIdx]*1/NContactPoints) # calculate "barycentric" coordinates
            Sum = Sum + Coords3D
        
        self.SphereROI.centers = [Sum]
        self.SphereROI2.centers = [Sum] 
        self.FPA.indices = self.SphereROI.indices

        
    def onAnimateEndEvent(self, eventType):
        print("AnimateBeginEvent")
        
        self.mapCapCoordinatesTo3DCoords()
        self.mlx_info_path = os.path.join(ThisPath, 'MlxInfo.txt')

        try:
            with open(self.mlx_info_path, 'r') as file:
                content = file.read().strip()
                mm_value = float(content)
                print(f"Valor del potenciómetro leído (mm): {mm_value}")
        except Exception as e:
            print(f"Error al leer el archivo MlxInfo.txt: {e}")
            mm_value = 0.0  # Valor por defecto

        # Definimos los rangos
        pot_min_mm = 0.0   # Valor mínimo en mm
        pot_max_mm = 11.0  # Valor máximo en mm (aproximado)
        percentage_max = 1.0  # Porcentaje máximo (reposo)
        percentage_min = 0.4  # Porcentaje mínimo (flexión máxima con 11 mm)

        # Limitamos mm_value al rango esperado
        if mm_value < pot_min_mm:
            mm_value = pot_min_mm
        if mm_value > pot_max_mm:
            mm_value = pot_max_mm

        # Calcular DesiredLengthPercentage
        # Queremos una relación lineal decreciente:
        # 0 mm = 1.0, 11 mm = 0.3
        # Fórmula lineal: Desired = max - ( (mm_value - pot_min_mm) / (pot_max_mm - pot_min_mm) ) * (max - min)
        self.DesiredLengthPercentage = percentage_max - ((mm_value - pot_min_mm) / (pot_max_mm - pot_min_mm)) * (percentage_max - percentage_min)

        print(f"DesiredLengthPercentage ajustado: {self.DesiredLengthPercentage}")

        # Actualizar el desiredLength del CableEffector
        self.CableEffector.desiredLength.value = self.CableEffector.cableInitialLength.value * self.DesiredLengthPercentage
        print(f"CableEffector.desiredLength actualizado: {self.CableEffector.desiredLength.value}")

         # -----------------------------------------
        # Nuevo bloque para leer y mostrar Coord.txt
        # Ajusta la ruta si es necesario. Suponemos que está un nivel arriba.
        try:
            WeightedAvg = np.loadtxt(ThisPath + '../Coord.txt')
            x_sensor = WeightedAvg[0]
            y_sensor = WeightedAvg[1]
            print(f"Coordenadas leídas de Coord.txt: x={x_sensor}, y={y_sensor}")

            # Calcular ContactRowIdx a partir de y_sensor
            self.ContactRowIdx = int(round(1 + (y_sensor*6.0/5.0)))
            if self.ContactRowIdx < 0:
                self.ContactRowIdx = 0
            if self.ContactRowIdx > 4:
                self.ContactRowIdx = 4

            # Calcular ContactColIdx a partir de x_sensor
            self.ContactColIdx = int(round(1 + (x_sensor*6.0/5.0)))
            if self.ContactColIdx < 0:
                self.ContactColIdx = 0
            if self.ContactColIdx > 4:
                self.ContactColIdx = 4

            print(f"ContactRowIdx ajustado: {self.ContactRowIdx}")
            print(f"ContactColIdx ajustado: {self.ContactColIdx}")
        except Exception as e:
            print(f"Error al leer o procesar Coord.txt: {e}") 
    # -----------------------------------------
    
    def onKeypressedEvent(self, c):
        pass
        key = c['key']

        if (key == "+" and self.ContactRowIdx<8): # if we have 8 rows, we allow only up to 7, because of the +1 index above
            self.ContactRowIdx += 1
        if (key == "-" and self.ContactRowIdx>1):
            self.ContactRowIdx -= 1            

        if (key == "6" and self.DesiredLengthPercentage<1): # if we have 8 rows, we allow only up to 7, because of the +1 index above
            self.DesiredLengthPercentage += 0.05
        if (key == "4" and self.ContactRowIdx>1):
            self.DesiredLengthPercentage -= 0.05

        print(f"self.ContactRowIdx: {self.ContactRowIdx}")
        
    
    def setDesiredSurfacePressureConstraints(self, Volumes): 

        #self.ForceBM.reinit()       
        
        #Volumes[0] = Volumes[0]*0.794718462  #using a correction factor here
        print('Desired volume changes (V1,V2,V3,V4): ' + str(Volumes))
#        self.SurfacePressureConstraint1.getData('value').value = self.SurfacePressureConstraint1.getData('initialCavityVolume').value - Volumes[0]
#        self.SurfacePressureConstraint2.getData('value').value = self.SurfacePressureConstraint2.getData('initialCavityVolume').value - Volumes[1]
#        self.SurfacePressureConstraint3.getData('value').value = self.SurfacePressureConstraint3.getData('initialCavityVolume').value - Volumes[2]
#      
  


def createScene(rootNode):
        		 
                rootNode.addObject('RequiredPlugin', pluginName='SoftRobots SofaOpenglVisual SofaSparseSolver SofaPreconditioner SoftRobots.Inverse')
                rootNode.addObject('BackgroundSetting', color='0 0 0')
                rootNode.addObject('VisualStyle', displayFlags='showVisualModels showBehaviorModels showCollisionModels hideBoundingCollisionModels hideForceFields showInteractionForceFields hideWireframe')
                rootNode.addObject('InteractiveCamera', name='c', orientation=[0.227029, -0.140615, -0.670453, 0.692227], position=[-139.753, -65.7326, 201.098], distance=354.42) #InteractiveCamera

                rootNode.addObject('FreeMotionAnimationLoop')
                rootNode.addObject("QPInverseProblemSolver", printLog=1, epsilon=0.1, maxIterations=1000,tolerance=1e-5)
                rootNode.gravity=[0,0,0]
                rootNode.dt = 0.02

                FinRay = rootNode.addChild('FinRay')
                
                FinRay.addObject('EulerImplicit', name='odesolver')#,rayleighStiffness=0.01)                
                FinRay.addObject('SparseLDLSolver', template="CompressedRowSparseMatrixMat3x3d")                      
                FinRay.addObject('MeshVTKLoader', name='loader', filename=path+'FinRay.vtk')                                
                FinRay.addObject('TetrahedronSetTopologyContainer', src='@loader', name='container')
                FinRay.addObject('TetrahedronSetGeometryAlgorithms')
                FinRay.addObject('MechanicalObject', name='TetrasMO', template='Vec3d', showIndices='false', showIndicesScale='10')
                FinRay.addObject('UniformMass', totalMass='0.1')
                FinRay.addObject('TetrahedronFEMForceField', template='Vec3d', name='FEM', method='large', poissonRatio=0.4,  youngModulus=18000)                         
                FinRay.addObject('BoxROI', name='boxROI', box=[-50, -5, -30,  50, 2, 30], drawBoxes=True, position="@tetras.rest_position", tetrahedra="@container.tetrahedra")
                FinRay.addObject('RestShapeSpringsForceField', points='@boxROI.indices', stiffness=1e12)                
                FinRay.addObject('LinearSolverConstraintCorrection')
                
                
                SphereROI = FinRay.addObject('SphereROI', centers=[[0,0,0]], radii=[[6]], drawSphere=False, drawTriangles=False)
                FPA = FinRay.addObject('ForcePointActuator', name="FPA", direction=[1,0,0], indices = SphereROI.indices, showForce=True, visuScale=0.2, template='Vec3d', printLog=True, minForce=0)                                                
                
                # Height = 30
                # PadSize = 50    
                # NumberOfThreads = 8 # Num*filas x Num*columnas

                # XCoords = np.linspace(0,PadSize,NumberOfThreads)
                # YCoords = np.linspace(0,PadSize,NumberOfThreads)

                # XCoordsCentered = XCoords-PadSize/2
                # YCoordsCentered = YCoords-PadSize/2
                # MeshGrid = np.meshgrid(XCoordsCentered, YCoordsCentered)
                # Coords = np.concatenate((MeshGrid[0].reshape((NumberOfThreads**2,1)),MeshGrid[1].reshape((NumberOfThreads**2,1)), np.ones((NumberOfThreads**2,1))*30),axis=1)
                # CoordsList = Coords.tolist()
                
                # print(Coordsself.ContactColIdx = int(round(1 + (x_sensor*6.0/5.0)))
                #---------------------------------
                # Goal and Position Effector
                #---------------------------------                                                
                
                # goal = rootNode.addChild('goal')
                # goal.addObject('EulerImplicitSolver', firstOrder=True)
                # goal.addObject('CGLinearSolver', iterations=100, tolerance=1e-5, threshold=1e-5)
                # goal.addObject('MechanicalObject', name='goalMO', position=[0, 0, Height-9])
                # goal.addObject('SphereCollisionModel', radius=3, group=3)
                # goal.addObject('UncoupledConstraintCorrection')

                ##########################################
                # Effector                               #
                ##########################################
                CablePoints = []
                
                NPoints = 20
                P0 = np.array([-Constants.GripperWidth, 0, Constants.Depth/2])
                P1 = np.array([Constants.WallThickness, Constants.GripperHeight, Constants.Depth/2])
                
                Vec = P1-P0
                Length = np.linalg.norm(Vec)
                Subdivision = np.linspace(0,1,NPoints)
                
                for u in Subdivision:
                    CablePoints.append((u*Vec+P0).tolist())
                    
                
                cable = FinRay.addChild('cable')
                cable.addObject('MechanicalObject', name='cable',
                                position=CablePoints)
                # cable.addObject('CableEffector', desiredLength=Length*.99, indices=list(range(NPoints//2,NPoints)), pullPoint=[Constants.GripperWidth, 0, Constants.Depth/2])
                CableEffector = cable.addObject('CableEffector', indices=[NPoints//3], pullPoint=[Constants.GripperWidth, 0, Constants.Depth/2])
                
                cable.addObject('BarycentricMapping')
                
                ##########################################
                # ContactNode                            #
                ##########################################
                
                
                
                CoordsList = []
                
                P0 = np.array([-Constants.GripperWidth, 0])
                P1 = np.array([-Constants.WallThickness, Constants.GripperHeight])
                
                Vec = P1-P0
                
                Length = np.linalg.norm(Vec)
                SubdivisionU = np.linspace(0,1,Constants.NRowsTactile)
                SubdivisionV = np.linspace(0,1,Constants.NColsTactile)
                expansion_factor = 2.0 
                for u_val in SubdivisionU:
                    for v_val in SubdivisionV:
                        Coord = np.append(u_val * Vec + P0, v_val * (Constants.Depth * expansion_factor))
                        CoordsList.append(Coord.tolist())
                
                ContactNode = FinRay.addChild("ContactNode")
                ContactNodeMO = ContactNode.addObject("MechanicalObject", position=CoordsList, showColor=[0,0,200], showObjectScale=10, showObject=True, showIndices=True)
                ContactNode.addObject("BarycentricMapping")

                #---------------------------------
                # Forces Visu 
                #---------------------------------       
                
                ForceAndVisualNode = FinRay.addChild('ForceAndVisualNode')                 
                ForceAndVisualNode.addObject('MeshSTLLoader', filename=path+"FinRay.stl", name="loader")                
                ForceAndVisualNode.addObject('OglModel', src="@loader", scale3d=[1, 1, 1])                
                ForceAndVisualNode.addObject('BarycentricMapping')
                SphereROI2 = ForceAndVisualNode.addObject('SphereROI', centers=[[0,0,0]], radii=[[8]], position="@OglModel.position", triangles="@OglModel.triangles", drawSphere=True, drawTriangles=True)
                # FPA = ForceAndVisualNode.addObject('ForcePointActuator', name="FPA", direction=[0,0,1], indices = SphereROI.indices, showForce=True,visuScale=0.2, template='Vec3d', printLog=True)                                                
                                
                rootNode.addObject(Controller(name="TouchController", 
                                              ContactNode=ContactNode,
                                              ContactNodeMO=ContactNodeMO, 
                                              RootNode=rootNode, 
                                              SphereROI=SphereROI,
                                              SphereROI2=SphereROI2,
                                              CableEffector=CableEffector,
                                              FPA=FPA))


                return rootNode