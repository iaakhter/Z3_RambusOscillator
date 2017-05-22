import numpy as np
import copy

def is_number(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

# Applies the simplex on a standard form LP matrix
# the first row is the objective function
# the first element in the first row must be positive
def simplex(standardMat, artificialIndices):
	numRows = standardMat.shape[0]
	numCols = standardMat.shape[1]
	count = 0
	while True:
		print "standardMat before simplex"
		print standardMat
		nonZeroVals = 0
		artInd = None
		for ind in artificialIndices:
			r = ind[0]
			c = ind[1]
			nonZeroVals += np.sum(standardMat[:,c] != 0)
			artInd = ind
		if nonZeroVals == len(artificialIndices):
			break

		standardMat = gauss_jordan(standardMat,artInd[0],artInd[1])
		count += 1

	count = 0
	while len(np.where(standardMat[0] < 0)[0]) > 0:
		print "mat "
		print standardMat
		print ""
		enteringVariable = np.where(standardMat[0,:] < 0)[0][0]
		ratios = np.divide(standardMat[:,numCols - 1],standardMat[:,enteringVariable])
		ratioSortedIndices = np.argsort(ratios)
		for ind in ratioSortedIndices:
			if ind != 0 and ratios[ind] > 0:
				pivot = ind
				break
		print "entering variable ", enteringVariable
		print "ratios ", ratios
		print "ratioIndices", ratioSortedIndices
		print "pivot ", pivot
		standardMat = gauss_jordan(standardMat,pivot,enteringVariable)
		print "mat after "
		print standardMat
		print ""
		count+=1
		'''if count == 2:
			return'''
	sols = np.zeros((numCols - 1))
	for i in range(len(sols)):
		if np.sum(standardMat[:,i]==0) == numRows - 1:
			nonzeroIndex = np.where(standardMat[:,i] != 0)[0][0]
			if standardMat[nonzeroIndex][i] == 1:
				sols[i] = standardMat[nonzeroIndex][numCols-1]
	return sols


def gauss_jordan(mat, pivot, enteringVariable):
	mat[pivot] = mat[pivot]/mat[pivot][enteringVariable]
	for i in range(mat.shape[0]):
		if i!= pivot:
			mat[i] = mat[i] - mat[i][enteringVariable]*mat[pivot]
	return mat

def convertToStdLP(stringConstraint):
	artificialIndices = []
	#split the strings appropriately to make it easy for parsing
	splittedConstraint = stringConstraint.split("\n")
	finalSplitConst = []
	for s in splittedConstraint:
		splitted = s.split(" ")
		finalSplitConst.append(splitted)
	
	# get all the variables from the last constraint added
	# assumes that the last constraint always constraints the individual
	# decision variables. e.g. x1 >= 0, x2 >= 0 and so on
	variables = {}
	variablesSign = {} # if negative need to change variables in original LP
	variableConstraints = finalSplitConst[len(finalSplitConst)-1]
	countVariables = 1
	for j in range(len(variableConstraints)-1):
		if variableConstraints[j+1] == "urs":
			variablesSign[variableConstraints[j]] = "urs"
			variables[variableConstraints[j]] = [countVariables, countVariables+1]
			countVariables += 2
		elif variableConstraints[j+1] == ">=":
			variablesSign[variableConstraints[j]] = True #variable must be positive
			variables[variableConstraints[j]] = countVariables
			countVariables += 1
		elif variableConstraints[j+1] == "<=":
			variablesSign[variableConstraints[j]] = False #variable must be negative
			countVariables += 1

	print "variablesSign"
	print variablesSign
	print "variables"
	print variables
	countInequalities = 1 # because of the objective function
	for i in range(1,len(finalSplitConst)-1):
		const = finalSplitConst[i]
		if const[len(const)-2] == ">=":
			countInequalities+=2
		else:
			countInequalities+=1

	mat = np.zeros((len(finalSplitConst)-1,countVariables + countInequalities))
	#print "mat.shape ", mat.shape
	mat[0,0] = 1.0
	slackVarNum = countVariables
	print "finalSplitConst"
	print finalSplitConst
	
	# fill in the matrix
	for i in range(mat.shape[0]):
		const = finalSplitConst[i]
		# deal with min max issue in the objectibe function
		if i== 0:
			maximize = True
			if const[0] == "min":
				maximize = False
			for j in range(1,len(const)-1):
				if is_number(const[j]):
					if maximize:
						#if variable is unrestricted, replace it with two variables
						if variablesSign[const[j+1]] == "urs":
							mat[i][variables[const[j+1]][0]] = -float(const[j])
							mat[i][variables[const[j+1]][1]] = float(const[j])
						elif variablesSign[const[j+1]]:
							mat[i][variables[const[j+1]]] = -float(const[j])
						else:
							mat[i][variables[const[j+1]]] = float(const[j])
					else:
						if variablesSign[const[j+1]] == "urs":
							mat[i][variables[const[j+1]][0]] = float(const[j])
							mat[i][variables[const[j+1]][1]] = -float(const[j])
						if variablesSign[const[j+1]]:
							mat[i][variables[const[j+1]]] = float(const[j])
						else:
							mat[i][variables[const[j+1]]] = -float(const[j])
		else:
			negConstant = False # if negative constant on the right hand side
								# multiply everything by -1 and flip the equality signs
			if (float(const[len(const)-1]) < 0):
				negConstant = True
			lessThan = True
			greaterThan = False
			if const[len(const)-2] == ">=":
				lessThan = False
				greaterThan = True
			elif const[len(const)-2] == "==":
				lessThan = False
				greaterThan = False
			if (lessThan or greaterThan) and negConstant:
				mat[i][mat.shape[1]-1] = -float(const[len(const)-1])
				if lessThan:
					lessThan = False
					greaterThan = True
				else:
					lessThan = True
					greaterThan = False
			else:
				mat[i][mat.shape[1]-1] = float(const[len(const)-1])
			for j in range(len(const)-1):
				if is_number(const[j]):
					if variablesSign[const[j+1]] == "urs":
						if negConstant == False:
							mat[i][variables[const[j+1]][0]] = float(const[j])
							mat[i][variables[const[j+1]][1]] = -float(const[j])
						else:
							mat[i][variables[const[j+1]][0]] = -float(const[j])
							mat[i][variables[const[j+1]][1]] = float(const[j])
					elif variablesSign[const[j+1]]:
						if negConstant == False:
							mat[i][variables[const[j+1]]] = float(const[j])
						else:
							mat[i][variables[const[j+1]]] = -float(const[j])
					else:
						if negConstant == False:
							mat[i][variables[const[j+1]]] = -float(const[j])
						else:
							mat[i][variables[const[j+1]]] = float(const[j])

			if lessThan == False and greaterThan == False:
				mat[i][slackVarNum] = 1.0
				mat[0][slackVarNum] = 1e+15
				artificialIndices.append([i,slackVarNum])
				slackVarNum += 1
			elif lessThan:
				mat[i][slackVarNum] = 1.0
				slackVarNum += 1
			elif greaterThan:
				mat[i][slackVarNum] = -1.0
				slackVarNum += 1
				mat[i][slackVarNum] = 1.0
				mat[0][slackVarNum] = 1e+15
				artificialIndices.append([i,slackVarNum])
				slackVarNum += 1


	return (mat, artificialIndices)

def linearConstraintFun1():
	constraintString = "1 y + 0.133 x <= 0.9205\n\
						1 y + 5.0 x <= 0.0\n\
						1 y + 1.974 x >= 0.0\n\
						1 y <= 1.0\n\
						1 y >= 0.987\n\
						1 y - 0.3 x == 0.1"



if __name__=="__main__":
	stringConstraint = "max 2 x1 + 1 x2\n1 x1 + 1 x2 <= 10\n-1 x1 + 1 x2 >= 2\nx1 >= 0 x2 >= 0"
	print "stringConstraint"
	print stringConstraint
	mat,artificialIndices = convertToStdLP(stringConstraint)
	print "mat "
	print mat
	'''mat = np.array([[1.0, -1.0, -1.0, 0.0, 0.0, 0.0],
					[0.0, 1.0, 2.0, 1.0, 0.0, 8.0],
					[0.0, 3.0, 2.0, 0.0, 1.0, 12.0]])'''
	'''mat = np.array([[1.0,-5.0,-7.0,0.0,0.0,0.0],
				[0.0,3.0,4.0,1.0,0.0,650.0],
				[0.0,2.0,3.0,0.0,1.0,500.0]])'''
	'''mat = np.array([[1.0,-1.0,-1.0,0.0,0.0,0.0],
				[0.0,2.0,1.0,1.0,0.0,4.0],
				[0.0,1.0,2.0,0.0,1.0,3.0]])'''
	solutions = simplex(mat,artificialIndices)
	print "final solutions"
	print solutions
