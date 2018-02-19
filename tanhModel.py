import numpy as np
import lpUtils
from cvxopt import matrix,solvers

class TanhModel:
	def __init__(self, modelParam, g_cc, g_fwd, numStages):
		# gradient of tanh -- y = tanh(modelParam*x)
		self.modelParam = modelParam
		self.g_cc = g_cc
		self.g_fwd = g_fwd
		self.numStages = numStages
		self.xs = []
		self.ys = []
		self.zs = []
		for i in range(numStages*2):
			self.xs.append("x" + str(i))
			self.ys.append("y" + str(i))
			self.zs.append("z" + str(i))

	'''
	takes in non-symbolic python values
	calculates the tanhFun of val
	'''
	def tanhFun(self,val):
		return np.tanh(self.modelParam*val)
		#return -(exp(a*val) - exp(-a*val))/(exp(a*val) + exp(-a*val))

	'''
	takes in non-symbolic python values
	calculates the derivative of tanhFun of val
	'''
	def tanhFunder(self,val):
		den = np.cosh(self.modelParam*val)*np.cosh(self.modelParam*val)
		#print "den ", den
		return self.modelParam/den



	'''
	when Vlow < 0 and Vhigh > 0, take the convex hull of 
	two triangles (one formed on the left side and one on the
		right side)
	'''
	def triangleConvexHullBounds(self, Vin, Vout, Vlow, Vhigh):
		if (Vlow >= 0 and Vhigh >= 0) or (Vlow <= 0 and Vhigh <= 0):
			print "Vlow and Vhigh are in the same quadrants"
			return
		VZero = 0.0
		tanhFunVlow = self.tanhFun(Vlow)
		tanhFunVhigh = self.tanhFun(Vhigh)
		tanhFunVZero = self.tanhFun(VZero)
		dLow = self.tanhFunder(Vlow)
		dHigh = self.tanhFunder(Vhigh)
		dZero = self.tanhFunder(0)
		cLow = tanhFunVlow - dLow*Vlow
		cHigh = tanhFunVhigh - dHigh*Vhigh
		cZero = tanhFunVZero - dZero*0

		#print "dHigh ", dHigh, " cHigh ", cHigh

		if abs(dLow - dZero) < 1e-8:
			leftIntersectX = Vlow
			leftIntersectY = tanhFunVlow
		else:
			leftIntersectX = (cZero - cLow)/(dLow - dZero)
			leftIntersectY = dLow*leftIntersectX + cLow
		#print "dLow, ", dLow, "dZero", dZero
		#print "leftIntersectX ", leftIntersectX, " leftIntersectY ", leftIntersectY
		#print "Vlow ", Vlow, "Vhigh ", Vhigh
		if abs(dHigh - dZero) < 1e-8:
			rightIntersectX = Vhigh
			rightIntersectY = tanhFunVhigh
		else:
			rightIntersectX = (cZero - cHigh)/(dHigh - dZero)
			rightIntersectY = dHigh*rightIntersectX + cHigh

		overallConstraint = "1 " + Vin + " >= " + str(Vlow) + "\n"
		overallConstraint += "1 " + Vin + " <= " + str(Vhigh) + "\n"

		# Construct constraints from the convex hull of (Vlow, tanhFunVlow),
		# (leftIntersectX, leftIntersectY), (0,0), (rightIntersectX, rightIntersectY),
		# and (Vhigh, tanhFunVhigh)
		# Use jarvis algorithm from https://www.geeksforgeeks.org/convex-hull-set-1-jarviss-algorithm-or-wrapping/
		origPoints = [(Vlow, tanhFunVlow),(leftIntersectX, leftIntersectY),
					(0,0),(rightIntersectX, rightIntersectY), (Vhigh, tanhFunVhigh)]
		points = []
		for point in origPoints:
			if point not in points:
				points.append(point)
		#print "points"
		#print points
		leftMostIndex = 0
		convexHullIndices = []
		nextIndex = leftMostIndex
		iters = 0
		while(iters == 0 or nextIndex != leftMostIndex):
			convexHullIndices.append(nextIndex)
			otherIndex = (nextIndex + 1)%len(points)
			for i in range(len(points)):
				orientation = ((points[i][1] - points[nextIndex][1]) * (points[otherIndex][0] - points[i][0]) - 
					(points[i][0] - points[nextIndex][0]) * (points[otherIndex][1] - points[i][1]))
				if orientation < 0:
					otherIndex = i
			nextIndex = otherIndex
			iters += 1

		#print "convexHull", convexHullIndices
		for ci in range(len(convexHullIndices)):
			i = convexHullIndices[ci]
			ii = convexHullIndices[(ci + 1)%len(convexHullIndices)]
			grad = (points[ii][1] - points[i][1])/(points[ii][0] - points[i][0])
			c = points[i][1] - grad*points[i][0]
			if points[i] == (Vlow, tanhFunVlow) and points[ii] == (rightIntersectX, rightIntersectY):
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " >= "+str(c) + "\n"
			elif points[i] == (rightIntersectX, rightIntersectY) and points[ii] == (Vhigh, tanhFunVhigh):
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " >= "+str(c) + "\n"
			elif points[i] == (Vhigh, tanhFunVhigh) and points[ii] == (leftIntersectX, leftIntersectY):
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " <= "+str(c) + "\n"
			elif points[i] == (leftIntersectX, leftIntersectY) and points[ii] == (Vlow, tanhFunVlow):
				#print "grad", grad, "c", c
				#print "dLow", dLow, "cLow", cLow
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " <= "+str(c) + "\n"

			elif points[i] == (Vhigh, tanhFunVhigh) and points[ii] == (Vlow, tanhFunVlow):
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " <= "+str(c) + "\n"

			elif points[i] == (Vlow, tanhFunVlow) and points[ii] == (Vhigh, tanhFunVhigh):
				#print "coming here?"
				overallConstraint += "1 "+Vout + " + " +str(-grad) + " " + Vin + " >= "+str(c) + "\n"

		#print "overallConstraint", overallConstraint
		return overallConstraint


	def triangleBounds(self, Vin, Vout, Vlow, Vhigh):
		tanhFunVlow = self.tanhFun(Vlow)
		tanhFunVhigh = self.tanhFun(Vhigh)
		dLow = self.tanhFunder(Vlow)
		dHigh = self.tanhFunder(Vhigh)
		diff = Vhigh - Vlow
		if(diff == 0):
			diff = 1e-10
		dThird = (tanhFunVhigh - tanhFunVlow)/diff
		cLow = tanhFunVlow - dLow*Vlow
		cHigh = tanhFunVhigh - dHigh*Vhigh
		cThird = tanhFunVlow - dThird*Vlow

		overallConstraint = "1 " + Vin + " >= " + str(Vlow) + "\n"
		overallConstraint += "1 " + Vin + " <= " + str(Vhigh) + "\n"

		#print "dLow ", dLow, "dHigh ", dHigh, "dThird ", dThird
		#print "cLow ", cLow, "cHigh ", cHigh, "cThird ", 

		#print "a ", a, " Vlow ", Vlow, " Vhigh ", Vhigh

		if self.modelParam > 0:
			if Vlow >= 0 and Vhigh >=0:
				return overallConstraint + "1 "+ Vout + " + " +str(-dThird) + " " + Vin + " >= "+str(cThird)+"\n" +\
				"1 "+Vout + " + " +str(-dLow) + " " + Vin + " <= "+str(cLow)+"\n" +\
				"1 "+Vout + " + " +str(-dHigh) + " " + Vin + " <= "+str(cHigh) + "\n"

			elif Vlow <=0 and Vhigh <=0:
				return overallConstraint + "1 "+ Vout + " + " +str(-dThird) + " " + Vin + " <= "+str(cThird)+"\n" +\
				"1 "+Vout + " + " +str(-dLow) + " " + Vin + " >= "+str(cLow)+"\n" +\
				"1 "+Vout + " + " +str(-dHigh) + " " + Vin + " >= "+str(cHigh) + "\n"

		elif self.modelParam< 0:
			if Vlow <= 0 and Vhigh <=0:
				return overallConstraint + "1 "+Vout + " + " +str(-dThird) + " " + Vin + " >= "+str(cThird)+"\n" +\
				"1 "+Vout + " + " +str(-dLow) + " " + Vin + " <= "+str(cLow)+"\n" +\
				"1 "+Vout + " + " +str(-dHigh) + " " + Vin + " <= "+str(cHigh) + "\n"
			elif Vlow >=0 and Vhigh >=0:
				return overallConstraint + "1 "+Vout + " + " +str(-dThird) + " " + Vin + " <= "+str(cThird)+"\n" +\
				"1 "+Vout + " + " +str(-dLow) + " " + Vin + " >= "+str(cLow)+"\n" +\
				"1 "+Vout + " + " +str(-dHigh) + " " + Vin + " >= "+str(cHigh) + "\n"
				
	def oscNum(self,V):
		lenV = len(V)
		Vin = [V[i % lenV] for i in range(-1,lenV-1)]
		Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
		VoutFwd = [self.tanhFun(Vin[i]) for i in range(lenV)]
		VoutCc = [self.tanhFun(Vcc[i]) for i in range(lenV)]
		return (VoutFwd, VoutCc, [((self.tanhFun(Vin[i])-V[i])*self.g_fwd
				+(self.tanhFun(Vcc[i])-V[i])*self.g_cc) for i in range(lenV)])


	'''Get jacobian of rambus oscillator at V
	'''
	def jacobian(self,V):
		lenV = len(V)
		Vin = [V[i % lenV] for i in range(-1,lenV-1)]
		Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
		jac = np.zeros((lenV, lenV))
		for i in range(lenV):
			jac[i,i] = -(self.g_fwd + self.g_cc)
			jac[i,(i-1)%lenV] = self.g_fwd * self.tanhFunder(V[(i-1)%lenV])
			jac[i,(i + lenV/2) % lenV] = self.g_cc * self.tanhFunder(V[(i + lenV/2) % lenV])

		return jac

	def jacobianInterval(self,bounds):
		lowerBound = bounds[:,0]
		upperBound = bounds[:,1]
		lenV = len(lowerBound)
		jac = np.zeros((lenV, lenV,2))
		zerofwd =  self.g_fwd * self.tanhFunder(0)
		zerocc = self.g_cc * self.tanhFunder(0)
		for i in range(lenV):
			jac[i,i,0] = -(self.g_fwd + self.g_cc)
			jac[i,i,1] = -(self.g_fwd + self.g_cc)
			gfwdVal1 = self.g_fwd * self.tanhFunder(lowerBound[(i-1)%lenV])
			gfwdVal2 = self.g_fwd * self.tanhFunder(upperBound[(i-1)%lenV])
			if lowerBound[(i-1)%lenV] < 0 and upperBound[(i-1)%lenV] > 0:
				jac[i,(i-1)%lenV,0] = min(gfwdVal1,gfwdVal2,zerofwd)
				jac[i,(i-1)%lenV,1] = max(gfwdVal1,gfwdVal2,zerofwd)
			else:
				jac[i,(i-1)%lenV,0] = min(gfwdVal1,gfwdVal2)
				jac[i,(i-1)%lenV,1] = max(gfwdVal1,gfwdVal2)
			gccVal1 = self.g_cc * self.tanhFunder(lowerBound[(i + lenV/2) % lenV])
			gccVal2 = self.g_cc * self.tanhFunder(upperBound[(i + lenV/2) % lenV])
			if lowerBound[(i + lenV/2) % lenV] < 0 and upperBound[(i + lenV/2) % lenV] > 0:
				jac[i,(i + lenV/2) % lenV,0] = min(gccVal1,gccVal2,zerocc)
				jac[i,(i + lenV/2) % lenV,1] = max(gccVal1,gccVal2,zerocc)
			else:
				jac[i,(i + lenV/2) % lenV,0] = min(gccVal1,gccVal2)
				jac[i,(i + lenV/2) % lenV,1] = max(gccVal1,gccVal2)
		return jac

	def linearConstraints(self, hyperRectangle):
		solvers.options["show_progress"] = False
		allConstraints = ""
		lenV = self.numStages*2

		allConstraints = ""
		for i in range(lenV):
			fwdInd = (i-1)%lenV
			ccInd = (i+lenV/2)%lenV
			#print "fwdInd ", fwdInd, " ccInd ", ccInd
			#print "hyperRectangle[fwdInd][0]", hyperRectangle[fwdInd][0], "hyperRectangle[fwdInd][1]", hyperRectangle[fwdInd][1]
			triangleClaimFwd = ""
			if hyperRectangle[fwdInd,0] < 0 and hyperRectangle[fwdInd,1] > 0:
				triangleClaimFwd += self.triangleConvexHullBounds(self.xs[fwdInd],self.ys[i],hyperRectangle[fwdInd,0],hyperRectangle[fwdInd,1])
			else:
				triangleClaimFwd += self.triangleBounds(self.xs[fwdInd],self.ys[i],hyperRectangle[fwdInd,0],hyperRectangle[fwdInd,1])
			allConstraints += triangleClaimFwd

			triangleClaimCc = ""
			if hyperRectangle[ccInd,0] < 0 and hyperRectangle[ccInd,1] > 0:
				triangleClaimCc += self.triangleConvexHullBounds(self.xs[ccInd],self.zs[i],hyperRectangle[ccInd,0],hyperRectangle[ccInd,1])
			else:
				triangleClaimCc += self.triangleBounds(self.xs[ccInd],self.zs[i],hyperRectangle[ccInd,0],hyperRectangle[ccInd,1])
			allConstraints += triangleClaimCc
				
			allConstraints += str(self.g_fwd) + " " + self.ys[i] + " + " + str(-self.g_fwd-self.g_cc) + \
			" " + self.xs[i] + " + " + str(self.g_cc) + " "  + self.zs[i] + " >= 0.0\n"
			allConstraints += str(self.g_fwd) + " " + self.ys[i] + " + " + str(-self.g_fwd-self.g_cc) + \
			" " + self.xs[i] + " + " + str(self.g_cc) + " "  + self.zs[i] + " <= 0.0\n"

		'''allConstraintList = allConstraints.splitlines()
		allConstraints = ""
		for i in range(len(allConstraintList)):
			allConstraints += allConstraintList[i] + "\n"
		print "numConstraints ", len(allConstraintList)
		print "allConstraints"
		print allConstraints'''
		variableDict, A, B = lpUtils.constructCoeffMatrices(allConstraints)
		newHyperRectangle = np.copy(hyperRectangle)
		feasible = True
		for i in range(lenV):
			#print "min max ", i
			minObjConstraint = "min 1 " + self.xs[i]
			maxObjConstraint = "max 1 " + self.xs[i]
			Cmin = lpUtils.constructObjMatrix(minObjConstraint,variableDict)
			Cmax = lpUtils.constructObjMatrix(maxObjConstraint,variableDict)
			minSol = solvers.lp(Cmin,A,B)
			maxSol = solvers.lp(Cmax,A,B)
			if (minSol["status"] == "primal infeasible" or minSol["status"] == "dual infeasible")  and (maxSol["status"] == "primal infeasible" or maxSol["status"] == "dual infeasible"):
				feasible = False
				break
			else:
				if minSol["status"] == "optimal":
					newHyperRectangle[i,0] = minSol['x'][variableDict[self.xs[i]]] - 1e-6
				if maxSol["status"] == "optimal":
					newHyperRectangle[i,1] = maxSol['x'][variableDict[self.xs[i]]] + 1e-6

		return [feasible, newHyperRectangle]


