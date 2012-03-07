#
# LOFAR Transients Key Project
#

# Python standard library
import logging
import os
# Other external libraries
from matplotlib import pylab
from datetime import *
import time as tm
# Local tkp_lib functionality
import monetdb.sql as db

def rms_distance_from_fieldcentre(conn, dsid, logscale=False):
    """
    Plot the rms of extracted sources in given dataset vs their 
    distance from the field centre.
    """
    try:
        cursor = conn.cursor()
        query = """\
        SELECT x1.image_id
              ,x1.xtrsrcid as xtrsrcid1
              ,DEGREES(2 * ASIN(SQRT( (x1.x - im1.x) * (x1.x - im1.x) 
                                    + (x1.y - im1.y) * (x1.y - im1.y) 
                                    + (x1.z - im1.z) * (x1.z - im1.z)
                                    ) / 2)) AS centr_img_dist_deg
              ,20000 * x1.i_peak / x1.det_sigma as rms_mJy
          FROM extractedsources x1
              ,images im1
         WHERE x1.image_id = im1.imageid
           AND ds_id = %s
        ORDER BY centr_img_dist_deg
        """
        cursor.execute(query, (dsid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            imageid = results[0]
            xtrsrcid = results[1]
            dist_deg = results[2]
            rms = results[3]
        
        plotfiles=[]
        p = 0
        fig = pylab.figure()
        ax = fig.add_subplot(111)
        ax.scatter(dist_deg, rms, c='r', s=20, edgecolor='r')
        ax.set_xlabel(r'Distance from Pointing Centre (deg)', size='x-large')
        ax.set_ylabel(r'rms (mJy/beam)', size='x-large')
        #ax.set_xlim(xmin=0)
        #ax.set_ylim(ymin=0)
        if logscale:
            ax.set_yscale("log", nonposy='clip')
        
        pylab.grid(True)
        
        fname = 'rms_dist_pc_dsid_' + str(dsid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)
        #print plotfiles[-1]
        
        return plotfiles
    except db.Error, e:
        logging.warn("Query rms vs dist pc for dsid %s failed: %s" % (str(dsid),query))
        raise

def hist_sources_per_image(conn, dsid):
    """
    Bar plot of the number of extracted sources per image in a given 
    dataset.
    Plotted are the image_ids (x-axis) and the number of sources (y-axis).
    Every bar displays the number of sources and the timestamp of the image.
    """
    try:
        cursor = conn.cursor()
        query = """\
        SELECT imageid
              ,taustart_ts
              ,nsources
          FROM images
              ,(SELECT x1.image_id 
                      ,COUNT(*) as nsources
                  FROM extractedsources x1
                      ,images im1
                 WHERE x1.image_id = im1.imageid
                   AND ds_id = %s
                GROUP BY x1.image_id
               ) t1
         WHERE t1.image_id = imageid
        """
        cursor.execute(query, (dsid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            imageid = results[0]
            taustart_ts = results[1]
            nsources = results[2]
        
        d = []
        for i in range(len(taustart_ts)):
            d.append(taustart_ts[i].isoformat(' '))

        plotfiles=[]
        p = 0
        fig = pylab.figure()
        ax = fig.add_subplot(111)
        width=0.8
        ind = pylab.arange(len(imageid))
        rects = ax.bar(ind, nsources, width, color='r')
        ax.set_xlabel(r'Image', size='x-large')
        ax.set_ylabel(r'Number of Sources', size='x-large')
        ax.set_xticks(ind+width/2.)
        ax.set_xticklabels( imageid )
        for i in range(len(ax.get_xticklabels())):
            ax.get_xticklabels()[i].set_size('x-large')
        for i in range(len(ax.get_yticklabels())):
            ax.get_yticklabels()[i].set_size('x-large')

        def autolabel(rects):
            i=0
            for rect in rects:
                height = rect.get_height()
                pylab.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%d'%int(height),
                         rotation='horizontal', ha='center', va='bottom')
                pylab.text(rect.get_x()+rect.get_width()/2., 0.5*height, '%s'%str(d[i]),
                         rotation='vertical', ha='center', va='center')
                i=i+1

        #ax.set_ylim(ymax=100)
        autolabel(rects)
        pylab.grid(True)
        
        fname = 'hist_sources_per_image_dsid_' + str(dsid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)
        #print plotfiles[-1]
        
        return plotfiles
    except db.Error, e:
        logging.warn("Query sources per image for dsid %s failed: %s" % (str(dsid),query))
        raise

def scat_pos_counterparts(conn, xtrsrcid):
    """
    Plot positions of all counterparts for a given source.
    Central in the plot is the position from the running catalog, whereas the positions
    of the associated sources are scattered around the central point.
    Axes are in arcsec relative to the running catalog position.
    """
    try:
        cursor = conn.cursor()
        query = """\
        select x.xtrsrcid
              ,x.ra
              ,x.decl
              /*,3600 * (x.ra * cos(radians(x.decl)) - r.wm_ra * cos(radians(r.wm_decl))) as ra_dist_arcsec*/
              ,3600 * (x.ra - r.wm_ra) as ra_dist_arcsec
              ,3600 * (x.decl - r.wm_decl) as decl_dist_arcsec
              ,x.ra_err/2
              ,x.decl_err/2 
              ,r.wm_ra_err/2
              ,r.wm_decl_err/2
          from assocxtrsources a
              ,extractedsources x 
              ,runningcatalog r
         where a.xtrsrc_id in (select xtrsrc_id 
                                 from assocxtrsources 
                                where assoc_xtrsrc_id = %s
                              ) 
           and a.assoc_xtrsrc_id = x.xtrsrcid
           and a.xtrsrc_id = r.xtrsrc_id

        """
        cursor.execute(query, (xtrsrcid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            xtrsrc_id = results[0]
            ra = results[1]
            decl = results[2]
            ra_dist_arcsec = results[3]
            decl_dist_arcsec = results[4]
            ra_err = results[5]
            decl_err = results[6]
            wm_ra_err = results[7]
            wm_decl_err = results[8]
        
        plotfiles=[]
        p = 0
        fig = pylab.figure(figsize=(8,8))
        ax = fig.add_subplot(111)
        
        ax.errorbar(0, 0, xerr=wm_ra_err[0], yerr=wm_decl_err[0], fmt='o',  color='k', label="rc")
        ax.errorbar(ra_dist_arcsec, decl_dist_arcsec, xerr=ra_err, yerr=decl_err, fmt='+',  color='r', label="xtr")
        ax.set_xlabel(r'RA (arcsec)', size='x-large')
        ax.set_ylabel(r'DEC (arcsec)', size='x-large')
        for i in range(len(ax.get_xticklabels())):
            ax.get_xticklabels()[i].set_size('x-large')
        for i in range(len(ax.get_yticklabels())):
            ax.get_yticklabels()[i].set_size('x-large')

        lim = 1+max(int(pylab.trunc(max(abs(min(ra_dist_arcsec)),abs(max(ra_dist_arcsec))))),int(pylab.trunc(max(abs(min(decl_dist_arcsec)),abs(max(decl_dist_arcsec))))))
        #print "x_int:",x_int,"y_int:",y_int
        ax.set_xlim(xmin=-lim,xmax=lim)
        ax.set_ylim(ymin=-lim,ymax=lim)
        pylab.grid(True)
        
        fname = 'scat_counterparts_xtrsrcid_' + str(xtrsrcid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)
        #print plotfiles[-1]
        
        return plotfiles
    except db.Error, e:
        logging.warn("Query counterparts for xtrsrcid %s failed: %s" % (str(xtrsrcid),query))
        raise

def scat_pos_all_counterparts(conn, dsid):
    """
    Plot positions of all counterparts for all (unique) sources for the given dataset.
    The positions of all (unique) sources in the running catalog are at the centre, 
    whereas the positions of all their associated sources are scattered around the central point.
    Axes are in arcsec relative to the running catalog position.
    """
    try:
        cursor = conn.cursor()
        query = """\
        select x.xtrsrcid
              ,x.ra
              ,x.decl
              /*,3600 * (x.ra * cos(radians(x.decl)) - r.wm_ra * cos(radians(r.wm_decl))) as ra_dist_arcsec*/
              ,3600 * (x.ra - r.wm_ra) as ra_dist_arcsec
              ,3600 * (x.decl - r.wm_decl) as decl_dist_arcsec
              ,x.ra_err/2
              ,x.decl_err/2 
              ,r.wm_ra_err/2
              ,r.wm_decl_err/2
          from assocxtrsources a
              ,extractedsources x 
              ,runningcatalog r
              ,images im1
         where a.xtrsrc_id <> a.assoc_xtrsrc_id
           and a.xtrsrc_id = r.xtrsrc_id
           and a.assoc_xtrsrc_id = x.xtrsrcid
           and x.image_id = im1.imageid
           and im1.ds_id = %s

        """
        cursor.execute(query, (dsid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            xtrsrc_id = results[0]
            ra = results[1]
            decl = results[2]
            ra_dist_arcsec = results[3]
            decl_dist_arcsec = results[4]
            ra_err = results[5]
            decl_err = results[6]
            wm_ra_err = results[7]
            wm_decl_err = results[8]
        
        plotfiles=[]
        p = 0
        fig = pylab.figure(figsize=(8,8))
        ax = fig.add_subplot(111)
        
        #ax.errorbar(0, 0, xerr=wm_ra_err[0], yerr=wm_decl_err[0], fmt='o',  color='k', label="rc")
        ax.errorbar(ra_dist_arcsec, decl_dist_arcsec, xerr=ra_err, yerr=decl_err, fmt='+',  color='r', label="xtr")
        ax.set_xlabel(r'RA (arcsec)', size='x-large')
        ax.set_ylabel(r'DEC (arcsec)', size='x-large')
        for i in range(len(ax.get_xticklabels())):
            ax.get_xticklabels()[i].set_size('x-large')
        for i in range(len(ax.get_yticklabels())):
            ax.get_yticklabels()[i].set_size('x-large')

        lim = 1+max(int(pylab.trunc(max(abs(min(ra_dist_arcsec)),abs(max(ra_dist_arcsec))))),int(pylab.trunc(max(abs(min(decl_dist_arcsec)),abs(max(decl_dist_arcsec))))))
        #print "x_int:",x_int,"y_int:",y_int
        ax.set_xlim(xmin=-lim,xmax=lim)
        ax.set_ylim(ymin=-lim,ymax=lim)
        pylab.grid(True)
        
        fname = 'scat_pos_all_counterparts_dsid_' + str(dsid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)
        #print plotfiles[-1]
        
        return plotfiles
    except db.Error, e:
        logging.warn("Query counterparts for xtrsrcid %s failed: %s" % (str(xtrsrcid),query))
        raise

def hist_all_counterparts_dist(conn, dsid):
    """
    Histogram of the all the distances of the associated sources to their
    running catalog based position.
    Distances are distributed across 10 bins.
    """
    try:
        cursor = conn.cursor()
        query = """\
        SELECT r.xtrsrc_id
              ,a.assoc_xtrsrc_id
              ,3600 * DEGREES(2 * ASIN(SQRT( (r.x - x.x) * (r.x - x.x)
                                           + (r.y - x.y) * (r.y - x.y)
                                           + (r.z - x.z) * (r.z - x.z)
                                           ) / 2)
                             ) AS dist_arcsec
          FROM assocxtrsources a
              ,extractedsources x 
              ,runningcatalog r
              ,images im1
         WHERE a.xtrsrc_id <> a.assoc_xtrsrc_id
           AND a.xtrsrc_id = r.xtrsrc_id
           AND a.assoc_xtrsrc_id = x.xtrsrcid
           AND x.image_id = im1.imageid
           AND im1.ds_id = %s
        """
        cursor.execute(query, (dsid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            xtrsrc_id = results[0]
            assoc_xtrsrc_id = results[1]
            dist_arcsec = results[2]
        
        plotfiles=[]
        p = 0
        fig = pylab.figure()
        ax = fig.add_subplot(111)
        ax.hist(dist_arcsec, 10, color='r')
        ax.set_xlabel(r'Distance from runcat (arcsec)', size='x-large')
        ax.set_ylabel(r'N', size='x-large')
        for i in range(len(ax.get_xticklabels())):
            ax.get_xticklabels()[i].set_size('x-large')
        for i in range(len(ax.get_yticklabels())):
            ax.get_yticklabels()[i].set_size('x-large')

        pylab.grid(True)
        
        fname = 'hist_all_counterparts_dist_dsid_' + str(dsid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)

        return plotfiles
    except db.Error, e:
        logging.warn("Query counterparts for dsid %s failed: %s" % (str(dsid),query))
        raise

def hist_all_counterparts_assoc_r(conn, dsid):
    """
    Histogram of the all the dimensionless distances (i.e. assoc_r)
    of the associated sources to their running catalog based position.
    Dimensionless distances are distributed across 10 bins.
    """
    try:
        cursor = conn.cursor()
        query = """\
        SELECT r.xtrsrc_id
              ,a.assoc_xtrsrc_id
              ,3600 * SQRT( ((r.wm_ra * COS(RADIANS(r.wm_decl)) - x.ra * COS(RADIANS(x.decl))) 
                          *  (r.wm_ra * COS(RADIANS(r.wm_decl)) - x.ra * COS(RADIANS(x.decl)))) 
                          / (r.wm_ra_err * r.wm_ra_err + x.ra_err * x.ra_err)
                          +
                          ((r.wm_decl - x.decl) * (r.wm_decl - x.decl)) 
                          / (r.wm_decl_err * r.wm_decl_err + x.decl_err * x.decl_err)
                          ) AS assoc_r
          FROM assocxtrsources a
              ,extractedsources x 
              ,runningcatalog r
              ,images im1
         WHERE a.xtrsrc_id <> a.assoc_xtrsrc_id
           AND a.xtrsrc_id = r.xtrsrc_id
           AND a.assoc_xtrsrc_id = x.xtrsrcid
           AND x.image_id = im1.imageid
           AND im1.ds_id = %s
        """
        cursor.execute(query, (dsid,))

        results = zip(*cursor.fetchall())
        cursor.close()
        if len(results) != 0:
            xtrsrc_id = results[0]
            assoc_xtrsrc_id = results[1]
            assoc_r = results[2]
        
        plotfiles=[]
        p = 0
        fig = pylab.figure()
        ax = fig.add_subplot(111)
        ax.hist(assoc_r, 10, color='r')
        ax.set_xlabel(r'Assoc_r from runcat', size='x-large')
        ax.set_ylabel(r'N', size='x-large')
        for i in range(len(ax.get_xticklabels())):
            ax.get_xticklabels()[i].set_size('x-large')
        for i in range(len(ax.get_yticklabels())):
            ax.get_yticklabels()[i].set_size('x-large')

        pylab.grid(True)
        
        fname = 'hist_all_counterparts_assoc_r_dsid_' + str(dsid) + '.eps'
        plotfiles.append(fname)
        pylab.savefig(plotfiles[-1], dpi=600)

        return plotfiles
    except db.Error, e:
        logging.warn("Query counterparts for dsid %s failed: %s" % (str(dsid),query))
        raise

