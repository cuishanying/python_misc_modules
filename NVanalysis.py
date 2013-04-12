### My name is Shanying! I wrote this piece'o shit! Today's date is 04/11/2013
### This is now the new version where I make shit awesome!!
### Test pushing.

import pylab as py
import winspec

def load_520exc(files,NV0fitrange=[573,586], NVmfitrange=[636,648]):
    """
    files: list
    """
    data=[winspec.Spectrum(f) for f in files]
    
    NV=py.zeros((py.size(data),3))
    NV[:,0]=[int_peak(d.wavelen, d.lum, fitrange=NV0fitrange) for d in data]
    NV[:,1]=[int_peak(d.wavelen, d.lum,fitrange=NVmfitrange) for d in data]
    NV[:,2]=NV[:,1]/(NV[:,0]+NV[:,1])
            
    return NV
    
def load_highgrating(files,NV0fitrange=[568,580],NV0intrange=[574,580],NVmfitrange=None):
    """
    files: list
    format: str
    """
    dataNV0=[]
    dataNVm=[]
    for f in files:
        if f.find('NV0') is not -1:
            dataNV0.append(winspec.Spectrum(f))
        elif f.find('NVm') is not -1:
            dataNVm.append(winspec.Spectrum(f))
        else:
            raise ValueError(f,'filename must contain either "NV0" or "NVm"')
    
    data=py.vstack([dataNV0,dataNVm])
    NV=py.zeros((py.size(dataNV0),3))

    NV[:,0]=[int_peak(d.wavelen, d.lum, fitrange=NV0fitrange,intrange=NV0intrange) for d in dataNV0]
    NV[:,1]=[int_peak(d.wavelen, d.lum,fitrange=NVmfitrange) for d in dataNVm]
    NV[:,2]=NV[:,1]/(NV[:,0]+NV[:,1])
            
    return NV

def find_focus (filename, maxwavelen=638):
    wavelen=py.loadtxt(filename)[0]
    data=py.loadtxt(filename,skiprows=1)
    
    if wavelen[0] > wavelen[-1]:
        reverse=True
        NVmindex=py.where(wavelen>maxwavelen)[0][-1]+1
    else:
        reverse=False
        NVmindex=py.where(wavelen>maxwavelen)[0][0]+1
    
    NVint=data[0][NVmindex]
    bestfocus=0       
    for focus in py.arange(py.shape(data)[0]):
        if data[focus][NVmindex] > NVint:
            NVint=data[focus][NVmindex]
            bestfocus=data[focus][0]
    print 'best focus is ', bestfocus        
    return wavelen, data[bestfocus][1:]

def find_focus_map (filename, npoints, maxwavelen=638) :
    """
    returns wavelength, list of lum where each row is a different point 
    
    filename: str
        txt filename
        first row: wavelen
        2nd to end row: luminescence data, including scan properties (len = len(wavelen)+3)
        col0: z, col1 and 2: x and y, col3 to end: luminescence
    npoints: total number of points (x and y)
    
    returns: wavelen (low to high), array of luminescence at best focus
    """
    wavelen=py.loadtxt(filename)[0]
    data=py.loadtxt(filename,skiprows=1)
    
    # sort
    data=list(data)
    data.sort( key=lambda x: x[1])
    data.sort( key=lambda x: x[2])
    nfocus=len(data)/npoints
    data=py.asarray(data)
    
    # find index, depending on if saved data goes from low to high or high to low in wavelength
    if wavelen[0] > wavelen[-1]:
        reverse=True
        NVmindex=py.where(wavelen>maxwavelen)[0][-1]+3
    else:
        reverse=False
        NVmindex=py.where(wavelen>maxwavelen)[0][0]+3
    
    # find index of maximum NV intensity per xy-point
    NVmintensity=py.zeros(npoints)
    maxindex=py.zeros(npoints)
    
    row=0
    while row < data.shape[0]:
        for point in py.arange(npoints):
            for focus in py.arange(nfocus):
                readNVm=data[row,NVmindex]
                if readNVm>NVmintensity[point]:
                    NVmintensity[point]=readNVm
                    maxindex[point]=row
                row+=1

    # save and return wavelen (from low to high), luminescence
    if reverse is True:
        wavelen=wavelen[::-1]

    maxdata=[]
    maxfocus=[]
    for point in maxindex:
        maxfocus.append(data[point][0])
        if reverse is True:
            maxdata.append(data[point][3:][::-1])
        else:
            maxdata.append(data[point][3:])
    print 'focus is ', maxfocus
    return wavelen, maxdata

def plot(wavelen, maxdata, *args, **kwargs):
    for i in range(len(maxdata)):
        if i > 6:
            fmt = '--'
        else:
            fmt = '-'
        py.plot(wavelen, maxdata[i],label=str(i),linestyle=fmt)
    py.legend()
            
def int_peak (wavelen, lum, fitrange=None, intrange=None, normalize=False, plot=False, npoints=10):
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
    if wavelen[0]>wavelen[-1]:
        wavelen=wavelen[::-1]
        lum=lum[::-1]
        
    if normalize is True:
        lum/=lum.max()
    
    if fitrange is None:
        fitindex=[0+npoints/2, len(wavelen)-1-npoints/2]
    else:
        fitindex=[0, 0]
        fitindex[0]=py.where(wavelen>fitrange[0])[0][0]
        fitindex[1]=py.where(wavelen>fitrange[1])[0][0]
    
    wavelenfit=py.concatenate((wavelen[fitindex[0]-npoints/2:fitindex[0]+npoints/2], 
                           wavelen[fitindex[1]-npoints/2:fitindex[1]+npoints/2]))
    lumfit=py.concatenate((lum[fitindex[0]-npoints/2:fitindex[0]+npoints/2], 
                        lum[fitindex[1]-npoints/2:fitindex[1]+npoints/2]))
    linearfit = py.polyfit(wavelenfit, lumfit, 1)
    linear_bg = py.polyval( linearfit, wavelen[fitindex[0]:fitindex[1]+1] )
    wavelen_bg = wavelen[fitindex[0]:fitindex[1]+1].copy()
    lum_bg = lum[fitindex[0]:fitindex[1]+1].copy()
    lum_bg -= linear_bg
    
    if plot is True:
        py.plot(wavelen,lum,'k')
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

def int_NVpeaks(wavelen, lum,NV0fitrange = [567, 581],NV0intrange = [573.5, 581],NVmfitrange = [633, 644],plot=False):
    NV0=int_peak(wavelen, lum, fitrange=NV0fitrange, intrange=NV0intrange, plot=plot)
    NVm=int_peak(wavelen, lum, fitrange=NVmfitrange,plot=plot)
    
    return [NV0,NVm,NVm/(NV0+NVm)]