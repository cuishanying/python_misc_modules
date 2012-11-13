# PicoHarp 300    File Access Utility
# ported from the PicoQuant matlab demo to python by KJR, Oct 2010
# (for python version 2.6)

# This script reads a binary PicoHarp 300 data file (*.phd)
# and returns its contents. Works with file format version 2.0 only!

# Original Matlab code disclaimer:
# Peter Kapusta, PicoQuant GmbH, September 2006
# This is demo code. Use at your own risk. No warranties.
# Make sure you have enough memory when loading large files!

import sys
import os.path
import struct # deal with binary data
import pylab
import numpy as np
from scipy.optimize import curve_fit, leastsq
from scipy.signal import cspline1d, cspline1d_eval

class Trace():
    """ A class for holding lifetime data. You pass
        it the name of the phdfile (including .phd)
        and it will load it and offer various methods
        for plotting, wrapping (removing time offset)
        and fitting exponentials.
    """
    def __init__( self, phdfile ):
        self.fname = phdfile
        self.has_fit = False
        self.ax = None
        self.irf = None
        self.wraptime = None
        self.in_counts_per_second = False
        with open( phdfile, 'rb' ) as self.fobj:
            self.readasciiheader( verbose=False )
            self.readbinaryheader( verbose=False )
            self.readboardheader()
            self.readcurveheaders( verbose=False )
            self.readhistograms()
            self.resolution = self.curveheaders[0]['Resolution'] # curve 0 resolution, actually (ns)
            self.t = []
            for i, curve in enumerate( self.curves ):
                self.t.append( pylab.arange(len(curve))*self.curveheaders[i]['Resolution'] )# this is in ns
            self.raw_t = self.t[:]
        
    def fit_exponential( self, tstart=0.0, tend=None, guess=dict( l0=5.0, a0=1.0, b=0.0 ), num_exp=None,
                         verbose=True, deconvolve=False, fixed_params=[None], 
                         curve_num=0 ):
        """
        fit a function of exponentials to a single curve of the file
        (my files only have one curve at this point anyway,
        curve 0). 
        The parameter num_exp (default is 1, max is 3) defines the number of
        exponentials in the funtion to be fitted.
        num_exp=1 yields:
        f(t) = a0*exp(-t/l0) + b
        where l0 is the lifetime and a0 and b are constants,
        and we fit over the range from tstart to tend.
        You don't have to pass this parameter anymore; just pass an initial guess and
        the number of parameters passed will determine the type of model used.
        
        If tend==None, we fit until the end of the curve.
        
        If num_exp > 1, you will need to modify the initial
        parameters for the fit (i.e. pass the method an explicit `guess`
        parameter) because the default has only three parameters
        but you will need two additional parameters for each additional
        exponential (another lifetime and another amplitude) to describe
        a multi-exponential fit. 
        For num_exp=2:
        f(t) = a1*exp(-t/l1) + a0*exp(-t/l0) + b
        
        and for num_exp=3:
        f(t) = a2*exp(-t/l2) + a1*exp(-t/l1) + a0*exp(-t/l0) + b
        
        verbose=True (default) results in printing of fitting results to terminal.
        
        """
        self.fitstart = tstart
        self.deconvolved = deconvolve
        tpulse = 1.0e9/self.curveheaders[0]['InpRate0'] # avg. time between pulses, in ns

        if num_exp is None:
            num_exp = 1 + int(guess.has_key('l1')) + int(guess.has_key('l2')) + int(guess.has_key('l3')) + int(guess.has_key('l4'))
            if num_exp != 1 + int(guess.has_key('a1')) + int(guess.has_key('a2')) + int(guess.has_key('a3')) + int(guess.has_key('a4')):
                raise ValueError("Missing a parameter! Unequal number of lifetimes and amplitudes.")

        keylist = [ "l0", "a0", "b" ]
        errlist = [ "l0_err", "a0_err" ]
        if num_exp == 2:
            keylist = [ "l1", "a1", "l0", "a0", "b" ]
            errlist = [ "l1_err", "a1_err", "l0_err", "a0_err" ]
        elif num_exp == 3 and not guess.has_key('t_ag') and not guess.has_key('t_d3'):
            keylist = [ "l2", "a2", "l1", "a1", "l0", "a0", "b" ]
            errlist = [ "l2_err", "a2_err", "l1_err", "a1_err", "l0_err", "a0_err" ]
        elif num_exp == 3 and guess.has_key('t_ag'):
            keylist = [ "l2", "a2", "l1", "a1", "l0", "a0", "t_ag" ]
            errlist = [ "l2_err", "a2_err", "l1_err", "a1_err", "l0_err", "a0_err" ]
        elif num_exp == 3 and guess.has_key('t_d3'):
            keylist = [ "l2", "a2", "l1", "a1", "l0", "a0", "t_d3" ]
            errlist = [ "l2_err", "a2_err", "l1_err", "a1_err", "l0_err", "a0_err" ]
        elif num_exp == 4:
            keylist = [ "l3", "a3", "l2", "a2", "l1", "a1", "l0", "a0", "b" ]
            errlist = [ "l3_err", "a3_err", "l2_err", "a2_err", "l1_err", "a1_err", "l0_err", "a0_err" ]
        elif num_exp == 5:
            keylist = [ "l4", "a4", "l3", "a3", "l2", "a2", "l1", "a1", "l0", "a0", "b" ]
            errlist = [ "l4_err", "a4_err", "l3_err", "a3_err", "l2_err", "a2_err", "l1_err", "a1_err", "l0_err", "a0_err" ]
                    
                    
        # sigma (std dev.) is equal to sqrt of intensity, see
        # Lakowicz, principles of fluorescence spectroscopy (2006)
        # sigma gets inverted to find a weight for leastsq, so avoid zero
        # and imaginary weight doesn't make sense.
        trace_scaling = self.curves[0].max()/self.raw_curves[0].max()
        sigma = pylab.sqrt(self.raw_curves[curve_num]*trace_scaling) # use raw curves for actual noise, scale properly
        if pylab.any(sigma==0): # prevent division by zero
            iz = pylab.find(sigma==0)
            sigma[iz] = 1

        if deconvolve==False:
            params = [ guess[key] for key in keylist ]
            free_params = [ i for i,key in enumerate(keylist) if not key in fixed_params ]
            initparams = [ guess[key] for key in keylist if not key in fixed_params ]
            def f(t, *args ):
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                local_params = params[:]
                b = local_params.pop(-1)
                result = pylab.zeros(len(t))
                for l,a in zip(params[::2],params[1::2]):
                    result += abs(a)*pylab.exp(-(t-tstart)/abs(l))
                return result+b

            istart = pylab.find( self.t[curve_num] >= tstart )[0]
            if tend is not None:
                iend = pylab.find( self.t[curve_num] <= tend )[-1]
            else:
                iend = len(self.t[curve_num])

            self.bestparams, self.pcov = curve_fit( f, self.t[curve_num][istart:iend],
                                            self.curves[curve_num][istart:iend],
                                            p0=initparams,
                                            sigma=sigma[istart:iend])
        else:
            if self.irf == None: raise AttributeError("No detector trace!!! Use self.set_detector() method.")
            t0 = tstart
            tstart = 0.0
            istart = 0
            iend = -1
            assert guess.has_key("tshift") or guess.has_key("trise")
            if guess.has_key("tshift"):
                keylist.append( "tshift" )
            else:
                tshift=0.0
            
            if guess.has_key("trise"):
                keylist.append( "trise" )
            
            params = [ guess[key] for key in keylist ]
            free_params = [ i for i,key in enumerate(keylist) if not key in fixed_params ]
            initparams = [ guess[key] for key in keylist if not key in fixed_params ]

            def f( t, *args ): # only gets used for bestfit line
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                local_params = params[:]
                if guess.has_key("trise"): trise = local_params.pop(-1)
                if guess.has_key("tshift"):
                    tshift = local_params[-1]
                else:
                    tshift = 0.0
                ideal = fmodel( t, *args )
                irf = cspline1d_eval( self.irf_generator, t-tshift, dx=self.irf_dt, x0=self.irf_t0 )
                convoluted = pylab.real(pylab.ifft( pylab.fft(ideal)*pylab.fft(irf) )) # very small imaginary anyway
                return convoluted

            def fmodel( t, *args ):
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                local_params = params[:]
                if guess.has_key("trise"): trise = local_params.pop(-1)
                if guess.has_key("tshift"): tshift = local_params.pop(-1)
                if guess.has_key('t_ag'):
                    t_ag = abs(local_params.pop(-1))
                elif guess.has_key('t_d3'):
                    t_d3 = abs(local_params.pop(-1))
                elif guess.has_key('a_fix'):
                    scale = local_params.pop(-1)
                else:
                    b = local_params.pop(-1)
                    
                result = pylab.zeros(len(t))
                for l,a in zip(local_params[::2],local_params[1::2]):
                    if guess.has_key('t_ag'): l = 1.0/(1.0/l + 1.0/t_ag)
                    if guess.has_key('t_d3'): l *= t_d3
                    if guess.has_key('a_fix'): a *= scale
                    result += abs(a)*pylab.exp(-t/abs(l))/(1.0-pylab.exp(-tpulse/abs(l)))
                if guess.has_key("trise"): result *= (1.0-pylab.exp(-t/abs(trise)))
                return result

            import pyximport; pyximport.install()
            import FastFit
            model = "multi_exp"
            Function = FastFit.Convolved(
                    model,
                    pylab.array(params,dtype=np.float),
                    pylab.array(free_params,dtype=np.float),
                    guess,
                    tpulse,
                    self.irf_dt,
                    self.irf_t0,
                    self.irf_generator,
                    sigma )
            res = Function.fit( self.t[curve_num], self.curves[curve_num], np.array(initparams,dtype=np.float) )
            (self.bestparams, self.pcov, infodict, errmsg, ier) = res

        if pylab.size(self.pcov) > 1 and len(pylab.find(self.pcov == pylab.inf))==0:
            self.stderr = pylab.sqrt( pylab.diag(self.pcov) ) # is this true?
        else:
            self.stderr = [pylab.inf]*len(guess)
            
        stderr = [np.NaN]*len(params)
        for i,p in enumerate(self.bestparams):
            params[ free_params[i] ] = p
            stderr[ free_params[i] ] = self.stderr[i]
        self.stderr = stderr

        self.fitresults = dict()
        keys = keylist[:]
        stderr = stderr[:]
        p = params[:]
        if deconvolve:
            if guess.has_key("trise"):
                trise=p.pop(-1)
                self.fitresults['trise'] = np.abs(trise)
                trise_err = stderr.pop(-1)
                self.fitresults['trise_err'] = trise_err
            if guess.has_key("tshift"):
                tshift = p.pop(-1)
                self.fitresults['tshift'] = tshift
                tshift_err = stderr.pop(-1)
                self.fitresults['tshift_err'] = tshift_err
            keys.pop(-1)
            self.fitresults['irf_dispersion'] = self.irf_dispersion

        b = p.pop(-1)
        self.fitresults['b'] = b
        b_err = stderr.pop(-1)
        self.fitresults['b_err'] = b_err
        keys.pop(-1)
        self.lifetime = [ abs(l) for l in p[::2] ]
        lsorted, asorted = zip(*sorted(zip(p[::2],p[1::2]), key=lambda x: -abs(x[0]))) # sort with shortest lifetime as l0
        for l,a,lkey,akey in zip(lsorted, asorted, keys[::2], keys[1::2]):
            if guess.has_key('t_ag'): l = 1.0/(1.0/l + 1.0/b)
            if guess.has_key('t_d3'): l *= b
            if guess.has_key('a_fix'): a *= b
            self.fitresults[lkey] = abs(l)
            self.fitresults[akey] = abs(a)
        for l,a,lkey,akey in zip(stderr[::2],stderr[1::2],errlist[::2],errlist[1::2]):
            self.fitresults[lkey] = l
            self.fitresults[akey] = a
        self.fitresults['l0_int'] = self.fitresults['l0']*self.fitresults['a0']

        if num_exp > 1: self.fitresults['l1_int'] = self.fitresults['l1']*self.fitresults['a1']
        if num_exp > 2: self.fitresults['l2_int'] = self.fitresults['l2']*self.fitresults['a2']
        if num_exp > 3: self.fitresults['l3_int'] = self.fitresults['l3']*self.fitresults['a3']
        if num_exp > 4: self.fitresults['l4_int'] = self.fitresults['l4']*self.fitresults['a4']

        self.bestfit = f( self.t[curve_num], *self.bestparams )
        if deconvolve: self.model = fmodel( self.t[curve_num], *self.bestparams )
        Chi2 = pylab.sum( (self.bestfit - self.curves[0])**2 / sigma**2 )
        Chi2 *= self.raw_curves[0].max()/self.curves[0].max() # undo any scaling
        mean_squares = pylab.mean( (self.bestfit - self.curves[0])**2 )
        degrees_of_freedom = len(self.bestfit) - len(free_params)
        self.fitresults['MSE'] = mean_squares/degrees_of_freedom
        self.fitresults['ReducedChi2'] = Chi2/degrees_of_freedom

        if verbose:
            print "Fit results: (Reduced Chi2 = %.3E)" % (self.fitresults['ReducedChi2'])
            print "             (MSE = %.3E)" % (self.fitresults['MSE'])
            print "  Offset/t_ag/scale = %.3f +-%.3e" % (self.fitresults['b'], self.fitresults['b_err'])
            print "  l0=%.3f +-%.3f ns, a0=%.3e +-%.3e" % (self.fitresults['l0'],
                                                            self.fitresults['l0_err'],
                                                            self.fitresults['a0'],
                                                            self.fitresults['a0_err'])
            if num_exp > 1:
                print "  l1=%.3f +-%.3f ns, a1=%.3e +-%.3e" % (self.fitresults['l1'],
                                                            self.fitresults['l1_err'],
                                                            self.fitresults['a1'],
                                                            self.fitresults['a1_err'])
            if num_exp > 2:
                print "  l2=%.3f +-%.3f ns, a2=%.3e +-%.3e" % (self.fitresults['l2'],
                                                            self.fitresults['l2_err'],
                                                            self.fitresults['a2'],
                                                            self.fitresults['a2_err'])
            if num_exp > 3:
                print "  l3=%.3f +-%.3f ns, a3=%.3e +-%.3e" % (self.fitresults['l3'],
                                                            self.fitresults['l3_err'],
                                                            self.fitresults['a3'],
                                                            self.fitresults['a3_err'])
            if num_exp > 4:
                print "  l4=%.3f +-%.3f ns, a4=%.3e +-%.3e" % (self.fitresults['l4'],
                                                            self.fitresults['l4_err'],
                                                            self.fitresults['a4'],
                                                            self.fitresults['a4_err'])
            print " "

        self.has_fit = True


    def fit_stretched_exponential( self, tstart=0.0, tend=None, guess=dict( l0=5.0, a0=1.0, h0=1.0 ),
                         verbose=True, deconvolve=False, fixed_params=[None], 
                         curve_num=0 ):
        """
        fit a stretched exponential to a single curve of the file
        (my files only have one curve at this point anyway, curve 0). 
        verbose=True (default) results in printing of fitting results to terminal.
        
        """
        self.fitstart = tstart
        self.deconvolved = deconvolve
        tpulse = 1.0e9/self.curveheaders[0]['InpRate0'] # avg. time between pulses, in ns

        keylist = [ "l0", "a0", "h0" ]
        errlist = [ "l0_err", "a0_err", "h0_err" ]
        
        if guess.has_key('l1'):
            keylist.append("l1")
            keylist.append("a1")
            keylist.append("h1")
                    
        errlist = [key+"_err" for key in keylist]
        trace_scaling = self.curves[0].max()/self.raw_curves[0].max()
        sigma = pylab.sqrt(self.raw_curves[curve_num]*trace_scaling) # use raw curves for actual noise, scale properly
        if pylab.any(sigma==0): # prevent division by zero
            iz = pylab.find(sigma==0)
            sigma[iz] = 1

        if deconvolve==False:
            raise ValueError("Not yet implemented.")
        else:
            if self.irf == None: raise AttributeError("No detector trace!!! Use self.set_detector() method.")
            t0 = tstart
            tstart = 0.0
            assert guess.has_key("tshift")
            if guess.has_key("tshift"):
                keylist.append( "tshift" )
            else:
                tshift=0.0
            
            params = [ guess[key] for key in keylist ]
            free_params = [ i for i,key in enumerate(keylist) if not key in fixed_params ]
            initparams = [ guess[key] for key in keylist if not key in fixed_params ]

            def f( t, *args ): # only gets used for bestfit line
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                local_params = params[:]
                tshift = local_params[-1]
                ideal = fmodel( t, *args )
                irf = cspline1d_eval( self.irf_generator, t-tshift, dx=self.irf_dt, x0=self.irf_t0 )
                convoluted = pylab.real(pylab.ifft( pylab.fft(ideal)*pylab.fft(irf) )) # very small imaginary anyway
                return convoluted

            def fmodel( t, *args ):
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                l, a, h = params[:3]
                if guess.has_key('l1'): l1, a1, h1 = params[3:6]
                result = pylab.zeros(len(t))
                for j in range(10): # sum over current and previous pulses
                    result += abs(a)*pylab.exp(-((t+j*tpulse)/abs(l))**(1.0/h)) # Kohlrausch function
                    #result += abs(a)*pylab.exp(1-(1+(t+j*tpulse)/abs(l))**(1.0/h)) # modified Kohlrausch function (see Berberan-Santos et al., 2005)
                    if guess.has_key('l1'):
                        result += abs(a1)*pylab.exp(-((t+j*tpulse)/abs(l1))**(1.0/h1))
                return result

            import pyximport; pyximport.install()
            import FastFit
            model = "stretched_exp"
            Function = FastFit.Convolved(
                    model,
                    pylab.array(params,dtype=np.float),
                    pylab.array(free_params,dtype=np.float),
                    guess,
                    tpulse,
                    self.irf_dt,
                    self.irf_t0,
                    self.irf_generator,
                    sigma )
            res = Function.fit( self.t[curve_num], self.curves[curve_num], np.array(initparams,dtype=np.float) )
            (self.bestparams, self.pcov, infodict, errmsg, ier) = res

        if pylab.size(self.pcov) > 1 and len(pylab.find(self.pcov == pylab.inf))==0:
            self.stderr = pylab.sqrt( pylab.diag(self.pcov) ) # is this true?
        else:
            self.stderr = [pylab.inf]*len(guess)
            
        stderr = [np.NaN]*len(params)
        for i,p in enumerate(self.bestparams):
            params[ free_params[i] ] = abs(p)
            stderr[ free_params[i] ] = self.stderr[i]
        self.stderr = stderr

        self.fitresults = dict()
        keys = keylist[:]
        stderr = stderr[:]
        p = params[:]
        if deconvolve:
            if guess.has_key("tshift"):
                tshift = p.pop(-1)
                self.fitresults['tshift'] = tshift
                tshift_err = stderr.pop(-1)
                self.fitresults['tshift_err'] = tshift_err
            keys.pop(-1)
            self.fitresults['irf_dispersion'] = self.irf_dispersion
    
        for i,p in enumerate(params): self.fitresults[keylist[i]] = p
        for i,err in enumerate(stderr): self.fitresults[errlist[i]] = err

        self.bestfit = f( self.t[curve_num], *self.bestparams )
        if deconvolve: self.model = fmodel( self.t[curve_num], *self.bestparams )
        Chi2 = pylab.sum( (self.bestfit - self.curves[0])**2 / sigma**2 )
        Chi2 *= self.raw_curves[0].max()/self.curves[0].max() # undo any scaling
        mean_squares = pylab.mean( (self.bestfit - self.curves[0])**2 )
        degrees_of_freedom = len(self.bestfit) - len(free_params)
        self.fitresults['MSE'] = mean_squares/degrees_of_freedom
        self.fitresults['ReducedChi2'] = Chi2/degrees_of_freedom

        if verbose:
            width = 15
            for key, value in sorted(self.fitresults.iteritems()):
                if value == None:
                    print '%s: None' % (key.rjust(width))
                else:
                    print '%s: %.3f' % (key.rjust(width), value)
                    
            print " "

        self.has_fit = True
        
            
    def fit_lifetime_distribution( self,
                    tstart=0.0, tend=None,
                    Tdist=lambda tau, tc, a0, dt: a0*pylab.exp(-(1/tau-1/tc)**2/2*dt**2),
                    time_array = None,
                    Npts=100,
                    guess=dict( tc=1.0, a0=1.0, dt=0.5 ),
                    verbose=True,
                    deconvolve=False,
                    fixed_params=[None], 
                    curve_num=0,
                    FakeFit=False ):
        """
        fit a distribution of lifetimes to the data.
        time_array is the 1-D array of times at which the distribution
        will be sampled.
        """
        self.fitstart = tstart
        self.deconvolved = deconvolve
        tpulse = 1.0e9/self.curveheaders[0]['InpRate0'] # avg. time between pulses, in ns

        if guess.has_key('fp0'):
            keylist = ['fp0','tR','tNR','a0']
        else:
            keylist = ['tc','a0','dt']
            assert 'tc' in keylist
        if guess.has_key('lss'): # also fitting a stretched exponential
            keylist.append("lss")
            keylist.append("ass")
            keylist.append("hss")
        errlist = [key+"_err" for key in keylist]
                    
        trace_scaling = self.curves[0].max()/self.raw_curves[0].max()
        sigma = pylab.sqrt(self.raw_curves[curve_num]*trace_scaling) # use raw curves for actual noise, scale properly
        if pylab.any(sigma==0): # prevent division by zero
            iz = pylab.find(sigma==0)
            sigma[iz] = 1

        if deconvolve==False:
            raise ValueError("Not yet implemented.")
        else:
            if self.irf == None: raise AttributeError("No detector trace!!! Use self.set_detector() method.")
            t0 = tstart
            tstart = 0.0
            assert guess.has_key("tshift")
            if guess.has_key("tshift"):
                keylist.append( "tshift" )
            else:
                tshift=0.0
            
            params = [ guess[key] for key in keylist ]
            free_params = [ i for i,key in enumerate(keylist) if not key in fixed_params ]
            initparams = [ guess[key] for key in keylist if not key in fixed_params ]

            def f( t, *args ): # only gets used for bestfit line
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                tshift = params[-1]
                ideal = fmodel( t, *args )
                irf = cspline1d_eval( self.irf_generator, t-tshift, dx=self.irf_dt, x0=self.irf_t0 )
                convoluted = pylab.real(pylab.ifft( pylab.fft(ideal)*pylab.fft(irf) )) # very small imaginary anyway
                return convoluted

            def fmodel( t, *args ):
                for i,arg in enumerate(args): params[ free_params[i] ] = arg
                local_params = params[:]
                if guess.has_key('fp0'):
                    p = local_params[:4]
                    fp0, tR, tNR, a0 = p
                    fp_array = pylab.linspace(1.0,fp0,Npts)
                    time_array = 1/(fp_array/tR + 1/tNR)
                else:
                    p = local_params[:3]
                
                result = pylab.zeros(len(t))
                for tau in time_array:
                    result += Tdist(tau,*p)*pylab.exp(-t/tau)/(1-pylab.exp(-tpulse/abs(tau)))
                if guess.has_key('lss'):
                    lss, ass, hss = local_params[-4:-1]
                    for j in range(10): # sum over previous pulses
                        result += abs(ass)*pylab.exp(-((t+j*tpulse)/abs(lss))**(1.0/hss))

                return result

            if FakeFit:
                self.bestparams, self.pcov = initparams, None
            else:
                self.bestparams, self.pcov = curve_fit( f, self.t[curve_num],
                                                self.curves[curve_num],
                                                p0=initparams,
                                                sigma=sigma)

        if pylab.size(self.pcov) > 1 and len(pylab.find(self.pcov == pylab.inf))==0:
            self.stderr = pylab.sqrt( pylab.diag(self.pcov) ) # is this true?
        else:
            self.stderr = [pylab.inf]*len(guess)
            
        self.fitresults = dict()
        for i,index in enumerate(free_params):
            self.fitresults[keylist[index]] = self.bestparams[i]
            
        self.bestfit = f( self.t[curve_num], *self.bestparams )
        if deconvolve: self.model = fmodel( self.t[curve_num], *self.bestparams )
        Chi2 = pylab.sum( (self.bestfit - self.curves[0])**2 / sigma**2 )
        Chi2 *= self.raw_curves[0].max()/self.curves[0].max() # undo any scaling
        mean_squares = pylab.mean( (self.bestfit - self.curves[0])**2 )
        degrees_of_freedom = len(self.bestfit) - len(free_params)
        self.fitresults['MSE'] = mean_squares/degrees_of_freedom
        self.fitresults['ReducedChi2'] = Chi2/degrees_of_freedom

        if verbose:
            for key, value in self.fitresults.iteritems():
                print key, value
            print " "

        self.has_fit = True

    def autocorr( self ):
        x = self.residuals()
        result = pylab.correlate( x, x, mode='full' )
        return result[result.size/2+1:]/sum(x**2)


    def residuals( self ):
        return self.bestfit - self.curves[0]


    def counts_per_second( self ):
        """
        Divide by acquisition time (self.Tacq), keeping
        note of the fact that Tacq is in milliseconds.
        """
        for i, curve in enumerate( self.curves ):
            curve = pylab.np.array( curve, dtype=pylab.np.float )
            curve /= self.Tacq/1000.0
            self.curves[i] = curve
        self.in_counts_per_second = True
        

    def get_max( self ):
        """ return a tuple containing the time and height of
            the maximum of curve[0]:
            t_max,cts_max = self.get_max()
        """
        cts_max = self.curves[0].max()
        t_max = self.t[0][ pylab.where( self.curves[0]==cts_max )[0][0] ]
        return t_max, cts_max

    def normalize( self, value=None ):
        # just a wrapper around normalize_curves
        self.normalize_curves( value=value )
        

    def normalize_curves( self, value=None ):
        """
        Normalize the curve to its maximum value (default),
        or normalize to some arbitrary value (if value != None).
        """
        for i, curve in enumerate( self.curves ):
            curve = pylab.np.array( curve, dtype=pylab.np.float )
            if value is None:
                curve /= curve.max()
            else:
                curve /= pylab.np.float(value)
            
            self.curves[i] = curve
            
    
    def plot( self, *args, **kwargs ):
        kwargs['type'] = "trace"
        return self.plot_misc( *args, **kwargs )
        
    def plotfit( self, *args, **kwargs):
        kwargs['type'] = "fit"
        return self.plot_misc( *args, **kwargs )
            
    def plotmodel( self, *args, **kwargs):
        kwargs['type'] = "model"
        return self.plot_misc( *args, **kwargs )
            
    def plotresiduals( self, *args, **kwargs):
        kwargs['type'] = "residuals"
        if not 'weighted' in kwargs.keys(): kwargs['weighted']=False
        return self.plot_misc( *args, **kwargs )
            
    def plot_misc( self, *args, **kwargs ):
        if kwargs['type'] == "trace":
            data = self.curves[0]
            t = self.t[0]
        elif  kwargs['type'] == "fit":
            t = self.t[0].copy()
            if self.deconvolved:
                data=self.bestfit
            else:
                data = self.bestfit[pylab.find(t>self.fitstart)]
                t = t[pylab.find(t>self.fitstart)]
        elif kwargs['type'] == "model":
            data = self.model
            t = self.t[0]
        elif kwargs['type'] == "residuals":
            data = self.residuals()
            if kwargs['weighted']:
                trace_scaling = self.curves[0].max()/self.raw_curves[0].max()
                data /= pylab.sqrt(self.raw_curves[0]*trace_scaling) # use raw curves in case BG was subtracted
            del kwargs['weighted']
            t = self.t[0]
        del kwargs['type']
            
        if 't0' in kwargs.keys():
            t0 = kwargs['t0']
            del kwargs['t0']
        else:
            t0 = 0.0

        if 'semilogy' in kwargs.keys():
            semilogy = kwargs['semilogy']
            del kwargs['semilogy']
        else:
            semilogy = False
        
        if 'fill' in kwargs.keys():
            fill = kwargs['fill']
            del kwargs['fill']
        else:
            fill = False
        
        if 'yoffset' in kwargs.keys():
            voffset = kwargs['yoffset']
            del kwargs['yoffset']
        else:
            voffset = 1.0e-5 # makes toggling to semilog okay with fill
        
        if self.ax is None:
            try:
                self.ax = pylab.gca()
            except AttributeError:
                f = pylab.figure(1)
                self.ax = f.add_subplot(111)
            
        if semilogy:
            line, = self.ax.plot( t+t0, data, *args, **kwargs )
            self.ax.set_yscale('log')
        else:
            if fill:
                line = self.ax.fill_between( t+t0, data, y2=voffset, *args, **kwargs )
            else:
                line, = self.ax.plot( t+t0, data, *args, **kwargs )
        self.ax.set_xlabel( 'Time (ns)' )
        self.ax.set_ylabel( 'Intensity (arb. units)' )
        pylab.show()
        return line
        
    def readasciiheader( self, verbose=False ):
        """ read this first. """
        ##################################################################################
        #
        # ASCII file header
        #
        ##################################################################################

        self.Ident = self.fobj.read(16).split('\x00')[0]
        if verbose:
            print self.Ident

        self.FormatVersion = "".join( self.fobj.read(6).split(" ") ).split('\x00')[0] # the join/split deblanks the string
        if verbose:
            print "PHD file format version:", self.FormatVersion

        if self.FormatVersion != '2.0':
            raise TypeError("PicoQuantUtils.py is only able to load phd file version 2.0. Quitting.")

        self.CreatorName = self.fobj.read(18).split('\x00')[0]
        if verbose:
            print "File created by:", self.CreatorName

        self.CreatorVersion = self.fobj.read(12).split('\x00')[0]
        if verbose:
            print "Program version:", self.CreatorVersion

        self.fobjTime = self.fobj.read(18).split('\x00')[0]
        if verbose:
            print "Time of creation:", self.fobjTime

        self.CRLF = self.fobj.read(2)
        if verbose:
            print self.CRLF

        self.Comment = self.fobj.read(256)
        if verbose:
            print "Comment:", self.Comment




    def readbinaryheader( self, verbose=False ):
        """ read this after the ascii header. """

        ##################################################################################
        #
        # Binary file header
        #
        ##################################################################################
        """
            I use the struct module to unpack the binary SPE data.
            Some useful formats for struct.unpack_from() include:
            fmt   c type          python
            c     char            string of length 1
            s     char[]          string (Ns is a string N characters long)
            h     short           integer 
            H     unsigned short  integer
            l     long            integer
            f     float           float
            d     double          float
            
            precede these with '=' to force usage of standard python sizes,
            not native sizes (to make usage the same on 32 and 64-bit systems)
        """
        
        binheader = self.fobj.read( 208 ) # should take up 208 bytes in memory...

        self.NumberOfCurves = struct.unpack_from( "=l", binheader, offset=0 )[0]
        if verbose: 
            print "Number of curves:", self.NumberOfCurves
        
        self.BitsPerHistogramBin = struct.unpack_from( "=l", binheader, offset=4 )[0]
        if verbose: 
            print "Bits per histogram bin:", self.BitsPerHistogramBin
        
        self.RoutingChannels = struct.unpack_from( "=l", binheader, offset=8 )[0]
        if verbose: 

            print "Number of routing channels:", self.RoutingChannels
        
        self.NumberOfBoards = struct.unpack_from( "=l", binheader, offset=12 )[0]
        if verbose: 
            print "Number of boards:", self.NumberOfBoards
        
        self.ActiveCurve = struct.unpack_from( "=l", binheader, offset=16 )[0]
        if verbose: 
            print "Active curve:", self.ActiveCurve
        
        self.MeasurementMode = struct.unpack_from( "=l", binheader, offset=20 )[0]
        if verbose: 
            print "Measurement mode:", self.MeasurementMode
        
        self.SubMode = struct.unpack_from( "=l", binheader, offset=24 )[0]
        if verbose: 
            print "Sub mode:", self.SubMode
        
        self.RangeNo = struct.unpack_from( "=l", binheader, offset=28 )[0]
        if verbose: 
            print "Range number:", self.RangeNo
        
        self.Offset = struct.unpack_from( "=l", binheader, offset=32 )[0]
        if verbose: 
            print "Offset:", self.Offset
        
        self.Tacq = struct.unpack_from( "=l", binheader, offset=36 )[0]
        if verbose: 
            print "Acquisition time (ms):", self.Tacq
        
        self.StopAt = struct.unpack_from( "=l", binheader, offset=40 )[0]
        if verbose: 
            print "Stop at (counts):", self.StopAt
        
        self.StopOnOverflow = struct.unpack_from( "=l", binheader, offset=44 )[0]
        if verbose: 
            print "Stop on overflow:", self.StopOnOverflow
        
        self.Restart = struct.unpack_from( "=l", binheader, offset=48 )[0]
        if verbose: 
            print "Restart:", self.Restart
        
        self.DispLinLog = struct.unpack_from( "=l", binheader, offset=52 )[0]
        if verbose: 
            print "Display lin/log:", self.DispLinLog
        
        self.DispTimeAxisFrom = struct.unpack_from( "=l", binheader, offset=56 )[0]
        if verbose: 
            print "Time axis from (ns):", self.DispTimeAxisFrom
        
        self.DispTimeAxisTo = struct.unpack_from( "=l", binheader, offset=60 )[0]
        if verbose: 
            print "Time axis to (ns):", self.DispTimeAxisTo
        
        self.DispCountAxisFrom = struct.unpack_from( "=l", binheader, offset=64 )[0]
        if verbose: 
            print "Count Axis From:", self.DispCountAxisFrom
        
        offset = 68
        self.DispCountAxisTo = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Count Axis To:", self.DispCountAxisTo
        
        self.DispCurveMapTo = []
        self.DispCurveShow = []    
        for i in range(8):
            offset += 4
            self.DispCurveMapTo.append( struct.unpack_from( "=l", binheader, offset=offset )[0] )
            offset += 4
            self.DispCurveShow.append( struct.unpack_from( "=l", binheader, offset=offset+4 )[0] )

        self.ParamStart = []
        self.ParamStep = []
        self.ParamEnd = []    
        for i in range(3):
            offset += 4
            self.ParamStart.append( struct.unpack_from( "=f", binheader, offset=offset )[0] )

            offset += 4
            self.ParamStep.append( struct.unpack_from( "=f", binheader, offset=offset )[0] )

            offset += 4
            self.ParamEnd.append( struct.unpack_from( "=f", binheader, offset=offset )[0] )
            
        offset += 4
        self.RepeatMode = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Repeat Mode:", self.RepeatMode
        
        offset += 4
        self.RepeatsPerCurve = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Repeat / Curve:", self.RepeatsPerCurve
        
        offset += 4
        self.RepeatTime = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Repeat Time:", self.RepeatTime
        
        offset += 4
        self.RepeatWaitTime = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Repeat Wait Time:", self.RepeatWaitTime
        
        offset += 4
        self.ScriptName = struct.unpack_from( "=l", binheader, offset=offset )[0]
        if verbose: 
            print "Script Name:", self.ScriptName
    
    



    def readboardheader( self, verbose=False ):
        """ read this after the ascii header and the binary header. """

        ##################################################################################
        #
        #          Header for each board
        #
        ##################################################################################

        boardheader = self.fobj.read( 156 )
        # I don't actually do anything with this at this point. Just get it out of the way...


        """
        for i = 1:NumberOfBoards
        fprintf(1,'-------------------------------------\n') 
        fprintf(1,'            Board No: #d\n', i-1)

        HardwareIdent(:,i) = char(fread(fid, 16, 'char'))
        fprintf(1,' Hardware Identifier: #s\n', HardwareIdent(:,i))

        HardwareVersion(:,i) = char(fread(fid, 8, 'char'))
        fprintf(1,'    Hardware Version: #s\n', HardwareVersion(:,i))    
            
        HardwareSerial(i) = fread(fid, 1, 'int32')
        fprintf(1,'    HW Serial Number: #d\n', HardwareSerial(i))

        SyncDivider(i) = fread(fid, 1, 'int32')
        fprintf(1,'        Sync divider: #d \n', SyncDivider(i))
         
        CFDZeroCross0(i) = fread(fid, 1, 'int32')
        fprintf(1,'     CFD 0 ZeroCross: #3i mV\n', CFDZeroCross0(i))

        CFDLevel0(i) = fread(fid, 1, 'int32')
        fprintf(1,'     CFD 0 Discr.   : #3i mV\n', CFDLevel0(i))

        CFDZeroCross1(i) = fread(fid, 1, 'int32')
        fprintf(1,'     CFD 1 ZeroCross: #3i mV\n', CFDZeroCross1(i))

        CFDLevel1(i) = fread(fid, 1, 'int32')
        fprintf(1,'     CFD 1 Discr.   : #3i mV\n', CFDLevel1(i))

        Resolution(i) = fread(fid, 1, 'float')
        fprintf(1,'          Resolution: #2.6g ns\n', Resolution(i))

        # below is new in format version 2.0

        RouterModelCode(i)      = fread(fid, 1, 'int32')
        RouterEnabled(i)        = fread(fid, 1, 'int32')

        # Router Ch1
        RtChan1_InputType(i)    = fread(fid, 1, 'int32')
        RtChan1_InputLevel(i)   = fread(fid, 1, 'int32')
        RtChan1_InputEdge(i)    = fread(fid, 1, 'int32')
        RtChan1_CFDPresent(i)   = fread(fid, 1, 'int32')
        RtChan1_CFDLevel(i)     = fread(fid, 1, 'int32')
        RtChan1_CFDZeroCross(i) = fread(fid, 1, 'int32')
        # Router Ch2
        RtChan2_InputType(i)    = fread(fid, 1, 'int32')
        RtChan2_InputLevel(i)   = fread(fid, 1, 'int32')
        RtChan2_InputEdge(i)    = fread(fid, 1, 'int32')
        RtChan2_CFDPresent(i)   = fread(fid, 1, 'int32')
        RtChan2_CFDLevel(i)     = fread(fid, 1, 'int32')
        RtChan2_CFDZeroCross(i) = fread(fid, 1, 'int32')
        # Router Ch3
        RtChan3_InputType(i)    = fread(fid, 1, 'int32')
        RtChan3_InputLevel(i)   = fread(fid, 1, 'int32')
        RtChan3_InputEdge(i)    = fread(fid, 1, 'int32')
        RtChan3_CFDPresent(i)   = fread(fid, 1, 'int32')
        RtChan3_CFDLevel(i)     = fread(fid, 1, 'int32')
        RtChan3_CFDZeroCross(i) = fread(fid, 1, 'int32')
        # Router Ch4
        RtChan4_InputType(i)    = fread(fid, 1, 'int32')
        RtChan4_InputLevel(i)   = fread(fid, 1, 'int32')
        RtChan4_InputEdge(i)    = fread(fid, 1, 'int32')
        RtChan4_CFDPresent(i)   = fread(fid, 1, 'int32')
        RtChan4_CFDLevel(i)     = fread(fid, 1, 'int32')
        RtChan4_CFDZeroCross(i) = fread(fid, 1, 'int32')

        # Router settings are meaningful only for an existing router:

        if RouterModelCode(i)>0


            fprintf(1,'-------------------------------------\n') 
            fprintf(1,'   Router Model Code: #d \n', RouterModelCode(i))
            fprintf(1,'      Router Enabled: #d \n', RouterEnabled(i))
            fprintf(1,'-------------------------------------\n') 
            
            # Router Ch1 
            fprintf(1,'RtChan1 InputType   : #d \n', RtChan1_InputType(i))
            fprintf(1,'RtChan1 InputLevel  : #4i mV\n', RtChan1_InputLevel(i))
            fprintf(1,'RtChan1 InputEdge   : #d \n', RtChan1_InputEdge(i))
            fprintf(1,'RtChan1 CFDPresent  : #d \n', RtChan1_CFDPresent(i))
            fprintf(1,'RtChan1 CFDLevel    : #4i mV\n', RtChan1_CFDLevel(i))
            fprintf(1,'RtChan1 CFDZeroCross: #4i mV\n', RtChan1_CFDZeroCross(i))
            fprintf(1,'-------------------------------------\n') 

            # Router Ch2
            fprintf(1,'RtChan2 InputType   : #d \n', RtChan2_InputType(i))
            fprintf(1,'RtChan2 InputLevel  : #4i mV\n', RtChan2_InputLevel(i))
            fprintf(1,'RtChan2 InputEdge   : #d \n', RtChan2_InputEdge(i))
            fprintf(1,'RtChan2 CFDPresent  : #d \n', RtChan2_CFDPresent(i))
            fprintf(1,'RtChan2 CFDLevel    : #4i mV\n', RtChan2_CFDLevel(i))
            fprintf(1,'RtChan2 CFDZeroCross: #4i mV\n', RtChan2_CFDZeroCross(i))
            fprintf(1,'-------------------------------------\n') 

            # Router Ch3
            fprintf(1,'RtChan3 InputType   : #d \n', RtChan3_InputType(i))
            fprintf(1,'RtChan3 InputLevel  : #4i mV\n', RtChan3_InputLevel(i))
            fprintf(1,'RtChan3 InputEdge   : #d \n', RtChan3_InputEdge(i))
            fprintf(1,'RtChan3 CFDPresent  : #d \n', RtChan3_CFDPresent(i))
            fprintf(1,'RtChan3 CFDLevel    : #4i mV\n', RtChan3_CFDLevel(i))
            fprintf(1,'RtChan3 CFDZeroCross: #4i mV\n', RtChan3_CFDZeroCross(i))
            fprintf(1,'-------------------------------------\n') 

            # Router Ch4
            fprintf(1,'RtChan4 InputType   : #d \n', RtChan4_InputType(i))
            fprintf(1,'RtChan4 InputLevel  : #4i mV\n', RtChan4_InputLevel(i))
            fprintf(1,'RtChan4 InputEdge   : #d \n', RtChan4_InputEdge(i))
            fprintf(1,'RtChan4 CFDPresent  : #d \n', RtChan4_CFDPresent(i))
            fprintf(1,'RtChan4 CFDLevel    : #4i mV\n', RtChan4_CFDLevel(i))
            fprintf(1,'RtChan4 CFDZeroCross: #4i mV\n', RtChan4_CFDZeroCross(i))
            fprintf(1,'-------------------------------------\n') 
         
        end
        end
    """



    def readcurveheaders( self, verbose=False ):
        """ read this after the ascii header, the binary header, and the boards header. """

        ##################################################################################
        #
        #                Headers for each histogram (curve)
        #
        ##################################################################################

        MAXCURVES = 512
        binheader = self.fobj.read( 150*MAXCURVES )

        offset = 0
        self.curveheaders = []

        for i in range( self.NumberOfCurves ):
            ch = dict()
            
            ch['CurveIndex'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose:
                print "Curve index:", ch['CurveIndex']
            offset += 4
                    
            ch['TimeOfRecording'] = struct.unpack_from( "=l", binheader, offset=offset )[0] # supposed to be unsigned long...
            if verbose: 
                print "Repeat Wait Time:", ch['TimeOfRecording']
            #  The PicoHarp software saves the time of recording
            #  in a 32 bit serial time value as defined in all C libraries.
            #  This equals the number of seconds elapsed since midnight
            #  (00:00:00), January 1, 1970, coordinated universal time.
            #  The conversion to normal date and time strings is tricky...
            #  In matlab: (but we need it to be a uint32, which it's not, so I won't implement the conversion here)
            #  TimeOfRecording(i) = TimeOfRecording(i)/24/60/60+25569+693960
            #  fprintf(1,'  Time of Recording: #s \n', datestr(TimeOfRecording(i),'dd-mmm-yyyy HH:MM:SS'))
            offset += 4

            ch['HardwareIdent'] = struct.unpack_from( "=16s", binheader, offset=offset )[0]
            if verbose: 
                print "Repeat Wait Time:", ch['HardwareIdent']
            offset += 16
        
            ch['HardwareVersion'] = struct.unpack_from( "=8s", binheader, offset=offset )[0]
            if verbose: 
                print "Hardware Version:", ch['HardwareVersion']
            offset += 8
        
            ch['HardwareSerial'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "HW Serial Number:", ch['HardwareSerial']
            offset += 4
        
            ch['SyncDivider'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Sync divider:", ch['SyncDivider']
            offset += 4
        
            ch['CFDZeroCross0'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "CFD 0 ZeroCross (mV):", ch['CFDZeroCross0']
            offset += 4
        
            ch['CFDLevel0'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "CFD 0 Discr. (mV):", ch['CFDLevel0']
            offset += 4
        
            ch['CFDZeroCross1'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "CFD 1 ZeroCross (mV):", ch['CFDZeroCross1']
            offset += 4
        
            ch['CFDLevel1'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "CFD 1 Discr. (mV):", ch['CFDLevel1']
            offset += 4
        
            ch['Offset'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Offset:", ch['Offset']
            offset += 4
        
            ch['RoutingChannel'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Routing Channel:", ch['RoutingChannel']
            offset += 4
        
            ch['ExtDevices'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "External Devices:", ch['ExtDevices']
            offset += 4
        
            ch['MeasMode'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Measure mode:", ch['MeasMode']
            offset += 4
        
            ch['SubMode'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Sub-Mode:", ch['SubMode']
            offset += 4
        
            ch['P1'] = struct.unpack_from( "=f", binheader, offset=offset )[0]
            if verbose: 
                print "P1:", ch['P1']
            offset += 4
        
            ch['P2'] = struct.unpack_from( "=f", binheader, offset=offset )[0]
            if verbose: 
                print "P2:", ch['P2']
            offset += 4
        
            ch['P3'] = struct.unpack_from( "=f", binheader, offset=offset )[0]
            if verbose: 
                print "P3:", ch['P3']
            offset += 4
        
            ch['RangeNo'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Range No.:", ch['RangeNo']
            offset += 4
        
            ch['Resolution'] = struct.unpack_from( "=f", binheader, offset=offset )[0]
            if verbose: 
                print "Resolution (ns):", ch['Resolution']
            offset += 4
        
            ch['Channels'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Channels:", ch['Channels']
            offset += 4
        
            ch['Tacq'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Acquisition Time (ms):", ch['Tacq']
            offset += 4
        
            ch['StopAfter'] = struct.unpack_from( "=l", binheader, offset=offset )[0] 
            if verbose: 
                print "Stop After (ms):", ch['StopAfter']
            offset += 4
        
            ch['StopReason'] = struct.unpack_from( "=l", binheader, offset=offset )[0] 
            if verbose: 
                print "Stop Reason (ms):", ch['StopReason']
            offset += 4
        
            ch['InpRate0'] = struct.unpack_from( "=l", binheader, offset=offset )[0] 
            if verbose: 
                print "Input Rate 0 (Hz):", ch['InpRate0']
            offset += 4
        
            ch['InpRate1'] = struct.unpack_from( "=l", binheader, offset=offset )[0] 
            if verbose: 
                print "Input Rate 1 (Hz):", ch['InpRate1']
            offset += 4
        
            ch['HistCountRate'] = struct.unpack_from( "=l", binheader, offset=offset )[0] 
            if verbose: 
                print "Hist. Count Rate (cps):", ch['HistCountRate']
            offset += 4
        
            ch['IntegralCount'] = struct.unpack_from( "=2l", binheader, offset=offset )[0] 
            if verbose: 
                print "Integral Count:", ch['IntegralCount']
            offset += 8
        
            ch['Reserved'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Reserved:", ch['Reserved']
            offset += 4
        
            ch['DataOffset'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            if verbose: 
                print "Data Offset relative to the start of the file:", ch['DataOffset']
            offset += 4
        
            # below is new in format version 2.0

            ch['RouterModelCode'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RouterEnabled'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_InputType'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_InputLevel'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_InputEdge'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_CFDPresent'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_CFDLevel'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
            ch['RtChan_CFDZeroCross'] = struct.unpack_from( "=l", binheader, offset=offset )[0]
            offset += 4
        
            self.curveheaders.append( ch )
            

    def readhistograms( self ):

        ##################################################################################
        #
        #          Reads all histograms into a list of numpy arrays
        #
        ##################################################################################

        self.fobj.seek(0) # go back to beginning because 'DataOffset' is measured from there.
        binarydata = self.fobj.read()
        
        self.curves = []
        
        for i,curve in enumerate( self.curveheaders ):
            
            # This will typically be waaay too long and will be padded with zeros because it
            # can accomodate up to 2**16 histogram bins but our laser rep rate is ~76MHz, so
            # if you were set at 4ps resolution, that would only require 1/76MHz/4ps ~ 3281 bins
            #
            # It's worth noting that when we wrap the curve (move data from before laser to after),
            # there is going to be some small error in the timing because the number of bins will
            # not be an exact integer. This error will be at most the resolution, which is likely
            # to be either really small compared to the lifetime of the emitter or, if the lifetime
            # is really short, the fluorescence will have decayed before the end of the un-wrapped
            # curve. The only time this could be an issue is if the lifetime is really short and
            # the peak in lifetime occurrs at the very end of the un-wrapped curve. Then you should
            # insert enough BNC cable to bring the peak back toward the front of the un-wrapped curve.

            zeropadded = pylab.np.array(
                struct.unpack_from( "="+str(curve['Channels'])+"l", binarydata, offset=curve['DataOffset'] ),
                dtype=pylab.np.int
                         )
            nbins = 1.0/self.curveheaders[0]['InpRate0']/self.curveheaders[0]['Resolution']/1.0e-9
            nfullbins = pylab.floor( nbins )
            npartialbins = pylab.mod( nbins, 1 )
            if npartialbins > 0.0:
                # I think in this case (which is almost always the case), the first bin is sometimes
                # the 'partial' bin, and the last bin is sometimes the 'partial' bin. So we'll delete them.
                # (or uncomment other line to add them.)
                ###zeropadded[0] += zeropadded[ nfullbins ] # add the partial bin to the first bin
                self.curves.append( zeropadded[1:nfullbins] ) 
            else:
                self.curves.append( zeropadded[:nfullbins] ) 
        
        self.raw_curves = self.curves[:]

    def set_axes( self, axes ):
        """ this allows you to plot the data to a particular axes
        """
        self.ax = axes

    def zero_except( self, tstart=None, tend=None):
        """ blank curve[0] of a trace except within the given window.
            Useful for removing background and reflections from IRF.
        """
        self.curves[0][pylab.find(self.t[0]<tstart)] = 0.0
        self.curves[0][pylab.find(self.t[0]>tend)] = 0.0

    def set_irf( self, irf=None, wraptime=None, dispersion=None ):
        """
        The detector response isn't a delta-function, meaning that what
        you measure isn't the true time-dependence of the system you are
        measuring. It's the time dependence of the system convolved with
        the response of the detector. This method sets the measured
        trace of the detector response that will be used to convolve
        the mult-exponential model before fitting (thereby taking this
        convolution into account without doing nearly-impossible
        numerical deconvolution).
        """
        if isinstance( irf, Trace ):
            self.irf = irf
        elif type(irf) == str:
            self.irf = Trace( irf )
            if wraptime is not None:
                self.irf.wrapcurves( wraptime )
            elif self.wraptime is not None:
                self.irf.wrapcurves( self.wraptime )
        
        self.irf_dispersion = dispersion
        if dispersion is not None and dispersion != 0:
            # this is meant to address chromatic dispersion within the setup
            # (e.g. optical fiber)
            # don't bother with normalization b/c it gets normalized to unit area below anyway.
            #original = self.irf.curves[0].copy()
            #self.irf.curves[0][dispersion:] += original[:-dispersion]
            #self.irf.curves[0][:-dispersion] += original[dispersion:]
            len1 = len(self.irf.curves[0])
            chain_of_three = pylab.zeros( 3*len1 ) # stack three curves end-to-end so cspline1d_eval doesn't have to extrapolate beyond data
            chain_of_three[:len1] = self.irf.curves[0][:]
            chain_of_three[len1:2*len1] = self.irf.curves[0][:]
            chain_of_three[-len1:] = self.irf.curves[0][:]
            g = cspline1d(chain_of_three)
            smoothed = pylab.zeros( len1 )
            std_dev = dispersion/1000.0
            for t0 in pylab.linspace(-2*std_dev, 2*std_dev, 50):
                weight = pylab.exp( -t0**2/2.0/std_dev**2 )
                smoothed += weight * cspline1d_eval( g, self.irf.t[0]-t0, dx=self.irf.t[0][1], x0=-self.irf.t[0][-1] )
            self.irf.curves[0] = smoothed
            
        normalized = self.irf.curves[0].astype(np.float)/float(sum(self.irf.curves[0])) # normalize integral to 1, just like delta-function!!!
        self.irf.curves[0] = normalized.copy()

        self.irf_generator = cspline1d(self.irf.curves[0])
        self.irf_dt = self.irf.t[0][1]-self.irf.t[0][0]
        self.irf_t0 = self.irf.t[0][0]
        
        if False:
            """not sure this matters if we do interpolation
            """
            # difference in degree of binning (e.g. 8ps vs. 4ps is bin difference of 2)
            bin_difference = pylab.np.int( self.resolution / self.irf.resolution )
            if bin_difference != 1:
                raise ValueError("Have not yet tested deconvolution with different resolution than detector trace!!!")
                d = self.irf.curves[0]
                detector_binned = pylab.zeros( len(d)/bin_difference )
                for i in range( len(detector_binned ) ):
                    detector_binned[i] = sum( d[i*bin_difference : i*bin_difference+bin_difference] )
            

    def wrapcurves( self, time, delete_firstpoints=0, delete_lastpoints=0, use_raw=False ):
        """ Odds are, your pulse doesn't start at time 0ns.
            Instead, if your lifetime is comparable to your pulse
            spacing, your data wraps around and at 0ns you're
            actually near the end of the decay tail. This method
            is designed to take the data from before the pulse and
            move it where it should be: at the end.
            Usage:
            self.wrap( time, delete_points=None )
            where time is the threshold: all data earlier than this
            get moved to the end of the scan.
            
            This does all curves at once (though all my data sets
            seem to only have curve [0] anyway).
            
            The optional arguments `delete_firstpoints` and
            `delete_lastpoints` is for when the
            first and/or last couple bins have an abnormally low
            number of counts. I think this happens when the time
            resolution of the curve is not at the detector minimum,
            meaning that some binning takes place. If the curve window
            isn't evenly divisible by the bin size, then the first and
            last bins can end up with fewer points. For some reason,
            I've also seen a couple traces where this happened for the
            last two bins, which I don't really understand. Regardless,
            let's just delete the points in question (after assigning the
            rest of the points the proper time delay).
            usage:
            delete_firstpoints=n deletes the first n points of unwrapped trace
            delete_lastpoints=n deletes the last n points of unwrapped trace
            
            use_raw=False means it will just wrap the data stored in self.curves.
            If you want to ensure that you're using the raw data (for example,
            to enable easy re-wrapping in the HuPlot program), then pass
            use_raw=True
        """
        self.wraptime = time
        if self.irf is not None: self.irf.wrapcurves( self.wraptime )
            
        if use_raw:
            curves = self.raw_curves[:]
        else:
            curves = self.curves[:]

        for i, curve in enumerate( curves ):
            time_per_channel = self.curveheaders[i]['Resolution'] # this is in ns
            points_before_threshold = pylab.find( time_per_channel*pylab.arange(len(curve))<time )
            if len( points_before_threshold ) == 0: 
                self.curves = curves[:]
                self.t = self.raw_t[:]
                return True
            
            threshold = points_before_threshold[-1]
            wrapped = pylab.zeros(len(curve))
            wrapped[-threshold:] = curve[:threshold]
            wrapped[:-threshold] = curve[threshold:]
            self.curves[i] = wrapped
            if delete_firstpoints > 0 or delete_lastpoints > 0:
                shortened_curve = pylab.zeros(len(curve) - delete_firstpoints - delete_lastpoints)
                shortened_t = pylab.zeros(len(curve) - delete_firstpoints - delete_lastpoints)

                shortened_curve[:-threshold+delete_firstpoints] = self.curves[i][:-threshold-delete_lastpoints]
                shortened_curve[-threshold+delete_firstpoints:] = self.curves[i][-threshold+delete_firstpoints:]
                self.curves[i] = shortened_curve
                
                shortened_t[:-threshold+delete_firstpoints] = self.raw_t[i][:-threshold-delete_lastpoints]
                shortened_t[-threshold+delete_firstpoints:] = self.raw_t[i][-threshold+delete_firstpoints:]
                self.t[i] = shortened_t

            

if __name__ == '__main__':
    # example usage:
    d = datafile( 'examplefile.phd' ) # doesn't actually exist in this directory...
    d.wrapcurves( 1.17 )
    d.normalize_curves()
    d.plot()

