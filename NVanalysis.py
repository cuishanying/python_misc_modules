### My name is Shanying! I wrote this piece'o shit! Today's date is 04/11/2013
### This is now the new version where I make shit awesome!!
### Test pushing.

import pylab as py
import winspec
from numpy import ndarray

class Spectrum():
    """
    This class loads a .SPE file or .txt file
    for .txt file (saved from Clarke's Raman), 
    first column is wavelength and 2nd column is luminescence
    """
    
    """ String for .txt filename """
    _fname = ''
    
    """ List of wavelengths in this spectrum"""
    _wavelen = []
    
    """ List of luminescenses associated with the wavelength at each index""" 
    _lum = []
    
    """ Boolean to determine if file has been saved from low-to-high wavelengths"""
    _reverse = False
    
    def __init__(self,*args):
        if len(args) == 1:
            assert type(args[0]) is str, "input must be either one str, or 2 lists"
            
            self._fname = args[0]
            self._wavelen = py.loadtxt(self._fname)[:,0]    
            if self._wavelen[0] > self._wavelen[-1]:
                self._wavelen = self._wavelen[::-1]
                self._reverse=True
                
            self._lum = py.loadtxt(self._fname)[:,1]
            if self._reverse is True:
                self._lum = self._lum[::-1]
                
            assert len(self._wavelen) == len(self._lum), "Wavelength and luminescence length should match"
        elif len(args) == 2:
            assert type(args[0]) is ndarray or type(args[0]) is list, "first input must be list or ndarray"
            assert type(args[1]) is ndarray or type(args[0]) is list, "second input must be list or ndarray"
            
            self._wavelen = args[0]
            self._lum = args[1] 
        
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
    

class Map():
    
    """ filename """
    _fname = ''
    _wavelen=[]
    _specList=[]
    _reverse=False
    _z=[]
    _nfocus=0
    
    def __init__(self,fname):
        """
        initializes Map object, and loads a z scan or x, y, z map. 
        """
        
        self._fname = fname
        self._wavelen = py.loadtxt(self._fname)[0]
        if self._wavelen[0] > self._wavelen[-1]:
            self._wavelen = self._wavelen[::-1]
            self._reverse=True
            
        data = py.loadtxt(self._fname,skiprows=1)
        
        # check what kind of a file it is
        lendiff = py.shape(data)[1] - len(self._wavelen)
        if lendiff == 1:
            self.load_focus(data)
        if lendiff == 3:
            self.load_map(data)
    
    def get_wavelen(self):
        return self._wavelen
    
    def get_specList(self):
        return self._specList
    
    def get_zvals(self):
        return self._z
    
    def load_focus(self,data):
        """
        return list of Spectrum 
        """
        self._z=data[:,0]
        self._nfocus=len(data[:,0])
        for focus in data:
            if self._reverse == True:
                lum = focus[1:][::-1]
            else:
                lum = focus[1:]
            self._specList.append(Spectrum(self._wavelen,lum))
        
        self._specList=[self._specList] # only one point
        
        assert len(self._specList[0]) == self._nfocus, "Num focus points must equal num of luminescence"
        
    def load_map(self,data):
        
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
            if self._reverse == True:
                lum = row[3:][::-1]
            else:
                lum = row[3:]
            self._specList.append(Spectrum(self._wavelen,lum))

        # split specList into points, ie. [[z1, z1, z3],[z1,z2,z3]]
        self._specList=[self._specList[i:i+self._nfocus] for i in range(0,len(self._specList),self._nfocus)]
        self._z = (data[:,0][0:self._nfocus])
        
        assert len(self._z) == len(self._specList[0]), "len of focuses must match specList sublist length"        

    def find_focus(self, wavelen,plot=False):
        """
        within a list of spectrum objects of the same point and a wavelength, find the focus of highest intensity
        Returns list index values where the lum is maximized for each point in map
        
        wavelen: int or float
            Finds focus with max luminescence at this wavelength (nm) 
        """
        lum = []
        maxlum_index = []
        for point in self._specList:
            if plot == True:
                py.figure()
            for spec in point:
                lum.append(spec.get_lumAtWavelen(wavelen))
                if plot == True:
                    spec.plot()
            maxlum_index.append(lum.index(max(lum)))
            lum = []
             
        return  maxlum_index
    
    def get_NVratio(self,maxwavelen=638,*args,**kwargs):
        """
        Finds best focus at given wavelength for each point, 
        
        maxwavelen: int or float, optional
            Default is 638nm, maximizing to NVm ZPL
        """
        NVvalues=[]
        indexList = self.find_focus(maxwavelen)
            
        for i in py.arange(len(self._specList)):
            focusedPoint = self._specList[i][indexList[i]]
            NVvalues.append(focusedPoint.get_NVratio(*args,**kwargs))
        
        return NVvalues

    def plot(self,maxdata, *args, **kwargs):
        """ copied directly from previous version, not complete"""
        for i in range(len(maxdata)):
            if i > 6:
                fmt = '--'
            else:
                fmt = '-'
            py.plot(self._wavelen, maxdata[i],label=str(i),linestyle=fmt)
        py.legend()
        
    def removeData(self):
        """
        Removes crappy spectra as necessary
        """