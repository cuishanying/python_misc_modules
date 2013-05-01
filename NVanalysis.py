### My name is Shanying! I wrote this piece'o shit! Today's date is 04/11/2013
### This is now the new version where I make shit awesome!!
### Test pushing.

import pylab as py
import winspec
from numpy import ndarray

class Spectrum:
    """
    This class loads a .SPE file or .txt file
    for .txt file (saved from Clarke's Raman), 
    first column is wavelength and 2nd column is luminescence
    """

    @classmethod
    def fromFile(cls,fname):
        return cls(fname = fname)
    
    def __init__(self,**kwargs):
        self._fname = ''
        self._wavelen = []
        self._lum = []
    
        if 'fname' in kwargs:

            self._fname = kwargs['fname']
            self._wavelen = py.loadtxt(self._fname)[:,0]
            self._lum = py.loadtxt(self._fname)[:,1]
                
            assert len(self._wavelen) == len(self._lum), "Wavelength and luminescence length should match"
        
        else:
            assert type(kwargs['wavelen']) in [ndarray, list], "first input must be list or ndarray"
            assert type(kwargs['lum']) in [ndarray, list], "second input must be list or ndarray"
            
            self._wavelen = kwargs['wavelen']
            self._lum = kwargs['lum'] 
            
        if self._wavelen[0] > self._wavelen[-1]:
            self._wavelen = self._wavelen[::-1]
            self._lum = self._lum[::-1]
        
    def get_wavelen(self):
        return self._wavelen
    
    def get_lum(self):
        return self._lum
    
    def get_lumAtWavelen(self, wavelen):
        lum = None
        index = py.where(self._wavelen > wavelen)[0][0]
        lum = self._lum[index]
            
        assert lum != None, "wavelength out of bound"
        return lum
    
    def int_peak(self,fitrange=None, intrange=None, normalize=False, plot=False, npoints=10):
        """
        Fits a linear background, subtracts the background, and integrates. Intended to be used for integrating peaks.
        
        wavelen : list
            list of wavelengths in nm. Can be sorted from low to high or high to low
        lum : list
            list of luminescence
        fitrange : 2-element list, optional
            Defaults to the span of the data. Input: [low nm, high nm]
        intrange : 2-element list, optional
            Defaults to the span of the data or fitrange (if given). Input: [low nm, high nm]
        normalize : boolean, optional
            Default is False
        plot : boolean, optional
            Default is False. Plots the original data, the linear background, and the data with the background subtracted
        npoints : int
            Default is 10. Number of points above and below the given fitrange point to average over.
        """
        if fitrange is None:
            fitindex=[0+npoints/2, len(self._wavelen)-1-npoints/2]
        else:
            fitindex=[0, 0]
            fitindex[0]=py.where(self._wavelen>fitrange[0])[0][0]
            fitindex[1]=py.where(self._wavelen>fitrange[1])[0][0]
        
        wavelenfit=py.concatenate((self._wavelen[fitindex[0]-npoints/2:fitindex[0]+npoints/2], 
                               self._wavelen[fitindex[1]-npoints/2:fitindex[1]+npoints/2]))
        lumfit=py.concatenate((self._lum[fitindex[0]-npoints/2:fitindex[0]+npoints/2], 
                            self._lum[fitindex[1]-npoints/2:fitindex[1]+npoints/2]))
        linearfit = py.polyfit(wavelenfit, lumfit, 1)
        linear_bg = py.polyval( linearfit, self._wavelen[fitindex[0]:fitindex[1]+1] )
        wavelen_bg = self._wavelen[fitindex[0]:fitindex[1]+1].copy()
        lum_bg = self._lum[fitindex[0]:fitindex[1]+1].copy()
        lum_bg -= linear_bg
        
        if plot is True:
            py.plot(self._wavelen,self._lum,'k')
            py.plot(wavelen_bg,linear_bg,'k:')
            py.plot(wavelen_bg,lum_bg,'r')
            py.show()
        
        intindex=[0,0]
        if intrange is None:
            wavelen_int = wavelen_bg
            lum_int = lum_bg  
        else:
            intindex[0]=py.where(wavelen_bg>intrange[0])[0][0]
            intindex[1]=py.where(wavelen_bg>intrange[1])[0][0]    
            wavelen_int = wavelen_bg[intindex[0]:intindex[1]+1]
            lum_int = lum_bg[intindex[0]:intindex[1]+1]
        
        peak_area = py.trapz(lum_int, x=wavelen_int)
        return peak_area
        
    def get_NVratio(self, NV0fitrange = [567, 581], NV0intrange = [573.5, 581], NVmfitrange = [633, 644],plot=False):
        """
        Returns a list of NV0 ZPL area, NVm ZPl area, and NVm/(NV0+NVm) ratio.
        
        NV0fitrange: list, optional
            Default [567, 581] (nm)
        NV0intrange: list, optional
            Default [573.5, 581] (nm)
        NVmfitrange: list, optional
            Default [633, 644] (nm)
        plot: boolean, optional
            Default False
        """
        NV0=self.int_peak(fitrange=NV0fitrange, intrange=NV0intrange, plot=plot)
        NVm=self.int_peak(fitrange=NVmfitrange,plot=plot)
        
        return [NV0,NVm,NVm/(NV0+NVm)]
    
    def plot(self,*args,**kwargs):
        py.plot(self._wavelen, self._lum,*args,**kwargs)
        
#    def load_520exc(files,NV0fitrange=[573,586], NVmfitrange=[636,648]):
#        """
#        files: list
#        """
#        data=[winspec.Spectrum(f) for f in files]
#        
#        NV=py.zeros((py.size(data),3))
#        NV[:,0]=[int_peak(d.wavelen, d.lum, fitrange=NV0fitrange) for d in data]
#        NV[:,1]=[int_peak(d.wavelen, d.lum,fitrange=NVmfitrange) for d in data]
#        NV[:,2]=NV[:,1]/(NV[:,0]+NV[:,1])
#                
#        return NV
#
#    def load_highgrating(files,NV0fitrange=[568,580],NV0intrange=[574,580],NVmfitrange=None):
#        """
#        files: list
#        format: str
#        """
#        dataNV0=[]
#        dataNVm=[]
#        for f in files:
#            if f.find('NV0') is not -1:
#                dataNV0.append(winspec.Spectrum(f))
#            elif f.find('NVm') is not -1:
#                dataNVm.append(winspec.Spectrum(f))
#            else:
#                raise ValueError(f,'filename must contain either "NV0" or "NVm"')
#        
#        data=py.vstack([dataNV0,dataNVm])
#        NV=py.zeros((py.size(dataNV0),3))
#    
#        NV[:,0]=[int_peak(d.wavelen, d.lum, fitrange=NV0fitrange,intrange=NV0intrange) for d in dataNV0]
#        NV[:,1]=[int_peak(d.wavelen, d.lum,fitrange=NVmfitrange) for d in dataNVm]
#        NV[:,2]=NV[:,1]/(NV[:,0]+NV[:,1])
#                
#        return NV
    

class Map:
    def __init__(self,fname):
        """
        initializes Map object, and loads a z scan or x, y, z map. 
        """
        self._specList=[]
        self._focusedSpec = []
        self._z=[]
        self._nfocus=0
        self._fname = fname
        self._wavelen = py.loadtxt(self._fname)[0]
        
        isReversed = self._wavelen[0] > self._wavelen[-1]
        if isReversed:
            self._wavelen = self._wavelen[::-1]
            
        data = py.loadtxt(self._fname,skiprows=1)
        
        # check what kind of a file it is
        lendiff = py.shape(data)[1] - len(self._wavelen)
        if lendiff == 1:
            self.load_focus(data, isReversed)
        if lendiff == 3:
            self.load_map(data, isReversed)
    
    def get_wavelen(self):
        return self._wavelen
    
    def get_specList(self):
        return self._specList
    
    def get_focusedSpec(self):
        return self._focusedSpec
    
    def get_zvals(self):
        return self._z
    
    def load_focus(self, data, isReversed):
        """
        return list of Spectrum 
        """
        self._z=data[:,0]
        self._nfocus=len(data[:,0])
        
        spectrums = []
        for focus in data:
            lum = focus[1:][::-1] if isReversed else focus[1:]
            spectrums.append(Spectrum(wavelen=self._wavelen,lum=lum))
        
        self._specList = [spectrums]  # only one point
        
        assert len(self._specList[0]) == self._nfocus, "Num focus points must equal num of luminescence"
        
    def load_map(self, data, isReversed):
        
        # sort
        data=list(data)
        data.sort( key=lambda x: x[1])
        data.sort( key=lambda x: x[2])
        data=py.asarray(data)
        
        # find nfocus
        firstfocus=data[0][0]
        for row in data[1:]:
            self._nfocus+=1
            if row[0] == firstfocus:
                break
        
        # extract lum data    
        for row in data:
            if isReversed:
                lum = row[3:][::-1]
            else:
                lum = row[3:]
            self._specList.append(Spectrum(wavelen=self._wavelen,lum=lum))

        # split specList into points, ie. [[z1, z1, z3],[z1,z2,z3]]
        self._specList=[self._specList[i:i+self._nfocus] for i in range(0,len(self._specList),self._nfocus)]
        self._z = (data[:,0][0:self._nfocus])
        
        assert len(self._z) == len(self._specList[0]), "len of focuses must match specList sublist length"        

    def find_focus(self, wavelen,plot=False):
        """
        for each point, finds the focus of highest intensity at given wavelength
        saves the Spectrum with "best focus" in a new list called self._focusedSpec
        
        returns z values of the best focus at each point
        
        wavelen: int or float
            Finds focus with max luminescence at this wavelength (nm) 
        """
        lum = []
        bestz=[]
        for point in self._specList:
            a=[]
            if plot == True:
                py.figure()
            for spec in point:
                lum.append(spec.get_lumAtWavelen(wavelen))
                if plot == True:
                    spec.plot()
            if plot == True:
                for z in self._z:
                    a.append(str(z))
                py.legend(a)
            maxlum_index = lum.index(max(lum))
            self._focusedSpec.append(point[maxlum_index])
            bestz.append(self._z[maxlum_index])
            lum = []
        
        #print bestz
        return bestz
    
    def define_focus(self,zindexlist):
        """
        zindexlist: list
            List of indexes for the desired focus
        """
        assert len(zindexlist) == len(self._specList), 'length of zindexlist must match number of points'
        self._focusedSpec=[]
        for point, index in zip(self._specList,zindexlist):
            self._focusedSpec.append(point[index])
        
    def get_NVratio(self,maxwavelen=638,*args,**kwargs):
        """
        Finds best focus at given wavelength for each point, 
        
        maxwavelen: int or float, optional
            Default is 638nm, maximizing to NVm ZPL
        """
        NVvalues=[]
        if self._focusedSpec==[]:
            indexList = self.find_focus(maxwavelen)
            
        for point in self._focusedSpec:
            NVvalues.append(point.get_NVratio(*args,**kwargs))
        
        NVvalues = py.asarray(NVvalues)
        
        return NVvalues

    def plot_points(self, *args, **kwargs):
        """ 
        Plots focused points
        to plot legend, use showlegend = True keyword argument
        """
        assert len(self._focusedSpec) != 0, "haven't found focus yet"
        
        for i in range(len(self._focusedSpec)):
            if i > 6:
                fmt = '--'
            else:
                fmt = '-'
            self._focusedSpec[i].plot(label=str(i),linestyle=fmt,*args, **kwargs)
        py.legend()
        
    def remove_point(self,pointindex):
        """
        Removes crappy points as necessary, inputting an index or a list of index
        """
        assert self._focusedSpec !=[], 'FocusedSpec list must have values'
        # need to insert some way of making sure the list of pointindexes are sorted from lowest to highest
        if type(pointindex) is list:
            for point in pointindex[::-1]:
                del self._focusedSpec[point]
        elif type(pointindex) is int:
            del self._focusedSpec[pointindex]
        else: 
            raise 'pointindex must be either list or int'