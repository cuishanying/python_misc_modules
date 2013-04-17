'''
Created on Apr 15, 2013

@author: Shanying
'''

import NVanalysis as nv
from pylab import show, shape, mean, std, asarray

class testSpectrum():
    
    def testNV(self):
        specFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130305-Igor-CF4_D0p6-200u-600g-50x-3s10x/2p5minO2_fullspectrum_D0p6-200u-100x-1s10x.txt'
        spec=nv.Spectrum(specFile)
        
        #spec.plot()
        #NV0area = spec.int_peak(fitrange = [567, 581], intrange = [573.5, 581],plot=True)
        #print NV0area
        NVratios = spec.get_NVratio(plot=True)
        print NVratios
        show() 

class testFocusMap():

    def testLoad(self):
        mapFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130305-Igor-CF4_D0p6-200u-600g-50x-3s10x/2p5minO2_spot1_zscan.txt'
        map=nv.Map(mapFile)      
        print map.get_wavelen()
        print map.get_specList()
        print map.get_zvals()

    def testNV(self):
        mapFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130305-Igor-CF4_D0p6-200u-600g-50x-3s10x/2p5minO2_spot1_zscan.txt'
        map=nv.Map(mapFile)
        print map.get_NVratio()        
        
class testMap():
    
    def testLoad(self):
        mapFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130328-Kanye-acid_D1-200um-600nm-600g-50xobj-1s10x/3x3map_z-8to8um.txt'
        map=nv.Map(mapFile)
        print map.get_wavelen()
        print map.get_specList()
        print map.get_zvals()
    
    def testNV(self):
        mapFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130328-Kanye-acid_D1-200um-600nm-600g-50xobj-1s10x/3x3map_z-8to8um.txt'
        map=nv.Map(mapFile)
        NV= map.get_NVratio()
        print NV
        print mean(NV[:,2]), std(NV[:,2])
        
        # should be 0.586 +/- 0.013
        
    def testPlot(self):
        mapFile = 'C:/Users/Shanying/Documents/Hu lab/Data/PL/130328-Kanye-acid_D1-200um-600nm-600g-50xobj-1s10x/3x3map_z-8to8um.txt'
        map=nv.Map(mapFile)
        map.find_focus(638)
        map.plotPoints()
        
test=testMap()
test.testNV()