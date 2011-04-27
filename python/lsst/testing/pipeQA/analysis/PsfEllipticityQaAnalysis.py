import sys, os, re
import lsst.meas.algorithms        as measAlg
import lsst.testing.pipeQA.figures as qaFig
import numpy

import lsst.afw.math                as afwMath
import lsst.testing.pipeQA.TestCode as testCode

import QaAnalysis as qaAna
import RaftCcdData as raftCcdData
import QaAnalysisUtils as qaAnaUtil

import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.font_manager as fm

class PsfEllipticityQaAnalysis(qaAna.QaAnalysis):

    def __init__(self):
	qaAna.QaAnalysis.__init__(self)

    def test(self, data, dataId):
	
	# get data
	self.ssDict        = data.getSourceSetBySensor(dataId)
	self.detector      = data.getDetectorBySensor(dataId)
	self.filter        = data.getFilterBySensor(dataId)

	# create containers for data in the focal plane
	self.x     = raftCcdData.RaftCcdVector(self.detector)
	self.y     = raftCcdData.RaftCcdVector(self.detector)
	self.ellip = raftCcdData.RaftCcdVector(self.detector)
	self.theta = raftCcdData.RaftCcdVector(self.detector)

	# compute values of interest
	filter = None
	for key, ss in self.ssDict.items():
	    raft = self.detector[key].getParent().getId().getName()
	    ccd  = self.detector[key].getId().getName()

	    filter = self.filter[key].getName()
	    
	    for s in ss:
		ixx = s.getIxx()
		iyy = s.getIyy()
		ixy = s.getIxy()

		a2 = 0.5*(ixx+iyy) + numpy.sqrt(0.25*(ixx-iyy)**2 + ixy**2)
		b2 = 0.5*(ixx+iyy) - numpy.sqrt(0.25*(ixx-iyy)**2 + ixy**2)
		ellip = 1.0 - numpy.sqrt(b2/a2)
		theta = 0.5*numpy.arctan2(2.0*ixy, ixx-iyy)
		#print ixx, iyy, ixy, a2, b2, ellip, theta
		
		if numpy.isfinite(ellip) and numpy.isfinite(theta):
		    self.ellip.append(raft, ccd, ellip)
		    self.theta.append(raft, ccd, theta)
		    self.x.append(raft, ccd, s.getXAstrom())
		    self.y.append(raft, ccd, s.getYAstrom())
		
	# create a testset and add values
	group = dataId['visit']
	testSet = self.getTestSet(group)
	testSet.addMetadata('dataset', data.getDataName())
	testSet.addMetadata('visit', dataId['visit'])
	testSet.addMetadata('filter', filter)

	# gets the stats for each sensor and put the values in the raftccd container
	self.ellipMedians = raftCcdData.RaftCcdData(self.detector)
	self.thetaMedians = raftCcdData.RaftCcdData(self.detector)
	
	for raft, ccd in self.ellip.raftCcdKeys():
	    ellip = self.ellip.get(raft, ccd)
	    theta = self.theta.get(raft, ccd)
	    
	    stat = afwMath.makeStatistics(ellip, afwMath.NPOINT | afwMath.MEDIAN)
	    ellipMed = stat.getValue(afwMath.MEDIAN)
	    stat = afwMath.makeStatistics(theta, afwMath.NPOINT | afwMath.MEDIAN)
	    thetaMed = stat.getValue(afwMath.MEDIAN)
	    n      = stat.getValue(afwMath.NPOINT)

	    # add a test for acceptible psf ellipticity
	    self.ellipMedians.set(raft, ccd, ellipMed)
	    label = "median psf ellipticity "+re.sub("\s+", "_", ccd)
	    comment = "median psf ellipticity (nstar=%d)" % (n)
	    testSet.addTest( testCode.Test(label, ellipMed, [0.00, 0.3], comment) )

	    # stash the angles.  We'll use them to make figures in plot()
	    self.thetaMedians.set(raft, ccd, thetaMed)
	    

    def plot(self, data, dataId, showUndefined=False):

	group = dataId['visit']
	testSet = self.getTestSet(group)

	vLen = 1000.0  # for e=1.0

	# fpa figure
	ellipFig = qaFig.VectorFpaQaFigure(data.cameraInfo.camera)
	for raft, ccdDict in ellipFig.data.items():
	    for ccd, value in ccdDict.items():
		if not self.ellipMedians.get(raft, ccd) is None:
		    ellipFig.data[raft][ccd] = [self.thetaMedians.get(raft, ccd),
						10*vLen*self.ellipMedians.get(raft, ccd)]
		    ellipFig.map[raft][ccd] = "ell/theta=%.3f/%.0f" % (self.ellipMedians.get(raft, ccd),
								       (180/numpy.pi)*self.thetaMedians.get(raft, ccd))
		
	ellipFig.makeFigure(showUndefined=showUndefined, cmap="YlOrRd", vlimits=[0.0, 0.1],
			    title="Median PSF Ellipticity")
	testSet.addFigure(ellipFig, "medPsfEllip.png", "Median PSF Ellipticity",
			  saveMap=True, navMap=True)

	#
	figsize = (4.0, 4.0)
	
	#xlim = [0, 25.0]
	#ylim = [0, 0.4]

	i = 0
	xmin, xmax = 1.0e99, -1.0e99
	for raft, ccd in self.ellip.raftCcdKeys():
	    eLen = vLen*self.ellip.get(raft, ccd)
	    t = self.theta.get(raft, ccd)
	    dx = eLen*numpy.cos(t)
	    dy = eLen*numpy.sin(t)
	    x = self.x.get(raft, ccd) - 0.5*dx
	    y = self.y.get(raft, ccd) - 0.5*dy

	    xmax, ymax = x.max(), y.max()
	    xlim = [0, 1024*int(xmax/1024.0 + 0.5)]
	    ylim = [0, 1024*int(ymax/1024.0 + 0.5)]
	    
	    print "plotting ", ccd
	    
	    fig = qaFig.QaFig(size=figsize)
	    fig.fig.subplots_adjust(left=0.15)
	    ax = fig.fig.add_subplot(111)
	    for i in range(len(x)):
		ax.plot([x[i], x[i]+dx[i]], [y[i], y[i]+dy[i]], '-k')

	    ax.set_title("PSF ellipticity")
	    ax.set_xlabel("x [pixels]")
	    ax.set_ylabel("y [pixels]")
	    ax.set_xlim(xlim)
	    ax.set_ylim(ylim)
	    for tic in ax.get_xticklabels() + ax.get_yticklabels():
		tic.set_size("x-small")

	    label = re.sub("\s+", "_", ccd)
	    testSet.addFigure(fig, "psfEllip_"+label+".png", "PSF ellipticity")
	    
	    i += 1
