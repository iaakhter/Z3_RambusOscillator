# Itrat Ahmed Akhter
# CPSC 538G
# Final Project
# z3lib.py

'''
A library of functions that model the Rambus mobius ring oscillator in
Z3 so that Z3 can find the DC quilibrium points.
'''

from z3 import *
from numpy import *
import copy
import matplotlib.pyplot as plt
from mpmath import mp, iv

def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

'''
A function that returns the absolute value of x.
'''
def myAbs(x):
	return If(x >= 0,x,-x)


'''
takes in non-symbolic python values
calculates the tanhFun of val
'''
def tanhFun(a,val):
	return -tanh(a*val)
	#return -(exp(a*val) - exp(-a*val))/(exp(a*val) + exp(-a*val))

def invTanhFun(a,val):
	return -arctanh(val)/a

'''
takes in non-symbolic python values
calculates the derivative of tanhFun of val
'''
def tanhFunder(a,val):
	den = cosh(a*val)*cosh(a*val)
	#print "den ", den
	return -a/(cosh(a*val)*cosh(a*val))
	#return (-4.0*a)/((exp(a*val) + exp(-a*val)) * (exp(a*val) + exp(-a*val)))


'''simulate oscillation with python numberical values to check if the
z3 solutions make sense'''
def oscNum(V,a,g_cc,g_fwd = 1):
	lenV = len(V)
	Vin = [V[i % lenV] for i in range(-1,lenV-1)]
	Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
	VoutFwd = [tanhFun(a,Vin[i]) for i in range(lenV)]
	VoutCc = [tanhFun(a,Vcc[i]) for i in range(lenV)]
	return (VoutFwd, VoutCc, [((tanhFun(a,Vin[i])-V[i])*g_fwd
			+(tanhFun(a,Vcc[i])-V[i])*g_cc) for i in range(lenV)])


'''Get jacobian of rambus oscillator at V
'''
def getJacobian(V,a,g_cc,g_fwd = 1):
	lenV = len(V)
	Vin = [V[i % lenV] for i in range(-1,lenV-1)]
	Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
	jacobian = zeros((lenV, lenV))
	for i in range(lenV):
		jacobian[i,i] = -(g_fwd+g_cc)
		jacobian[i,(i-1)%lenV] = g_fwd*tanhFunder(a,V[(i-1)%lenV])
		jacobian[i,(i + lenV/2) % lenV] = g_cc*tanhFunder(a,V[(i + lenV/2) % lenV])

	return jacobian

def getJacobianInterval(bounds,a,g_cc,g_fwd=1):
	lowerBound = bounds[:,0]
	upperBound = bounds[:,1]
	lenV = len(lowerBound)
	jacobian = zeros((lenV, lenV,2))
	jacobian[:,:,0] = jacobian[:,:,0] 
	jacobian[:,:,1] = jacobian[:,:,1]
	for i in range(lenV):
		jacobian[i,i,0] = -(g_fwd+g_cc)
		jacobian[i,i,1] = -(g_fwd+g_cc)
		gfwdVal1 = g_fwd*tanhFunder(a,lowerBound[(i-1)%lenV])
		gfwdVal2 = g_fwd*tanhFunder(a,upperBound[(i-1)%lenV])
		jacobian[i,(i-1)%lenV,0] = min(gfwdVal1,gfwdVal2)
		jacobian[i,(i-1)%lenV,1] = max(gfwdVal1,gfwdVal2)
		gccVal1 = g_cc*tanhFunder(a,lowerBound[(i + lenV/2) % lenV])
		gccVal2 = g_cc*tanhFunder(a,upperBound[(i + lenV/2) % lenV])
		jacobian[i,(i + lenV/2) % lenV,0] = min(gccVal1,gccVal2)
		jacobian[i,(i + lenV/2) % lenV,1] = max(gccVal1,gccVal2)

	return jacobian

def triangleBounds(a, Vin, Vout, Vlow, Vhigh):
	tanhFunVlow = tanhFun(a,Vlow)
	tanhFunVhigh = tanhFun(a,Vhigh)
	dLow = tanhFunder(a,Vlow)
	dHigh = tanhFunder(a,Vhigh)
	diff = Vhigh - Vlow
	if(diff == 0):
		diff = 1e-10
	dThird = (tanhFunVhigh - tanhFunVlow)/diff
	cLow = tanhFunVlow - dLow*Vlow
	cHigh = tanhFunVhigh - dHigh*Vhigh
	cThird = tanhFunVlow - dThird*Vlow

	if Vlow <= 0 and Vhigh <=0:
		return Implies(And(Vin >= Vlow, Vin <= Vhigh),
						And(Vout >= dThird*Vin + cThird,
							Vout <= dLow*Vin + cLow,
							Vout <= dHigh*Vin + cHigh))

	elif Vlow >=0 and Vhigh >=0:
		return Implies(And(Vin >= Vlow, Vin <= Vhigh),
						And(Vout <= dThird*Vin + cThird,
							Vout >= dLow*Vin + cLow,
							Vout >= dHigh*Vin + cHigh))

	elif Vlow <= 0 and Vhigh >= 0:
		return Implies(And(Vin >= Vlow, Vin <= Vhigh),
						And(Vout <= dLow*Vin + cLow,
							Vout >= dHigh*Vin + cHigh))

def tangentTriangleBounds(a,Vin,Vout,point,Vpoint,low,high):
	tanhFunPoint = tanhFun(a,point)
	dPoint = tanhFunder(a,point)
	cPoint = tanhFunPoint - dPoint*point
	if point <= 0:
		claim1 =  Vout <= dPoint*Vin + cPoint
		if Vpoint <= tanhFun(a,point):
			lowVal = point
			highVal = invTanhFun(a,Vpoint)
			if lowVal < 0.0 and highVal > 0.0:
				highVal = 0.0
			diff = highVal - lowVal
			if diff == 0.0:
				diff = 1e-5
			#print "lowVal ", lowVal, " highVal ", highVal
			dSec = (tanhFun(a,highVal) - tanhFun(a,lowVal))/diff
			cSec = tanhFun(a,lowVal) - dSec*lowVal
			return And(triangleBounds(a, Vin, Vout, lowVal, highVal),
						triangleBounds(a, Vin, Vout, low,lowVal),
						triangleBounds(a, Vin, Vout, highVal, high))
			#return (Vout >= dSec*Vin + cSec)
		else:
			return claim1
	else:
		claim1 = Vout >= dPoint*Vin + cPoint
		if Vpoint <= tanhFun(a,point):
			return claim1
		else:
			lowVal = invTanhFun(a,Vpoint)
			highVal = point
			if lowVal < 0.0 and highVal > 0.0:
				lowVal = 0.0
			diff = highVal - lowVal
			if diff == 0.0:
				diff = 1e-5
			#print "lowVal ", lowVal, " highVal ", highVal
			dSec = (tanhFun(a,highVal) - tanhFun(a,lowVal))/diff
			cSec = tanhFun(a,lowVal) - dSec*lowVal
			return And(triangleBounds(a, Vin, Vout, lowVal, highVal),
						triangleBounds(a, Vin, Vout, low,lowVal),
						triangleBounds(a, Vin, Vout, highVal, high))
			#return (Vout <= dSec*Vin + cSec)

def trapezoidBounds(a,Vin,Vout, Vlow, Vhigh):
	tanhFunVlow = tanhFun(a,Vlow)
	tanhFunVhigh = tanhFun(a,Vhigh)
	dLow = tanhFunder(a,Vlow)
	dHigh = tanhFunder(a,Vhigh)
	diff = Vhigh - Vlow
	if(diff == 0):
		diff = 1e-10
	dThird = (tanhFunVhigh - tanhFunVlow)/diff
	cLow = tanhFunVlow - dLow*Vlow
	cHigh = tanhFunVhigh - dHigh*Vhigh
	cThird = tanhFunVlow - dThird*Vlow

	if Vlow <= 0:
		return Implies(Vin < Vlow, 
						And(Vout < dLow*Vin + cLow,
							Vout <= 1,
							Vout > tanhFunVlow))
	elif Vhigh >=0:
		return Implies(Vin > Vhigh, 
						And(Vout > dHigh*Vin + cHigh,
							Vout >= - 1,
							Vout <  tanhFunVhigh))



# Use triangle and trapezoid bounds for the constraints
# VlowVhighs indicate how triangle and trapezoid bounds are created
# to approximate the non linear solution.
# For example, VlowVhighs can be of the form [[[a,b,c,d],[e,f,g,h]],[[A,B,C,D],[E,F,G,H]]]
# This means that each voltage in V (V[0] or V[1] or V[2] or so on) is 
# constrained by triangles bound by [a,e] and by [b,f] and by [c,g] and by [d,h] and
# by [A,E] and by [B,F] and so on. The bounds are all in increasing order meaning that
# a < e = A < E, b < f = B < F and so on. Trapezoid bounds are applied 
# for voltages outside the bounds
def oscl(s,I,V,a,VlowVhighs,g_cc,g_fwd = 1):
	lenV = len(V)
	VoutFwd = RealVector('VoutFwd',lenV)
	VoutCc = RealVector('VoutCc',lenV)
	Vin = [V[i % lenV] for i in range(-1,lenV-1)]
	Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
	allVlowVhighs = []
	for i in range(lenV):
		allVlowVhighs.append(VlowVhighs)

	for i in range(lenV):
		# For each voltage in V, there are two inverters involved
		# Use all possible combinations of triangle bounds for those 
		# two inverters 
		for j in range(len(allVlowVhighs[i])):
			for k in range(len(allVlowVhighs[i])):
				boundin = allVlowVhighs[(i-1)%lenV][j]
				boundcc = allVlowVhighs[(i+lenV/2)%lenV][k]
				claimFwd = triangleBounds(a,Vin[i],VoutFwd[i],boundin[0][(i-1)%lenV],boundin[1][(i-1)%lenV])
				claimCc = triangleBounds(a,Vcc[i],VoutCc[i],boundcc[0][(i+lenV/2)%lenV],boundcc[1][(i+lenV/2)%lenV])
				s.add(claimFwd)
				s.add(claimCc)

				# Need trapezoid bounds for the left most and right most 
				# bounds
				if j==0:
					claimTrapFwd1 = trapezoidBounds(a, Vin[i], VoutFwd[i], boundin[0][i], boundin[1][i])
					s.add(claimTrapFwd1)
				if k==0:
					claimTrapCc1 = trapezoidBounds(a, Vcc[i], VoutCc[i], boundcc[0][i], boundcc[1][i])
					s.add(claimTrapCc1)
				if j==len(allVlowVhighs[i])-1:
					claimTrapFwd2 = trapezoidBounds(a, Vin[i], VoutFwd[i], boundin[0][i], boundin[1][i])
					s.add(claimTrapFwd2)
				if k==len(allVlowVhighs[i])-1:
					claimTrapCc2 = trapezoidBounds(a, Vcc[i], VoutCc[i], boundcc[0][i], boundcc[1][i])
					s.add(claimTrapCc2)

		s.add(I[i] == (VoutFwd[i] - V[i])*g_fwd + (VoutCc[i] - V[i])*g_cc)

# Use only the triangle bounds for the constraints (not the trapezoid bounds).
# hyperRectangles is a list of hyper rectangles and each triangle bound is constrained
# within a hyperrectangle
# Each voltage is only bound by the corresponding indices in hyperRectangles
# For example, hyperRectangles can be of the form [[[a,b,c,d],[e,f,g,h]],[[A,B,C,D],[E,F,G,H]]]. 
# This means that V[0] is constrained to be in the triangle bounded by [a,e] and that
# bounded by [A,E]. V[1] is constrained to be in in the triangle bounded by [b,f] and that
# bounded by [B,F] and so on.
def osclRefine(s,I,V,a,hyperRectangles,g_cc,g_fwd = 1):
	lenV = len(V)
	VoutFwd = RealVector('VoutFwd',lenV)
	VoutCc = RealVector('VoutCc',lenV)
	Vin = [V[i % lenV] for i in range(-1,lenV-1)]
	Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
	for i in range(lenV):
		for j in range(len(hyperRectangles)):
			hyperRectangle = hyperRectangles[j]
			boundin = [hyperRectangle[0][(i-1) % lenV],hyperRectangle[1][(i-1) % lenV]]
			boundcc = [hyperRectangle[0][(i+lenV/2)%lenV],hyperRectangle[1][(i+lenV/2)%lenV]]
			#print "boundin ", boundin
			#print "boundcc ", boundcc
			claimFwd = triangleBounds(a,Vin[i],VoutFwd[i],boundin[0],boundin[1])
			claimCc = triangleBounds(a,Vcc[i],VoutCc[i],boundcc[0],boundcc[1])
			#print "claimFwd"
			#print claimFwd
			s.add(claimFwd)
			s.add(claimCc)

		s.add(I[i] == (VoutFwd[i] - V[i])*g_fwd + (VoutCc[i] - V[i])*g_cc)

def osclRefineWithSol(s,I,V,a,solution,VoutSolFwd,VoutSolCc,hyperrectangle,g_cc,g_fwd):
	lenV = len(V)
	VoutFwd = RealVector('VoutFwd',lenV)
	VoutCc = RealVector('VoutCc',lenV)
	Vin = [V[i % lenV] for i in range(-1,lenV-1)]
	Vcc = [V[(i + lenV/2) % lenV] for i in range(lenV)]
	for i in range(lenV):
		pointToBeConsideredFwd = solution[(i-1) % lenV]
		pointToBeConsideredCc = solution[(i+lenV/2)%lenV]
		lowFwd = hyperrectangle[0][(i-1) % lenV]
		highFwd = hyperrectangle[1][(i-1) % lenV]
		lowCc = hyperrectangle[0][(i+lenV/2)%lenV]
		highCc = hyperrectangle[1][(i+lenV/2)%lenV]
		claimFwd = tangentTriangleBounds(a,Vin[i],VoutFwd[i],pointToBeConsideredFwd,VoutSolFwd[i],lowFwd,highFwd)
		claimCc = tangentTriangleBounds(a,Vcc[i],VoutCc[i],pointToBeConsideredCc,VoutSolCc[i],lowCc,highCc)
		s.add(claimFwd)
		s.add(claimCc)
		s.add(I[i] == (VoutFwd[i] - V[i])*g_fwd + (VoutCc[i] - V[i])*g_cc)

def findScale(I,V,a,VlowVhighs,g_fwd,g_cc):
	print "Finding Scale"
	opt = Optimize()
	oscl(opt,I,V,a,VlowVhighs,g_cc,g_fwd)
	claim = Or(*[I[i]!=0 for i in range(len(V))])
	opt.add(Not(claim))
	lowerBounds = []
	upperBounds = []
	for i in range(len(V)):
		print "i: ", i
		opt.push()
		optMin = opt.minimize(V[i])
		opt.check()
		minVal = float(Fraction(str(opt.lower(optMin))))
		opt.pop()
		opt.push()
		optMax = opt.maximize(V[i])
		opt.check()
		maxVal = float(Fraction(str(opt.upper(optMax))))
		opt.pop()
		lowerBounds.append(minVal)
		upperBounds.append(maxVal)
	print "lowerBounds ", lowerBounds
	print "upperbounds ", upperBounds
	print ""
	return [lowerBounds,upperBounds]
	

# s is solver. I and V are an array of Z3 symbolic  values.
# VlowVhighs contain indicate how triangle bounds are created
# This function finds hyper rectangles containing DC equilibrium points 
# for our oscillator model. Each hyper rectangle has length and width
# equalling distance
def findHyper(I,V,a,VlowVhighs,g_fwd,g_cc,distances):
	allHyperRectangles = []
	s = Solver()
	print "Finding HyperRectangles"
	count = 0
	while(True):
		#simulate the oscillator and check for solution
		print "count: ", count
		count += 1
		s.push()
		oscl(s,I,V,a,VlowVhighs,g_cc,g_fwd)
		is_equilibrium = And(*[I[i]==0 for i in range(len(V))])
		s.add(is_equilibrium)

		#print "solver "
		#print s
		ch = s.check()
		if(ch == sat):
			VoutFwd = range(0,len(V))
			VoutCc = range(0,len(V))
			lowVoltArray = range(0,len(V))
			highVoltArray = range(0,len(V))
			solVoltArray = range(0,len(V))
			m = s.model()
			for d in m.decls():
				dName = str(d.name())
				index = int(dName[len(dName) - 1])
				val = float(Fraction(str(m[d])))
				if(dName[0]=="V" and dName[1]=="_"):
					solVoltArray[index] = val
					lowVoltArray[index] = val-distances[index]
					highVoltArray[index] = val+distances[index]
					if(lowVoltArray[index] < 0 and highVoltArray[index]>0):
						if(val >= 0):
							lowVoltArray[index] = 0.0
						elif(val < 0):
							highVoltArray[index] = 0.0

				elif(dName[0]=="V" and dName[4]=="F"):
					VoutFwd[index] = val

				elif(dName[0]=="V" and dName[4]=="C"):
					VoutCc[index] = val
			'''print "VoutFwd: "
			print VoutFwd
			print "VoutCC: "
			print VoutCc
			print "sol: "
			print solVoltArray
			print "Check solution "
			_,_,Inum = oscNum(solVoltArray,a,g_cc,g_fwd)
			print "I should be close to 0"
			print Inum'''
			
			#create hyperrectangle around the solution formed 
			newHyperRectangle = [lowVoltArray,highVoltArray]

		else:
			newHyperRectangle = None
			if(ch == unsat):
				print "no more solutions"
				print "allHyperRectangles = " + str(allHyperRectangles)
			elif(ch == unknown):
				print "solver failed"
			else:
				print "INTERNAL ERROR -- unrecognized return code"

		s.pop()
		if newHyperRectangle is None:
			return allHyperRectangles
		else:
			print "newHyperRectangle"
			print newHyperRectangle
			allHyperRectangles.append(newHyperRectangle)
			# Add the constraint so that Z3 can find solutions outside the hyper rectangle just constructed
			# TODO: need to fix these constraint. is this correct?
			s.add(Or(*[Or(V[i] < newHyperRectangle[0][i], 
							V[i] > newHyperRectangle[1][i]) for i in range(len(V))]))


def refine(I,V,a,hyperrectangle,g_fwd,g_cc,hyperNumber,figure):
	print "Finding solutions within hyperrectangle"
	print "low bounds: ", hyperrectangle[0]
	print "upper bounds: ", hyperrectangle[1]
	s = Solver()
	s.add(And(*[And(V[i]>=hyperrectangle[0][i], V[i]<=hyperrectangle[1][i]) for i in range(len(V))]))
	oldSol = array([(hyperrectangle[0][i]+hyperrectangle[1][i])/2.0 for i in range(len(V))])
	VoutSolFwd =  None
	VoutSolCc = None
	hyperrectangles = [hyperrectangle]
	count = 0
	InumNorms = []
	VoutFwdErrors = []
	VoutCcErrors = []
	finalSol = zeros((len(V)))
	smallerHyperrectangles = []
	diffBetweenSolnNorms = []
	osclRefine(s,I,V,a,hyperrectangles,g_cc,g_fwd)
	while True:
		print "count # ", count
		s.push()
		if VoutSolFwd is not None:
			osclRefineWithSol(s,I,V,a,oldSol,VoutSolFwd,VoutSolCc,hyperrectangle,g_cc,g_fwd)
		is_equilibrium = And(*[I[i]==0 for i in range(len(V))])
		s.add(is_equilibrium)
		ch = s.check()
		solVoltArray = zeros((len(V)))
		if ch==sat:
			VoutFwd = range(0,len(V))
			VoutCc = range(0,len(V))
			m = s.model()
			for d in m.decls():
				dName = str(d.name())
				firstLetter = dName[0]
				index = int(dName[len(dName) - 1])
				val = float(Fraction(str(m[d])))
				if(dName[0]=="V" and dName[1]=="_"):
					solVoltArray[index] = val
				elif(dName[0]=="V" and dName[4]=="F"):
					VoutFwd[index] = val
				elif(dName[0]=="V" and dName[4]=="C"):
					VoutCc[index] = val
			#print "VoutFwd: "
			#print VoutFwd
			#print "VoutCC: "
			#print VoutCc
			print "sol: "
			print solVoltArray
			print "Check solution "
			VoutFwdnum,VoutCcnum,Inum = oscNum(solVoltArray,a,g_cc,g_fwd)
			print "I should be close to 0"
			print Inum
			s.pop()

			smallerDistances = (array(hyperrectangle[1]) - array(hyperrectangle[0]))/3.0
			lowSol = solVoltArray - smallerDistances
			highSol = solVoltArray + smallerDistances
			#print "lowSol ", lowSol
			#print "highSol ", highSol

			s.add(Or(*[Or(V[i] < lowSol[i], V[i] > highSol[i]) for i in range(len(V))]))
			smallerHyperrectangle = [lowSol,highSol]
			smallerHyperrectangles.append(smallerHyperrectangle)
			'''print "lowSol ", lowSol
			print "highSol ", highSol
			print ""'''

			'''diffBetweenSoln = absolute(solVoltArray - oldSol)
			diffBetweenSolnNorm = linalg.norm(diffBetweenSoln)
			if len(smallerHyperrectangles) == 0:
				diffBetweenSolnNorms.append(diffBetweenSolnNorm)
				InumNorms.append(log10(linalg.norm(Inum)))
			VoutFwdErrors.append(log10(abs(array(VoutFwdnum)-VoutFwd)))
			VoutCcErrors.append(log10(abs(array(VoutCcnum)-VoutCc)))
			print "diffBetweenSoln: ", diffBetweenSoln
			print "norm of diff: ", diffBetweenSolnNorm
			print "all(diffBetweenSoln < 1e-5) ", all(diffBetweenSoln < 1e-5)
			#print "all(absolute(Inum) < 1e-4) ", all(absolute(Inum) < 1e-4)
			if all(diffBetweenSoln < 1e-5):
				finalSol = solVoltArray
				smallerDistances = (array(hyperrectangle[1]) - array(hyperrectangle[0]))/4.0
				lowSol = finalSol - smallerDistances
				highSol = finalSol + smallerDistances
				#print "lowSol ", lowSol
				#print "highSol ", highSol
				s.add(Or(*[Or(V[i] < lowSol[i], V[i] > highSol[i]) for i in range(len(V))]))
				smallerHyperrectangle = [lowSol,highSol]
				smallerHyperrectangles.append(smallerHyperrectangle)
				oldSol = array([(hyperrectangle[0][i]+hyperrectangle[1][i])/2.0 for i in range(len(V))])
				count = -1
				VoutSolFwd = None
				VoutSolCc = None

			else:
				oldSol = solVoltArray
				VoutSolFwd = VoutFwd
				VoutSolCc = VoutCc'''
			count+=1
		
		else:
			s.pop()
			finalSol =  []
			break
	
	if figure:
		if len(smallerHyperrectangles) > 0:
			legends = ["VoutFwd0", "VoutFwd1", "VoutFwd2", "VoutFwd3",
			"VoutCc0","VoutCc1","VoutCc2","VoutCc3","InumNorm"]
			plt.figure(hyperNumber)
			#plt.plot(arange(len(InumNorms)),InumNorms)
			plt.plot(arange(len(InumNorms)),diffBetweenSolnNorms)
			#plt.plot(arange(len(InumNorms)), VoutFwdErrors,arange(len(InumNorms)), VoutCcErrors)
			plt.xlabel("Number of Iterations")
			plt.ylabel("Log of norm of error")
			#plt.legend(legends,prop={'size':8})
	sepHypers = separateHyperrectangles(smallerHyperrectangles)
	return sepHypers

def multiplyRegularMatWithIntervalMat(regMat,intervalMat):
	mat1 = dot(regMat,intervalMat[:,:,0])
	mat2 = dot(regMat,intervalMat[:,:,1])
	result = zeros((regMat.shape[0],regMat.shape[1],2))
	result[:,:,0] = minimum(mat1,mat2)
	result[:,:,1] = maximum(mat1,mat2)
	return result

def subtractIntervalMatFromRegularMat(regMat,intervalMat):
	mat1 = regMat - intervalMat[:,:,0]
	mat2 = regMat - intervalMat[:,:,1]
	result = zeros((regMat.shape[0],regMat.shape[1],2))
	result[:,:,0] = minimum(mat1,mat2)
	result[:,:,1] = maximum(mat1,mat2)
	return result

def multiplyIntervalMatWithIntervalVec(mat,vec):
	mat1 = dot(mat[:,:,0],vec[:,0])
	mat2 = dot(mat[:,:,1],vec[:,0])
	mat3 = dot(mat[:,:,0],vec[:,1])
	mat4 = dot(mat[:,:,1],vec[:,1])
	result = zeros((mat.shape[0],vec.shape[1]))
	result[:,0] = minimum(minimum(mat1,mat2),minimum(mat3,mat4))
	result[:,1] = maximum(maximum(mat1,mat2),maximum(mat3,mat4))
	return result


def checkExistenceOfSolution(a,g_fwd,g_cc,hyperRectangle):
	print "lower bounds ", hyperRectangle[0]
	print "upper bounds ",hyperRectangle[1]
	numVolts = len(hyperRectangle[0])

	#hyperRectangle = [[0.3,-0.31,0.3,-0.31],[0.31,-0.3,0.31,-0.3]]
	startBounds = zeros((numVolts,2))
	startBounds[:,0] = hyperRectangle[0]
	startBounds[:,1] = hyperRectangle[1]
	
	iteration = 0
	while True:
		print "iteration number: ", iteration
		midPoint = (startBounds[:,0] + startBounds[:,1])/2.0
		print "midPoint"
		print midPoint
		_,_,IMidPoint = array(oscNum(midPoint,a,g_cc,g_fwd))
		jacMidPoint = getJacobian(midPoint,a,g_cc,g_fwd)
		C = linalg.inv(jacMidPoint)
		I = identity(numVolts)

		jacInterval = getJacobianInterval(startBounds,a,g_cc,g_fwd)
		C_IMidPoint = dot(C,IMidPoint)

		C_jacInterval = multiplyRegularMatWithIntervalMat(C,jacInterval)
		I_minus_C_jacInterval = subtractIntervalMatFromRegularMat(I,C_jacInterval)
		xi_minus_midPoint = zeros((numVolts,2))
		for i in range(numVolts):
			xi_minus_midPoint[i][0] = startBounds[i][0] - midPoint[i]
			xi_minus_midPoint[i][1] = startBounds[i][1] - midPoint[i]

		lastTerm = multiplyIntervalMatWithIntervalVec(I_minus_C_jacInterval, xi_minus_midPoint)
		
		kInterval1 = midPoint - C_IMidPoint + lastTerm[:,0]
		kInterval2 = midPoint - C_IMidPoint + lastTerm[:,1]
		kInterval = zeros((numVolts,2))
		kInterval[:,0] = minimum(kInterval1, kInterval2)
		kInterval[:,1] = maximum(kInterval1, kInterval2)

		print "kInterval "
		print kInterval

		uniqueSoln = True
		for i in range(numVolts):
			if kInterval[i][0] <= startBounds[i][0] or kInterval[i][0] >= startBounds[i][1]:
				uniqueSoln = False
			if kInterval[i][1] <= startBounds[i][0] or kInterval[i][1] >= startBounds[i][1]:
				uniqueSoln = False

		if uniqueSoln:
			print "Hyperrectangle with unique solution found"
			print kInterval
			return (True,kInterval)

		intersect = zeros((numVolts,2))
		for i in range(numVolts):
			minVal = max(kInterval[i][0],startBounds[i][0])
			maxVal = min(kInterval[i][1],startBounds[i][1])
			if minVal <= maxVal and \
				minVal >= kInterval[i][0] and minVal >= startBounds[i][0] and \
				minVal <= kInterval[i][1] and minVal <= startBounds[i][1] and \
				maxVal >= kInterval[i][0] and maxVal >= startBounds[i][0] and \
				maxVal <= kInterval[i][1] and maxVal <= startBounds[i][1]:
				intersect[i] = [minVal,maxVal]
				intervalLength =  intersect[:,1] - intersect[:,0]
			else:
				intersect = None
				break

		print "intersect"
		print intersect

		if intersect is None:
			print "hyperrectangle does not contain any solution"
			return (False,None)
		elif linalg.norm(intervalLength) < 1e-8 or linalg.norm(intersect-startBounds) < 1e-8:
			print "Found the smallest possible hyperrectangle containing solutions"
			return (False,intersect)
		else:
			startBounds = intersect
		iteration += 1


# combine hyperrectangles that intersect
def filterHyperrectangles(allHyperRectangles):
	filteredHypers = []
	intersected = []
	for hyper in allHyperRectangles:
		intersected.append(False)

	for i in range(len(allHyperRectangles)):
		if intersected[i] == False:
			hyper1 = array(allHyperRectangles[i])
			for j in range(i+1,len(allHyperRectangles)):
				enclosure = zeros((2,len(hyper1[0])))
				if intersected[j] == False:
					hyper2 = allHyperRectangles[j]
					for k in range(len(hyper1[0])):
						minValCheck = max(hyper1[0][k],hyper2[0][k])
						maxValCheck = min(hyper1[1][k],hyper2[1][k])
						minVal = min(hyper1[0][k],hyper2[0][k])
						maxVal = max(hyper1[1][k],hyper2[1][k])
						if minValCheck <= maxValCheck and \
							minValCheck <= hyper1[1][k] and minValCheck <= hyper2[1][k] and \
							minValCheck >= hyper1[0][k] and minValCheck >= hyper2[0][k] and \
							maxValCheck >= hyper1[0][k] and maxValCheck >= hyper2[0][k] and \
							maxValCheck <= hyper1[1][k] and maxValCheck <= hyper2[1][k]:
							enclosure[0][k] = minVal
							enclosure[1][k] = maxVal
						else:
							enclosure = None
							break
					if enclosure is not None:
						#print "combined "
						#print "hyper1 ", hyper1
						#print "hyper2 ", hyper2
						hyper1 = enclosure
						#print "enclosure ", enclosure
						#print "hyper1 ", hyper1
						intersected[j] = True
			filteredHypers.append(hyper1)
			intersected[i] = True

	return filteredHypers

#separate hyperrectangles that intersect
def separateHyperrectangles(allHyperRectangles):
	separatedHypers = copy.deepcopy(allHyperRectangles)

	for i in range(len(allHyperRectangles)):
		hyper1 = array(separatedHypers[i])
		for j in range(i+1,len(allHyperRectangles)):
			changed = True
			hyper2 = array(separatedHypers[j])
			'''print "hyper1 before " 
			print allHyperRectangles[i][0]
			print allHyperRectangles[i][1]
			print "hyper2 before "
			print allHyperRectangles[j][0]
			print allHyperRectangles[j][1]
			print ""'''
			for k in range(len(hyper1[0])):
				minValCheck = max(hyper1[0][k],hyper2[0][k])
				maxValCheck = min(hyper1[1][k],hyper2[1][k])
				if minValCheck <= maxValCheck and \
					minValCheck <= hyper1[1][k] and minValCheck <= hyper2[1][k] and \
					minValCheck >= hyper1[0][k] and minValCheck >= hyper2[0][k] and \
					maxValCheck >= hyper1[0][k] and maxValCheck >= hyper2[0][k] and \
					maxValCheck <= hyper1[1][k] and maxValCheck <= hyper2[1][k]:
					if hyper1[0][k] < hyper2[0][k]:
						hyper2[0][k] = hyper1[1][k]
					elif hyper1[0][k] > hyper2[0][k]:
						hyper2[1][k] = hyper1[0][k]
				else:
					changed = False
					break
			if changed:
				allHyperRectangles[j] = hyper2
				'''print "hyper1 after "
				print allHyperRectangles[i][0]
				print allHyperRectangles[i][1]
				print "hyper2 after " 
				print allHyperRectangles[j][0]
				print allHyperRectangles[j][1]
				print ""'''
	return separatedHypers



def testInvRegion(g_cc):
	a = 5
	g_fwd = 1.0
	lenV = 8
	V = RealVector('V',lenV)
	I = RealVector('I',lenV)
	allHyperRectangles = []

	V = RealVector('V',4)
	I = RealVector('I',4)
	allHyperRectangles = []
	VlowVhighs = [[[-3.0,-3.0,-3.0,-3.0],[-2.0,-2.0,-2.0,-2.0]],
				  [[-2.0,-2.0,-2.0,-2.0],[-1.0,-1.0,-1.0,-1.0]],
				  [[-1.0,-1.0,-1.0,-1.0],[0.0, 0.0, 0.0, 0.0]],
				  [[0.0, 0.0, 0.0, 0.0],[1.0, 1.0, 1.0, 1.0]],
				  [[1.0, 1.0, 1.0, 1.0],[2,0, 2.0, 2.0, 2.0]],
				  [[2.0, 2.0, 2.0, 2.0],[3.0, 3.0, 3.0, 3.0]]]

	overallHyperRectangle = findScale(I,V,a,VlowVhighs,g_fwd,g_cc)
	minOptSol = overallHyperRectangle[0]
	maxOptSol = overallHyperRectangle[1]
	VlowVhighs = [[minOptSol,[minOptSol[0]/2.0,minOptSol[1]/2.0,minOptSol[2]/2.0,minOptSol[3]/2.0]],
				  [[minOptSol[0]/2.0,minOptSol[1]/2.0,minOptSol[2]/2.0,minOptSol[3]/2.0],[0.0, 0.0, 0.0, 0.0]],
				  [[0.0, 0.0, 0.0, 0.0],[maxOptSol[0]/2.0,maxOptSol[1]/2.0,maxOptSol[2]/2.0,maxOptSol[3]/2.0]],
				  [[maxOptSol[0]/2.0,maxOptSol[1]/2.0,maxOptSol[2]/2.0,maxOptSol[3]/2.0],maxOptSol]]


	distances = [(maxOptSol[i] - minOptSol[i])/8.0 for i in range(len(V))]
	print "hyperrectangles before"
	print allHyperRectangles
	allHypers = findHyper(I,V,a,VlowVhighs,g_fwd,g_cc,distances)
	allHyperRectangles = separateHyperrectangles(allHypers)
	print "hyperrectangles after"
	print allHyperRectangles
	
	finalHyperrectangles = []

	# until all hyperrectangles do not contain any unique solution
	while len(allHyperRectangles) != 0:
		print "refining hyperrectangles"
		sols = []
		figure = False
		for i in range(len(allHyperRectangles)):
			print "Refining hyper rectangle ", i
			sol = refine(I,V,a,allHyperRectangles[i],g_fwd,g_cc,i,figure)
			if len(sol) ==0:
				print "No solution found"
			else:
				print "Refined solution: "
				print sol
				for rect in sol:
					sols.append(rect)
			print ""
		if figure:
			plt.show()
		print "All refined solutions "
		print sols
		print ""
		allHyperRectangles = []

		print "Checking existence of solutions within refined hyperrectangles"
		for i in range(len(sols)):
			print "Checking existience within hyperrectangle ", i
			uniqueness,interval = checkExistenceOfSolution(a,g_fwd,g_cc,sols[i])
			if uniqueness:
				finalHyperrectangles.append(transpose(interval))
			else:
				if interval is not None:
					allHyperRectangles.append(transpose(interval))
			print ""

	print "final solutions"
	print finalHyperrectangles

	filteredHyperrectangles = filterHyperrectangles(finalHyperrectangles)
	print "final filtered solutions"
	print filteredHyperrectangles

testInvRegion(0.5)
