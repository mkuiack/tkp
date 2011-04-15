#
# LOFAR Transients Key Project
#
# Gaussian fitting routines
#

import math, logging
import numpy, scipy, scipy.optimize

import tkp.settings as settings
from tkp.utility.uncertain import Uncertain

def gaussian(height, centre_x, centre_y, semimajor, semiminor, theta):
    """Return a Gaussian function with the given parameters. Theta is the
    angle between the semi-major & y axes measured in radians, measured counterclockwise."""
    return lambda x, y: height*numpy.exp(-math.log(2.)*(((math.cos(theta)*(x-centre_x)+math.sin(theta)*(y-centre_y))/semiminor)**2.+((math.cos(theta)*(y-centre_y)-math.sin(theta)*(x-centre_x))/semimajor)**2.))

def moments(dat, beam, threshold=0):
    """Use the first moment of the distribution is the barycentre of an
    ellipse. The second moments are used to estimate the rotation angle
    and the length of the axes.

    input: numpy array of pixel values, threshold
    reutrns: dict(peak, total, xbar, ybar, semimajor, semiminor, theta).
    ** NB DO NOT CHANGE ARGUMENTS / RETURN VALUES **"""

    # Are we fitting a -ve or +ve Gaussian?
    if dat.mean() >= 0:
        # The peak is always underestimated when you take the highest pixel.
        peak = dat.max()*settings.fudge_max_pix(*beam)
    else:
        peak = dat.min()
    ratio = threshold/peak
    total = dat.sum()
    X, Y = numpy.indices(dat.shape)
    xbar = float((X*dat).sum()/total)
    ybar = float((Y*dat).sum()/total)
    xxbar = (X*X*dat).sum()/total - xbar**2
    yybar = (Y*Y*dat).sum()/total - ybar**2
    xybar = (X*Y*dat).sum()/total - xbar*ybar

    working1 = (xxbar + yybar) / 2.0
    working2 = math.sqrt(((xxbar - yybar)/2)**2 + xybar**2)

    beamsize = settings.calculate_beamsize(beam[0],beam[1])

    # Some problems arise with the sqrt of (working1-working2) when they are
    # equal, this happens with islands that have a thickness of only one pixel
    # in at least one dimension.  Due to rounding errors this difference
    # becomes negative--->math domain error in sqrt.
    if len(dat.nonzero()[0]) == 1:
        # This is the case when the island (or more likely subisland) has
        # a size of only one pixel.
        semiminor = numpy.sqrt(beamsize/numpy.pi)
        semimajor = numpy.sqrt(beamsize/numpy.pi)
    else:
        semimajor_tmp = (working1 + working2)*2.*math.log(2.)
        semiminor_tmp = (working1 - working2)*2.*math.log(2.)
        # ratio will be 0 for data that hasn't been selected according to a
        # threshold.
        if ratio != 0:
            # The corrections below for the semi-major and semi-minor axes are
            # to compensate for the underestimate of these quantities due to the
            # cutoff at the threshold.
            semimajor_tmp /= (1.0+math.log(ratio)*ratio/(1.0-ratio))
            semiminor_tmp /= (1.0+math.log(ratio)*ratio/(1.0-ratio))
        semimajor = math.sqrt(semimajor_tmp)
        semiminor = math.sqrt(semiminor_tmp)
        if semiminor == 0:
            # A semi-minor axis exactly zero gives all kinds of problems.
            # For instance wrt conversion to celestial coordinates.
            # This is a quick fix.
            semiminor = beamsize/(numpy.pi*semimajor)

    # This shouldn't happen, but..
    if (
        numpy.isnan(xbar) or numpy.isnan(ybar) or
        numpy.isnan(semimajor) or numpy.isnan(semiminor)
    ):
        raise ValueError("Unable to estimate Gauss shape")

    # Not sure if theta is affected in any way by the cutoff at the threshold.

    if abs(semimajor - semiminor) < 0.01:
        # short circuit!
        theta = 0.
    else:
        theta = math.atan(2. * xybar / (xxbar - yybar))/2.
        if theta * xybar > 0.:
            if theta < 0.:
                theta += math.pi / 2.0
            else:
                theta -= math.pi / 2.0

    ## NB: a dict should give us a bit more flexibility about arguments;
    ## however, all those here are ***REQUIRED***.
    return {"peak": peak, "flux": total, "xbar": xbar, "ybar": ybar,
        "semimajor": semimajor, "semiminor":  semiminor, "theta": theta}

def fitgaussian(data, params, fixed={}, maxfev=0):
    """
    Perform a least squares fit to an elliptical Gaussian. Uses the
    moments() method to generate an initial estimate of the solution. Based on
    code from SciPy cookbook, but modified to take account of rotation of
    ellipse relative to axes.

    If a dict called fixed is passed in, then parameters specified within the
    dict with the same names as fit_params (below) will be "locked" in the
    fitting process.

    input: numpy array of pixel values, initial parameters for fit (a dict, as
    generated by moments(), above.
    output: max value, barycentre pixel x, y, length of semimajor & minor
    axes, angle between x axis and semi-major axis in radians. In a dict, as
    above.
    """
    fit_params = ('peak', 'xbar', 'ybar', 'semimajor', 'semiminor', 'theta')
    # Collect necessary values from parameter dict; only those which aren't
    # fixed.
    my_pars = []
    for param in fit_params:
        if not fixed.has_key(param):
            if isinstance(params[param], Uncertain):
                my_pars.append(params[param].value)
            else:
                my_pars.append(params[param])

    def errorfunction(paramlist, fixed):
        # Takes two arguments: the current fit parameters (paramlist) and a
        # list of all the parameters which are fixed for this fit. Combines
        # the two to build the arguments to gaussian().
        paramlist = list(paramlist)
        gaussian_args = []
        for param in fit_params:
            if fixed.has_key(param):
                gaussian_args.append(fixed[param])
            else:
                gaussian_args.append(paramlist.pop(0))
        return (
            gaussian(*gaussian_args)(*numpy.indices(data.shape)) - data
        ).compressed()

    # The .compressed() below is essential so the Gaussian fit will not take
    # account of the masked values (=below threshold) at the edges and corners
    # of data (=(masked) array, so rectangular in shape).
    solution, icov_x, infodict, mesg, success = scipy.optimize.leastsq(
        errorfunction, my_pars, fixed, full_output=True, maxfev=maxfev
    )
    # solution contains only the variable parameters; we need to merge the
    # contents of fixed into the solution list.
    tmp_solution = list(solution)
    solution = []
    for param in fit_params:
        if fixed.has_key(param):
            solution.append(fixed[param])
        else:
            solution.append(tmp_solution.pop(0))

    if success in [5, 6, 7, 8]:
        raise ValueError("leastsq returned %d (%s)" % (success, mesg))

    # Negative semi-major and semi-minor axis are just as good a
    # solution as positive ones from the least squares Gaussian
    # fitting, since both of them appear as a square in def gaussian.
    # Of couse, we only want the positive ones.  In this case it is
    # safer to stick with moments, because the peak from Gauss fitting
    # is likely ot be outside the island.
    semimajor, semiminor = round(solution[3], 5), round(solution[4], 5)
    if semimajor < 0 or semiminor < 0 or semiminor > semimajor:
        # Bail out; let outside routine catch error and decide
        # how to proceed (eg, use moments)
        raise ValueError("incorrect axis from fitgauss; using moments")
    else:
        theta = solution[5]
        if theta > numpy.pi / 2:
            theta -= numpy.pi
        elif theta < -numpy.pi / 2:
            theta += numpy.pi

    return {
        "peak": solution[0], "xbar": solution[1], "ybar": solution[2],
        "semimajor": solution[3], "semiminor": solution[4], "theta": solution[5]
    }
