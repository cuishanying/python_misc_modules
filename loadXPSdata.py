'''
Created on Nov 30, 2012

@author: Shanying
'''

def load_tilt(fname):
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

#print data
#for i in data:
#    if i['name'] == 'C 1s':
#        pylab.subplot(221)
#        pylab.plot(i['tilt'],i['conc'],marker='o',color='r',label=i['name'])
#        pylab.xlim([-5,65])
#        pylab.ylabel('% concentration')
#        pylab.title(i['name'])
#    if i['name'] == 'F 1s':
#        pylab.subplot(222)
#        pylab.plot(i['tilt'],i['conc'],marker='o',color='b',label=i['name'])
#        pylab.xlim([-5,65])
#        pylab.title(i['name'])
#    if i['name'] == 'O 1s':
#        pylab.subplot(223)
#        pylab.plot(i['tilt'],i['conc'],marker='o',color='g',label=i['name'])
#        pylab.xlim([-5,65])
#        pylab.xlabel('Tilt angle')
#        pylab.ylabel('% concentration')
#        pylab.title(i['name'])
#    if i['name'] == 'Al 2p':
#        pylab.subplot(224)
#        pylab.plot(i['tilt'],i['conc'],marker='o',color='k',label=i['name'])
#        pylab.xlim([-5,65])
#        pylab.xlabel('Tilt angle')    
#        pylab.title(i['name'])       
#pylab.show()
#        