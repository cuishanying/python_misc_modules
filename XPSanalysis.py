'''
Created on Feb 18, 2013

@author: Shanying
'''

import pylab

def load_tilt(fname):
    """
    Returns a list of dictionary. Each dictionary has tilt, name, position, fwhm, rsf, area, and concentration
    
    fname : str
        txt file, saved from CasaXPS
    """
    f=open(fname)
    linecount=0
    data = []
    for line in f.readlines():
        linecount += 1
        if linecount > 3:
            if line == '\n':
                break
            print line.split('\t')
            readtilt=line.split('\t')[0]
            if readtilt is not '':
                tilt=float(line.split('\t')[0])
            name=line.split('\t')[1]
            position,fwhm,rsf,area,conc=[float(d) for d in line.split('\t')[2:-1]]
            d=dict(tilt=tilt,name=name,position=position,fwhm=fwhm,rsf=rsf,area=area,conc=conc)
            data.append(d)
            
    return data

def plot_composition_tilt(fname):
    """
    I don't think this function is complete...
    
    fname : str
        txt file, saved from CasaXPS
    """
    data=load_tilt(fname)
    elements=[]
    for d in data:
        if len(elements)==0:
            elements.append(d['name'])
        elif d['name'] is not elements[0]:
            elements.append(d['name'])
        elif d['name'] is elements[0]:
            break
    print elements
    p=121
    for element in elements:
        #print element
        for d in data:
            if d['name'] is element:
                pylab.subplot(p)
                pylab.plot(d['tilt'],d['conc'],marker='o',color='r')
        p=122
    pylab.show()
                    
def plot_survey(fnames, normalize=True, yoffset=0):
    """
    Plots survey spectrum
    
    fnames: str or list
        If plotting only one survey, input just the txt filename
        If plotting multiple spectrum, input a list of txt filenames
    normalize: boolean, optional
        Default is True
    yoffset: float, optional
        Default is 0
    """
    if type(fnames) == str:
        survey=pylab.loadtxt(fnames,skiprows=4)
        BE=survey[:,1]
        spectrum=survey[:,2]
        
        if normalize==True:
            norm=max(spectrum)
        else:
            norm=1
        spectrum=spectrum/norm
        
        fig=pylab.figure()
        ax=fig.add_subplot(111)
        pylab.plot(BE,spectrum,'k')
        #ax.set_xlim(ax.get_xlim()[::-1])
        ax.set_yticklabels([])
        for label in ax.xaxis.get_ticklabels():
            label.set_fontsize(18)
        pylab.xlabel('Binding Energy (eV)',fontsize=18)
        pylab.ylabel('Counts (a.u.)',fontsize=18)
        pylab.xlim([BE[0],0])
        pylab.show()
        
    elif type(fnames) == list:
    
        fig=pylab.figure()
        ax=fig.add_subplot(111)
        
        numfiles=len(fnames)   
        for filenum in pylab.arange(numfiles):
            survey=pylab.loadtxt(fnames[filenum], skiprows=4)
            BE=survey[:,1]
            spectrum=survey[:,2]
            
            if normalize == True:
                norm=max(spectrum)
            else:
                norm=1
            spectrum=spectrum/norm
            
            pylab.plot(BE,spectrum+yoffset*filenum,'k')
            
        #ax.set_xlim(ax.get_xlim()[::-1])
        ax.set_yticklabels([])
        for label in ax.xaxis.get_ticklabels():
            label.set_fontsize(18)
        pylab.xlabel('Binding Energy (eV)',fontsize=18)
        pylab.ylabel('Counts (a.u.)',fontsize=18)
        pylab.xlim([BE[0],0])
        pylab.show()
        

def plot_highres(fnames, normalize=True, yoffset=0, plotenv=False, plotbkgd=False):
    """
    Plots high resolution spectrum, empty circles for measured points, solid lines for deconvoluted peaks. 
    
    fnames: str or list
        If plotting only one survey, input just the txt filename
        If plotting multiple spectrum, input a list of txt filenames
    normalize: boolean, optional
        Default is True
    yoffset: float, optional
        Default is 0
    plotenv: boolean, optional
        Plots the envelope of the deconvoluted peaks in solid line. Default is False.
    plotbkgd: boolean, optional
        Plots the background of the peak in solid line. Default is False.
    """
    if type(fnames) == str:
        fig=pylab.figure()
        ax=fig.add_subplot(111)
        d=pylab.loadtxt(fnames,skiprows=4)
        KE=d[:,0]
        BE=d[:,1]
        cts=d[:,2]
        
        if normalize==True:
            norm=max(cts)
        elif normalize==False:
            norm=1
        
        cts=cts/norm + yoffset
        peaks=d[:,3:-2]/norm + yoffset
        numpeaks=pylab.shape(peaks)[1]
        background=d[:,-2]/norm + yoffset
        envelope=d[:,-1]/norm + yoffset
        
        pylab.scatter(BE,cts,facecolors='none',edgecolors='grey')
        #colors=['b','r','g','c','m','y','k','b--','r--','g--','c--','m--','y--',]
        for i in pylab.arange(numpeaks):
            pylab.plot(BE, peaks[:,i],'k')
        
        if plotenv == True:
            pylab.plot(BE,envelope,'k')
        if plotbkgd == True:
            pylab.plot(BE, background, 'k')
        
        ax.set_yticklabels([])
        for label in ax.xaxis.get_ticklabels():
            label.set_fontsize(18)
        pylab.xlabel('Binding Energy (eV)',fontsize=18)
        pylab.ylabel('Counts (a.u.)',fontsize=18)
        pylab.xlim([BE[0],BE[-1]])
        pylab.show()
    
    elif type(fnames) == list:
        
        fig=pylab.figure()
        ax=fig.add_subplot(111)
        
        numfiles=len(fnames)   
        for filenum in pylab.arange(numfiles):
            d=pylab.loadtxt(fnames[filenum], skiprows=4)
            BE=d[:,1]
            cts=d[:,2]
            
            if normalize == True:
                norm=max(cts)
            else:
                norm=1
            cts=cts/norm + yoffset*filenum
            peaks=d[:,3:-2]/norm + yoffset*filenum
            numpeaks=pylab.shape(peaks)[1]
            background=d[:,-2]/norm + yoffset*filenum
            envelope=d[:,-1]/norm + yoffset*filenum
            
            pylab.scatter(BE,cts,facecolors='none',edgecolors='grey')
            for i in pylab.arange(numpeaks):
                pylab.plot(BE, peaks[:,i],'k')
        
            if plotenv == True:
                pylab.plot(BE,envelope,'k')
            if plotbkgd == True:
                pylab.plot(BE, background, 'k')
        
        pylab.xlim([BE[0],BE[-1]])
            
        #ax.set_yticklabels([])
        for label in ax.xaxis.get_ticklabels():
            label.set_fontsize(18)
        pylab.xlabel('Binding Energy (eV)',fontsize=18)
        pylab.ylabel('Counts (a.u.)',fontsize=18)
        pylab.xlim([BE[0],BE[-1]])
        pylab.show()

    