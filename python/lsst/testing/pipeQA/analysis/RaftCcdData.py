import numpy

class RaftCcdData(object):

    def __init__(self, detector, initValue=0.0):
	self.detector = detector
	self.data = {}
	self.keys = []
	self.reset(initValue)
	
	self.cache = None

    def raftCcdKeys(self):
	keyList = []
	for raft in sorted(self.data.keys()):
	    for ccd in sorted(self.data[raft].keys()):
		keyList.append([raft, ccd])
	return keyList
	

    def listKeysAndValues(self):
	kvList = []
	for raft in sorted(self.data.keys()):
	    for ccd in sorted(self.data[raft].keys()):
		kvList.append([raft, ccd, self.data[raft][ccd]])
	return kvList


    def reset(self, value=0.0):
	for key, detector in self.detector.items():
	    raft = detector.getParent().getId().getName()
	    ccd = detector.getId().getName()
	    if not self.data.has_key(raft):
		self.data[raft] = {}
	    if not self.data[raft].has_key(ccd):
		self.data[raft][ccd] = value

    def set(self, raft, ccd, value):
	self.data[raft][ccd] = value
    def get(self, raft, ccd):
	if self.data.has_key(raft) and self.data[raft].has_key(ccd):
	    return self.data[raft][ccd]
	else:
	    return None

    def cacheValues(self, recache=False):
	if (self.cache is None) or recache:
	    self.cache = numpy.array([])
	    for raft, ccdDict in self.data.items():
		for ccd, value in ccdDict.items():
		    self.cache = numpy.append(self.cache, value)

    def summarize(self, methodName, recache=False):
	self.cacheValues(recache)
	if methodName == 'median':
	    return numpy.median(self.cache)
	method = getattr(self.cache, methodName)
	return method()
    
	

class RaftCcdVector(RaftCcdData):

    def __init__(self, detector):
	RaftCcdData.__init__(self, detector, initValue=numpy.array([]))

    def listKeysAndValues(self, methodName=None, nHighest=None, nLowest=None):
	kvList = []
	for raft in sorted(self.data.keys()):
	    for ccd in sorted(self.data[raft].keys()):
		# if not method specified, return the list
		if methodName is None:
		    value = self.data[raft][ccd]

		# otherwise reduce the list to a number: eg. mean, std, median
		else:
		    finite = numpy.where( numpy.isfinite(self.data[raft][ccd]) )
		    dtmp = self.data[raft][ccd][finite]
		    if not nHighest is None:
			dtmp.sort()
			dtmp = dtmp[-nHighest:]
		    if (not nLowest is None) and (nHighest is None):
			dtmp.sort()
			dtmp = dtmp[0:nLowest]

		    value = None
		    if methodName == 'median':
			value = numpy.median(dtmp)
		    else:
			method = getattr(dtmp, methodName)
			value = method()
		kvList.append([raft, ccd, value])
	return kvList
	
    def reset(self, initValue=numpy.array([])):
	RaftCcdData.reset(self, initValue)

    def append(self, raft, ccd, value):
	self.data[raft][ccd] = numpy.append(self.data[raft][ccd], value)
    
